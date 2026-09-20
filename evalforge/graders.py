from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from .schemas import GraderResultModel, SystemOutput, TestCaseDefinition


def _result(name: str, passed: bool, score: float, labels=None, details=None) -> GraderResultModel:
    return GraderResultModel(
        grader=name,
        passed=passed,
        score=max(0.0, min(1.0, float(score))),
        labels=list(labels or []),
        details=details or {},
    )


def _fact_key(value: Any) -> str:
    return " ".join(str(value).lower().split())


class Grader(ABC):
    name: str

    @abstractmethod
    def evaluate(self, case: TestCaseDefinition, output: SystemOutput) -> GraderResultModel:
        raise NotImplementedError


class ExactMatchGrader(Grader):
    name = "exact_match"

    def evaluate(self, case, output):
        expected = str(case.expected_fields.get("answer", case.metadata.get("expected_answer", "")))
        actual = output.answer
        passed = _fact_key(expected) == _fact_key(actual)
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            [] if passed else ["EXACT_MISMATCH"],
            {"expected": expected, "actual": actual},
        )


class ContainsFactsGrader(Grader):
    name = "contains_facts"

    def evaluate(self, case, output):
        expected = {_fact_key(fact) for fact in case.expected_facts}
        actual = {_fact_key(fact) for fact in output.facts}
        missing = sorted(expected - actual)
        passed = not missing
        return _result(
            self.name,
            passed,
            1 if not expected else (len(expected) - len(missing)) / len(expected),
            ["FACT_MISS"] if missing else [],
            {"missing": missing, "expected_count": len(expected)},
        )


class SchemaGrader(Grader):
    name = "schema"

    def evaluate(self, case, output):
        expected = case.expected_fields.get("schema", {})
        missing = [key for key in expected if key not in output.structured]
        wrong_types = []
        for key, expected_type in expected.items():
            if key not in output.structured:
                continue
            value = output.structured[key]
            valid = {
                "str": isinstance(value, str),
                "bool": isinstance(value, bool),
                "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            }.get(str(expected_type), True)
            if not valid:
                wrong_types.append(key)
        failures = missing + wrong_types
        passed = not failures
        return _result(
            self.name,
            passed,
            1 if not expected else (len(expected) - len(failures)) / len(expected),
            ["SCHEMA_FAILURE"] if failures else [],
            {"missing_fields": missing, "wrong_types": wrong_types},
        )


class NumericToleranceGrader(Grader):
    name = "numeric_tolerance"

    def evaluate(self, case, output):
        expected = case.expected_fields.get("numeric_expected")
        actual = output.structured.get(case.expected_fields.get("numeric_field", "value"))
        tolerance = float(case.expected_fields.get("numeric_tolerance", 0.01))
        if expected is None:
            return _result(self.name, True, 1, details={"skipped": True})
        try:
            difference = abs(float(actual) - float(expected))
            passed = difference <= tolerance
        except (TypeError, ValueError):
            difference = math.inf
            passed = False
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            ["NUMERIC_ERROR"] if not passed else [],
            {
                "expected": expected,
                "actual": actual,
                "difference": difference,
                "tolerance": tolerance,
            },
        )


class CitationPresenceGrader(Grader):
    name = "citation_presence"

    def evaluate(self, case, output):
        expected = len(case.expected_citations)
        present = len(output.citations)
        passed = present > 0 if expected else present == 0
        label = (
            "CITATION_MISSING"
            if expected and not passed
            else "UNEXPECTED_CITATION"
            if not expected and not passed
            else None
        )
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            [label] if label else [],
            {"expected_count": expected, "actual_count": present},
        )


class CitationCorrectnessFixtureGrader(Grader):
    name = "citation_correctness"

    def evaluate(self, case, output):
        expected = {(item.document_id, item.passage_id) for item in case.expected_citations}
        valid_context = {
            (str(item.get("document_id")), str(item.get("passage_id"))) for item in case.context
        }
        actual = {(item.document_id, item.passage_id) for item in output.citations}
        if not expected:
            passed = not actual
            return _result(
                self.name,
                passed,
                1 if passed else 0,
                ["WRONG_CITATION"] if actual else [],
                {"expected": [], "actual": sorted(actual)},
            )
        supported = actual & expected & valid_context
        score = len(supported) / len(expected)
        passed = score == 1 and actual <= valid_context
        labels = [] if passed else ["WRONG_CITATION"]
        return _result(
            self.name,
            passed,
            score,
            labels,
            {
                "expected": sorted(expected),
                "actual": sorted(actual),
                "supported": sorted(supported),
            },
        )


class ToolSequenceGrader(Grader):
    name = "tool_sequence"

    def evaluate(self, case, output):
        expected = [str(item.get("name")) for item in case.expected_tool_calls]
        actual = [str(item.get("name")) for item in output.tool_calls]
        passed = expected == actual
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            ["WRONG_TOOL"] if not passed else [],
            {"expected": expected, "actual": actual},
        )


class ToolArgumentGrader(Grader):
    name = "tool_arguments"

    def evaluate(self, case, output):
        expected = [item.get("arguments", {}) for item in case.expected_tool_calls]
        actual = [item.get("arguments", {}) for item in output.tool_calls]
        matched = sum(left == right for left, right in zip(expected, actual, strict=False))
        passed = expected == actual
        score = 1 if not expected else matched / len(expected)
        return _result(
            self.name,
            passed,
            score,
            ["TOOL_ARGUMENT_ERROR"] if not passed else [],
            {"expected": expected, "actual": actual},
        )


class RefusalGrader(Grader):
    name = "refusal"

    def evaluate(self, case, output):
        passed = case.expected_refusal == output.refusal
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            ["FAILED_REFUSAL"] if not passed else [],
            {"expected": case.expected_refusal, "actual": output.refusal},
        )


class LatencyBudgetGrader(Grader):
    name = "latency_budget"

    def __init__(self, budget_ms: float = 3000):
        self.budget_ms = budget_ms

    def evaluate(self, case, output):
        passed = output.latency_ms <= self.budget_ms
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            ["LATENCY_REGRESSION"] if not passed else [],
            {"latency_ms": output.latency_ms, "budget_ms": self.budget_ms},
        )


class CostBudgetGrader(Grader):
    name = "cost_budget"

    def __init__(self, budget_usd: float = 0.01):
        self.budget_usd = budget_usd

    def evaluate(self, case, output):
        passed = output.cost_usd <= self.budget_usd
        return _result(
            self.name,
            passed,
            1 if passed else 0,
            ["COST_REGRESSION"] if not passed else [],
            {"cost_usd": output.cost_usd, "budget_usd": self.budget_usd},
        )


class LLMJudgeGrader(Grader):
    """Optional provider boundary; no key or live judge is required by EvalForge."""

    name = "llm_judge"

    def __init__(self, provider: Any | None = None):
        self.provider = provider

    def evaluate(self, case, output):
        if self.provider is None:
            return _result(self.name, False, 0, ["UNVERIFIED_LLM_JUDGE"], {"configured": False})
        result = self.provider(case, output)
        return _result(
            self.name,
            bool(result),
            1 if result else 0,
            [] if result else ["LLM_JUDGE_FAIL"],
            {"configured": True},
        )


def default_rag_graders() -> list[Grader]:
    return [
        ContainsFactsGrader(),
        CitationPresenceGrader(),
        CitationCorrectnessFixtureGrader(),
        RefusalGrader(),
        LatencyBudgetGrader(),
        CostBudgetGrader(),
    ]


def default_agent_graders() -> list[Grader]:
    return [
        ToolSequenceGrader(),
        ToolArgumentGrader(),
        SchemaGrader(),
        RefusalGrader(),
        LatencyBudgetGrader(),
        CostBudgetGrader(),
    ]
