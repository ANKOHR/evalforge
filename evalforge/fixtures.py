from __future__ import annotations

from dataclasses import dataclass

from .schemas import Citation, DatasetDefinition, TestCaseDefinition

TOPICS = [
    ("Northstar", "Northstar uses a 30-day evaluation window."),
    ("Mariner", "Mariner supports exports in CSV and JSON."),
    ("Juniper", "Juniper's standard support response target is four hours."),
    ("Cedar", "Cedar stores primary records in London."),
    ("Quarry", "Quarry requires manager approval for refunds above 500 pounds."),
    ("Aster", "Aster's batch import limit is 10,000 rows."),
    ("Beacon", "Beacon rotates service credentials every 90 days."),
    ("Orchard", "Orchard invoices are payable within 30 days."),
    ("Lumen", "Lumen publishes a monthly availability report."),
    ("Rook", "Rook's standard retention period is seven years."),
]


def _context(topic: str, fact: str, index: int, conflict: bool = False) -> list[dict]:
    gold = {
        "document_id": f"doc-{topic.lower()}",
        "passage_id": f"p-{topic.lower()}-1",
        "text": fact,
        "authority": "primary",
    }
    distractor = {
        "document_id": f"doc-{topic.lower()}-faq",
        "passage_id": f"p-{topic.lower()}-faq",
        "text": f"{topic} is reviewed by operations in quarter {index % 4 + 1}.",
        "authority": "secondary",
    }
    values = [gold, distractor]
    if conflict:
        values.append(
            {
                "document_id": f"doc-{topic.lower()}-legacy",
                "passage_id": f"p-{topic.lower()}-legacy",
                "text": f"Legacy {topic} guidance used a different policy.",
                "authority": "legacy",
            }
        )
    return values


def rag_dataset(case_count: int = 120) -> DatasetDefinition:
    cases: list[TestCaseDefinition] = []
    for index in range(1, case_count + 1):
        topic, fact = TOPICS[(index - 1) % len(TOPICS)]
        absent = index % 6 == 0
        conflict = index % 11 == 0
        paraphrase = index % 7 == 0
        if absent:
            query = (
                f"Can the knowledge base verify the {topic} office's unannounced weekend policy?"
            )
            context = _context(topic, fact, index)
            expected_facts: list[str] = []
            expected_citations: list[Citation] = []
            expected_refusal = True
            failure_category = "MISSING_EVIDENCE"
            answer = "Unable to verify from the supplied evidence."
        else:
            wording = (
                "What does the source say about"
                if paraphrase
                else "What is the documented fact for"
            )
            query = f"{wording} {topic}?"
            context = _context(topic, fact, index, conflict=conflict)
            expected_facts = [fact]
            expected_citations = [
                Citation(document_id=f"doc-{topic.lower()}", passage_id=f"p-{topic.lower()}-1")
            ]
            expected_refusal = False
            failure_category = (
                "CONFLICTING_SOURCE" if conflict else "PARAPHRASE" if paraphrase else None
            )
            answer = fact
        split = (
            "train"
            if index <= int(case_count * 0.6)
            else "dev"
            if index <= int(case_count * 0.8)
            else "held_out"
        )
        cases.append(
            TestCaseDefinition(
                id=f"rag-{index:03d}",
                input=query,
                context=context,
                expected_facts=expected_facts,
                expected_citations=expected_citations,
                expected_refusal=expected_refusal,
                expected_fields={"answer": answer},
                tags=["rag", "synthetic", "held-out" if split == "held_out" else "development"],
                difficulty="hard" if conflict or absent else "medium" if paraphrase else "easy",
                failure_category=failure_category,
                split=split,
                metadata={
                    "topic": topic,
                    "gold_answer": answer,
                    "case_index": index,
                    "kind": "absent"
                    if absent
                    else "conflict"
                    if conflict
                    else "paraphrase"
                    if paraphrase
                    else "supported",
                },
            )
        )
    return DatasetDefinition(
        name="Synthetic RAG Reliability", slug="synthetic-rag-reliability", cases=cases, version=1
    )


@dataclass(frozen=True)
class AgentFixture:
    cases: list[TestCaseDefinition]


def agent_dataset(case_count: int = 50) -> DatasetDefinition:
    cases: list[TestCaseDefinition] = []
    for index in range(1, case_count + 1):
        refund = index % 4 == 0
        high_value = index % 8 == 0
        expected_tools = [
            {"name": "find_customer", "arguments": {"customer_id": f"CUS-{index:04d}"}},
            {"name": "inspect_order", "arguments": {"order_id": f"ORD-{index:04d}"}},
        ]
        if refund and not high_value:
            expected_tools.extend(
                [
                    {"name": "calculate_refund", "arguments": {"amount": 25 + index}},
                    {"name": "create_review_task", "arguments": {"priority": "normal"}},
                ]
            )
        elif refund:
            expected_tools.append(
                {"name": "create_review_task", "arguments": {"priority": "finance"}}
            )
        cases.append(
            TestCaseDefinition(
                id=f"agent-{index:03d}",
                input={
                    "customer_id": f"CUS-{index:04d}",
                    "order_id": f"ORD-{index:04d}",
                    "refund_requested": refund,
                    "amount": 25 + index,
                },
                expected_tool_calls=expected_tools,
                expected_fields={"schema": {"decision": "str", "policy_allowed": "bool"}},
                expected_refusal=False,
                tags=["agent", "policy", "synthetic"],
                difficulty="hard" if high_value else "medium",
                failure_category="POLICY_BOUNDARY" if high_value else None,
                split="held_out"
                if index > int(case_count * 0.8)
                else "dev"
                if index > int(case_count * 0.6)
                else "train",
                metadata={"case_index": index, "high_value": high_value},
            )
        )
    return DatasetDefinition(
        name="Synthetic tool policy benchmark", slug="synthetic-tool-policy", cases=cases, version=1
    )
