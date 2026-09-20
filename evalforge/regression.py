from __future__ import annotations

from .metrics import bootstrap_difference
from .schemas import ComparisonReport, GateDefinition, RegressionGateResult, RunReport

DEFAULT_GATES = [
    GateDefinition(
        metric="answer_fact_correctness",
        max_drop_pp=1,
        description="answer facts cannot drop by more than 1pp",
    ),
    GateDefinition(
        metric="citation_correctness",
        min_value=0.95,
        max_drop_pp=2,
        description="citations must remain at least 95% correct and cannot drop by more than 2pp",
    ),
    GateDefinition(
        metric="unsupported_claim_rate",
        max_value=0.02,
        description="unsupported claims must remain at or below 2%",
    ),
    GateDefinition(metric="latency_p95_ms", max_value=3000, description="p95 latency budget"),
    GateDefinition(
        metric="cost_per_query_usd", max_value=0.01, description="per-query cost budget"
    ),
]


def compare_runs(
    baseline: RunReport, candidate: RunReport, gates: list[GateDefinition] | None = None
) -> ComparisonReport:
    gate_results: list[RegressionGateResult] = []
    for gate in gates or DEFAULT_GATES:
        base = baseline.metrics.get(gate.metric)
        current = candidate.metrics.get(gate.metric)
        delta = current - base if base is not None and current is not None else None
        passed = current is not None
        reasons: list[str] = []
        if current is None:
            passed = False
            reasons.append("metric missing")
        if passed and gate.min_value is not None and current < gate.min_value:
            passed = False
            reasons.append(f"{current:.3f} below minimum {gate.min_value:.3f}")
        if passed and gate.max_value is not None and current > gate.max_value:
            passed = False
            reasons.append(f"{current:.3f} above maximum {gate.max_value:.3f}")
        if (
            passed
            and delta is not None
            and gate.max_drop_pp is not None
            and delta * 100 < -gate.max_drop_pp
        ):
            passed = False
            reasons.append(
                f"delta {delta * 100:.2f}pp exceeds allowed drop {gate.max_drop_pp:.2f}pp"
            )
        if (
            passed
            and delta is not None
            and gate.max_increase_pp is not None
            and delta * 100 > gate.max_increase_pp
        ):
            passed = False
            reasons.append(
                f"delta {delta * 100:.2f}pp exceeds allowed increase {gate.max_increase_pp:.2f}pp"
            )
        if not reasons:
            reasons.append(gate.description or "gate passed")
        gate_results.append(
            RegressionGateResult(
                metric=gate.metric,
                baseline=base,
                candidate=current,
                delta=delta,
                passed=passed,
                reason="; ".join(reasons),
            )
        )
    bootstrap = {}
    baseline_scores = _scores(baseline, "contains_facts")
    candidate_scores = _scores(candidate, "contains_facts")
    bootstrap["answer_fact_correctness"] = bootstrap_difference(baseline_scores, candidate_scores)
    baseline_citations = _scores(baseline, "citation_correctness")
    candidate_citations = _scores(candidate, "citation_correctness")
    bootstrap["citation_correctness"] = bootstrap_difference(
        baseline_citations, candidate_citations
    )
    failed = [gate for gate in gate_results if not gate.passed]
    status = "BLOCK_RELEASE" if failed else "PASS"
    summary = (
        "Release blocked: " + ", ".join(f"{gate.metric} regression" for gate in failed)
        if failed
        else "All regression gates passed."
    )
    return ComparisonReport(
        baseline=baseline,
        candidate=candidate,
        gates=gate_results,
        status=status,
        summary=summary,
        bootstrap=bootstrap,
    )


def _scores(report: RunReport, grader_name: str) -> list[float]:
    return [
        result.score
        for case in report.case_results
        for result in case.graders
        if result.grader == grader_name
    ]
