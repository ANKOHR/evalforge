from __future__ import annotations

from evalforge.adapters import CallableAdapter, DeterministicAgentAdapter, DeterministicRAGAdapter
from evalforge.fixtures import agent_dataset, rag_dataset
from evalforge.graders import default_agent_graders, default_rag_graders
from evalforge.metrics import bootstrap_difference, percentile, proportion_interval
from evalforge.regression import compare_runs
from evalforge.runner import evaluate_case, run_dataset


def test_rag_dataset_has_held_out_split_and_required_edge_cases():
    dataset = rag_dataset(120)
    assert len(dataset.cases) == 120
    assert sum(case.split == "held_out" for case in dataset.cases) == 24
    assert any(case.expected_refusal for case in dataset.cases)
    assert any(case.failure_category == "CONFLICTING_SOURCE" for case in dataset.cases)
    assert any(case.failure_category == "PARAPHRASE" for case in dataset.cases)


def test_rag_report_metrics_are_reproducible():
    dataset = rag_dataset(120)
    first = run_dataset(dataset, DeterministicRAGAdapter("baseline_v1"), default_rag_graders())
    second = run_dataset(dataset, DeterministicRAGAdapter("baseline_v1"), default_rag_graders())
    assert first.metrics == second.metrics
    assert first.case_count == 24
    assert first.metadata["held_out_only"] is True


def test_candidate_improves_facts_but_citations_regress():
    dataset = rag_dataset(120)
    baseline = run_dataset(
        dataset,
        DeterministicRAGAdapter("baseline_v1"),
        default_rag_graders(),
        candidate_name="baseline_v1",
    )
    candidate = run_dataset(
        dataset,
        DeterministicRAGAdapter("candidate_v2"),
        default_rag_graders(),
        candidate_name="candidate_v2",
    )
    comparison = compare_runs(baseline, candidate)
    assert (
        candidate.metrics["answer_fact_correctness"] > baseline.metrics["answer_fact_correctness"]
    )
    assert candidate.metrics["citation_correctness"] < baseline.metrics["citation_correctness"]
    assert comparison.status == "BLOCK_RELEASE"
    assert any(g.metric == "citation_correctness" and not g.passed for g in comparison.gates)


def test_agent_report_measures_tool_selection_and_arguments():
    report = run_dataset(
        agent_dataset(50),
        DeterministicAgentAdapter("candidate_v2"),
        default_agent_graders(),
        candidate_name="agent",
    )
    assert report.case_count == 10
    assert report.metrics["tool_sequence_accuracy"] < 1
    assert "WRONG_TOOL" in report.failure_groups


def test_callable_adapter_validates_output():
    adapter = CallableAdapter(lambda case: {"answer": "ok", "structured": {"value": 1}})
    output = adapter.run(rag_dataset(1).cases[0])
    assert output.answer == "ok"


def test_evaluate_case_keeps_case_id_and_grader_trace():
    case = rag_dataset(1).cases[0]
    evaluation = evaluate_case(case, DeterministicRAGAdapter(), default_rag_graders())
    assert evaluation.case_id == case.id
    assert len(evaluation.graders) == 6


def test_percentile_is_stable():
    assert percentile([1, 2, 3, 4], 0.95) == 4
    assert percentile([], 0.95) == 0


def test_proportion_interval_warns_for_tiny_sample():
    interval = proportion_interval(8, 10)
    assert interval["low"] < interval["high"]
    assert "warning" in interval


def test_bootstrap_is_seeded_and_descriptive():
    first = bootstrap_difference([0, 1, 1], [1, 1, 1], seed=7, samples=100)
    second = bootstrap_difference([0, 1, 1], [1, 1, 1], seed=7, samples=100)
    assert first == second
    assert first["difference"] > 0
    assert "warning" in first


def test_empty_bootstrap_is_safe():
    assert bootstrap_difference([], [1])["samples"] == 0
