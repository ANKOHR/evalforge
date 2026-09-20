from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import mean
from uuid import uuid4

from .adapters import SystemAdapter
from .graders import Grader
from .metrics import percentile
from .schemas import CaseEvaluation, DatasetDefinition, RunReport, TestCaseDefinition


def _metric(values: list[float]) -> float:
    return round(mean(values), 6) if values else 0.0


def evaluate_case(
    case: TestCaseDefinition, adapter: SystemAdapter, graders: Iterable[Grader]
) -> CaseEvaluation:
    output = adapter.run(case)
    grader_results = [grader.evaluate(case, output) for grader in graders]
    return CaseEvaluation(case_id=case.id, split=case.split, output=output, graders=grader_results)


def run_dataset(
    dataset: DatasetDefinition,
    adapter: SystemAdapter,
    graders: list[Grader],
    split: str = "held_out",
    candidate_name: str = "candidate",
    run_id: str | None = None,
) -> RunReport:
    cases = [case for case in dataset.cases if split == "all" or case.split == split]
    evaluations = [evaluate_case(case, adapter, graders) for case in cases]
    by_grader: dict[str, list[float]] = defaultdict(list)
    failure_groups: Counter[str] = Counter()
    latency_values: list[float] = []
    cost_values: list[float] = []
    unsupported_claims = 0
    false_successes = 0
    citation_hits = 0
    citation_total = 0
    reciprocal_ranks: list[float] = []
    for evaluation, case in zip(evaluations, cases, strict=True):
        latency_values.append(evaluation.output.latency_ms)
        cost_values.append(evaluation.output.cost_usd)
        if case.expected_refusal and not evaluation.output.refusal:
            unsupported_claims += 1
        if (
            case.metadata.get("high_value")
            and evaluation.output.structured.get("decision") == "allowed"
        ):
            false_successes += 1
        expected_citations = {
            (item.document_id, item.passage_id) for item in case.expected_citations
        }
        actual_citations = [
            (item.document_id, item.passage_id) for item in evaluation.output.citations
        ]
        if expected_citations:
            citation_total += len(expected_citations)
            citation_hits += len(expected_citations & set(actual_citations))
            rank = next(
                (
                    position + 1
                    for position, citation in enumerate(actual_citations)
                    if citation in expected_citations
                ),
                None,
            )
            reciprocal_ranks.append(1 / rank if rank else 0)
        for result in evaluation.graders:
            by_grader[result.grader].append(result.score)
            for label in result.labels:
                failure_groups[label] += 1
    metrics = {
        "answer_fact_correctness": _metric(by_grader.get("contains_facts", [])),
        "citation_presence": _metric(by_grader.get("citation_presence", [])),
        "citation_correctness": _metric(by_grader.get("citation_correctness", [])),
        "refusal_correctness": _metric(by_grader.get("refusal", [])),
        "retrieval_recall_at_3": round(citation_hits / citation_total, 6)
        if citation_total
        else 1.0,
        "mrr": _metric(reciprocal_ranks),
        "unsupported_claim_rate": round(unsupported_claims / len(cases), 6) if cases else 0.0,
        "latency_mean_ms": _metric(latency_values),
        "latency_p95_ms": percentile(latency_values, 0.95),
        "cost_per_query_usd": _metric(cost_values),
        "case_pass_rate": _metric(
            [1.0 if all(result.passed for result in item.graders) else 0.0 for item in evaluations]
        ),
        "tool_sequence_accuracy": _metric(by_grader.get("tool_sequence", [])),
        "tool_argument_correctness": _metric(by_grader.get("tool_arguments", [])),
        "task_completion_rate": _metric(
            [
                1.0
                if any(
                    result.grader == "tool_sequence" and result.passed for result in item.graders
                )
                else 0.0
                for item in evaluations
            ]
        ),
        "false_success_count": float(false_successes),
    }
    slices: dict[str, dict[str, float]] = {}
    for difficulty in ("easy", "medium", "hard"):
        selected = [
            item
            for item, case in zip(evaluations, cases, strict=True)
            if case.difficulty == difficulty
        ]
        if selected:
            slices[difficulty] = {
                "case_count": float(len(selected)),
                "answer_fact_correctness": _metric(
                    [
                        next(
                            (
                                result.score
                                for result in item.graders
                                if result.grader == "contains_facts"
                            ),
                            0,
                        )
                        for item in selected
                    ]
                ),
                "citation_correctness": _metric(
                    [
                        next(
                            (
                                result.score
                                for result in item.graders
                                if result.grader == "citation_correctness"
                            ),
                            0,
                        )
                        for item in selected
                    ]
                ),
            }
    return RunReport(
        run_id=run_id or f"run_{uuid4().hex[:18]}",
        candidate=candidate_name,
        dataset=dataset.slug,
        dataset_version=dataset.version,
        split=split,
        case_count=len(cases),
        metrics=metrics,
        metric_samples={name: len(values) for name, values in by_grader.items()},
        slices=slices,
        failure_groups=dict(failure_groups),
        case_results=evaluations,
        metadata={
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset_total_cases": len(dataset.cases),
            "fixture_type": "deterministic synthetic",
            "held_out_only": split == "held_out",
        },
    )
