from __future__ import annotations

import pytest

from evalforge.graders import (
    CitationCorrectnessFixtureGrader,
    CitationPresenceGrader,
    ContainsFactsGrader,
    CostBudgetGrader,
    ExactMatchGrader,
    LatencyBudgetGrader,
    LLMJudgeGrader,
    NumericToleranceGrader,
    RefusalGrader,
    SchemaGrader,
    ToolArgumentGrader,
    ToolSequenceGrader,
)
from evalforge.schemas import Citation, SystemOutput
from evalforge.schemas import TestCaseDefinition as CaseDefinition


def rag_case(**kwargs):
    defaults = {"id": "case", "input": "question", "expected_facts": [], "expected_citations": []}
    defaults.update(kwargs)
    return CaseDefinition(**defaults)


@pytest.mark.parametrize(
    ("expected", "actual", "passed"),
    [
        ("same answer", "same answer", True),
        ("same answer", "different", False),
        ("Northstar 30 days", "northstar 30   days", True),
    ],
)
def test_exact_match(expected, actual, passed):
    result = ExactMatchGrader().evaluate(
        rag_case(expected_fields={"answer": expected}), SystemOutput(answer=actual)
    )
    assert result.passed is passed


@pytest.mark.parametrize(
    ("expected", "actual", "score"),
    [([], [], 1), (["one"], ["one"], 1), (["one", "two"], ["one"], 0.5), (["one"], [], 0)],
)
def test_contains_facts(expected, actual, score):
    result = ContainsFactsGrader().evaluate(
        rag_case(expected_facts=expected), SystemOutput(facts=actual)
    )
    assert result.score == score


@pytest.mark.parametrize(
    ("structured", "passed"),
    [
        ({"name": "Acme", "allowed": True}, True),
        ({"name": "Acme"}, False),
        ({"name": 42, "allowed": True}, False),
    ],
)
def test_schema_grader(structured, passed):
    case = rag_case(expected_fields={"schema": {"name": "str", "allowed": "bool"}})
    assert SchemaGrader().evaluate(case, SystemOutput(structured=structured)).passed is passed


@pytest.mark.parametrize(
    ("actual", "passed"),
    [(100.0, True), (100.04, True), (100.2, False), (None, False)],
)
def test_numeric_tolerance(actual, passed):
    case = rag_case(
        expected_fields={
            "numeric_expected": 100,
            "numeric_field": "total",
            "numeric_tolerance": 0.05,
        }
    )
    assert (
        NumericToleranceGrader().evaluate(case, SystemOutput(structured={"total": actual})).passed
        is passed
    )


@pytest.mark.parametrize(
    ("expected", "actual", "passed"),
    [(1, 1, True), (1, 0, False), (0, 0, True), (0, 1, False)],
)
def test_citation_presence(expected, actual, passed):
    case = rag_case(
        expected_citations=[Citation(document_id="d", passage_id="p")] if expected else []
    )
    output = SystemOutput(citations=[Citation(document_id="d", passage_id="p")] if actual else [])
    assert CitationPresenceGrader().evaluate(case, output).passed is passed


@pytest.mark.parametrize(
    ("citation", "passed"),
    [
        (Citation(document_id="d", passage_id="p"), True),
        (Citation(document_id="d", passage_id="wrong"), False),
        (Citation(document_id="other", passage_id="p"), False),
    ],
)
def test_citation_correctness(citation, passed):
    case = rag_case(
        expected_citations=[Citation(document_id="d", passage_id="p")],
        context=[
            {"document_id": "d", "passage_id": "p"},
            {"document_id": "d", "passage_id": "wrong"},
        ],
    )
    assert (
        CitationCorrectnessFixtureGrader().evaluate(case, SystemOutput(citations=[citation])).passed
        is passed
    )


@pytest.mark.parametrize(
    ("actual", "passed"),
    [([], False), ([{"name": "find"}], True), ([{"name": "wrong"}], False)],
)
def test_tool_sequence(actual, passed):
    case = rag_case(expected_tool_calls=[{"name": "find", "arguments": {}}])
    assert ToolSequenceGrader().evaluate(case, SystemOutput(tool_calls=actual)).passed is passed


@pytest.mark.parametrize(
    ("actual", "passed"),
    [
        ([{"name": "find", "arguments": {"id": "1"}}], True),
        ([{"name": "find", "arguments": {"id": "2"}}], False),
    ],
)
def test_tool_arguments(actual, passed):
    case = rag_case(expected_tool_calls=[{"name": "find", "arguments": {"id": "1"}}])
    assert ToolArgumentGrader().evaluate(case, SystemOutput(tool_calls=actual)).passed is passed


def test_refusal_grader():
    case = rag_case(expected_refusal=True)
    assert RefusalGrader().evaluate(case, SystemOutput(refusal=True)).passed
    assert not RefusalGrader().evaluate(case, SystemOutput(refusal=False)).passed


@pytest.mark.parametrize(
    ("latency", "cost", "passed"),
    [(100, 0.001, True), (3100, 0.001, False), (100, 0.02, False)],
)
def test_budgets(latency, cost, passed):
    case = rag_case()
    latency_result = LatencyBudgetGrader(3000).evaluate(case, SystemOutput(latency_ms=latency))
    cost_result = CostBudgetGrader(0.01).evaluate(case, SystemOutput(cost_usd=cost))
    assert (latency_result.passed and cost_result.passed) is passed


def test_optional_llm_judge_is_unverified_without_provider():
    result = LLMJudgeGrader().evaluate(rag_case(), SystemOutput())
    assert not result.passed
    assert "UNVERIFIED_LLM_JUDGE" in result.labels
