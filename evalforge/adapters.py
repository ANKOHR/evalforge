from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

import httpx

from .schemas import CandidateConfig, Citation, SystemOutput, TestCaseDefinition


class SystemAdapter(Protocol):
    def run(self, case: TestCaseDefinition) -> SystemOutput: ...


class DeterministicRAGAdapter:
    def __init__(self, variant: str = "baseline_v1"):
        self.variant = variant

    def run(self, case: TestCaseDefinition) -> SystemOutput:
        index = int(case.metadata.get("case_index", 1))
        expected_fact = case.expected_facts[0] if case.expected_facts else ""
        expected_citation = case.expected_citations[0] if case.expected_citations else None
        context_citations = [
            Citation(document_id=item["document_id"], passage_id=item["passage_id"])
            for item in case.context
        ]
        if self.variant == "broken_candidate":
            facts = [] if index % 3 == 0 else ["Unsupported claim from a broken candidate."]
            citations = context_citations[-1:] if case.context else []
            refusal = False
        elif case.expected_refusal:
            # Candidate v2 handles evidence absence more consistently than baseline_v1.
            refusal = index % 13 != 0 if self.variant == "baseline_v1" else index % 17 != 0
            facts = [] if refusal else ["The system invented an answer."]
            citations = [] if refusal else context_citations[:1]
        else:
            fact_ok = index % (13 if self.variant == "baseline_v1" else 19) != 0
            facts = [expected_fact] if fact_ok else ["A similar but incorrect fact."]
            refusal = False
            if expected_citation is None:
                citations = []
            else:
                citation_ok = index % (25 if self.variant == "baseline_v1" else 9) != 0
                citations = [expected_citation] if citation_ok else context_citations[1:2]
        answer = facts[0] if facts else "Unable to verify from the supplied evidence."
        latency = (
            180 + (index % 17) * 13 if self.variant == "baseline_v1" else 130 + (index % 13) * 9
        )
        return SystemOutput(
            answer=answer,
            facts=facts,
            citations=citations,
            refusal=refusal,
            structured={"answer": answer, "source_count": len(case.context)},
            latency_ms=latency,
            cost_usd=0.0008 if self.variant == "baseline_v1" else 0.0011,
            raw={"adapter": "deterministic_rag", "variant": self.variant},
        )


class DeterministicAgentAdapter:
    def __init__(self, variant: str = "baseline_v1"):
        self.variant = variant

    def run(self, case: TestCaseDefinition) -> SystemOutput:
        expected = list(case.expected_tool_calls)
        index = int(case.metadata.get("case_index", 1))
        calls = expected.copy()
        if self.variant == "broken_candidate" or (
            self.variant == "baseline_v1" and index % 10 == 0
        ):
            calls = calls[:-1] if calls else [{"name": "wrong_tool", "arguments": {}}]
        if self.variant == "candidate_v2" and index % 9 == 0:
            calls = calls + [{"name": "unnecessary_lookup", "arguments": {}}]
        structured = {
            "decision": "review" if case.metadata.get("high_value") else "allowed",
            "policy_allowed": not bool(case.metadata.get("high_value")),
        }
        return SystemOutput(
            answer=structured["decision"],
            structured=structured,
            tool_calls=calls,
            latency_ms=100 + index % 20 * 7,
            cost_usd=0.0004,
            raw={"adapter": "deterministic_agent", "variant": self.variant},
        )


class CallableAdapter:
    def __init__(self, function: Callable[[TestCaseDefinition], dict[str, Any] | SystemOutput]):
        self.function = function

    def run(self, case: TestCaseDefinition) -> SystemOutput:
        value = self.function(case)
        return value if isinstance(value, SystemOutput) else SystemOutput.model_validate(value)


class HttpAdapter:
    def __init__(self, endpoint: str, timeout_seconds: float = 10):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def run(self, case: TestCaseDefinition) -> SystemOutput:
        response = httpx.post(
            self.endpoint, json=case.model_dump(mode="json"), timeout=self.timeout_seconds
        )
        response.raise_for_status()
        return SystemOutput.model_validate(response.json())


def build_adapter(
    config: CandidateConfig, callable_system: Callable | None = None
) -> SystemAdapter:
    if config.kind == "deterministic_rag":
        return DeterministicRAGAdapter(config.variant)
    if config.kind == "deterministic_agent":
        return DeterministicAgentAdapter(config.variant)
    if config.kind == "python_callable" and callable_system is not None:
        return CallableAdapter(callable_system)
    if config.kind == "http" and config.endpoint:
        return HttpAdapter(config.endpoint, config.timeout_seconds)
    raise ValueError(f"candidate adapter is not configured: {config.kind}")
