from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    passage_id: str


class TestCaseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=160)
    input: str | dict[str, Any]
    context: list[dict[str, Any]] = Field(default_factory=list)
    expected_facts: list[str] = Field(default_factory=list)
    expected_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    expected_citations: list[Citation] = Field(default_factory=list)
    expected_refusal: bool = False
    expected_fields: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    failure_category: str | None = None
    split: Literal["train", "dev", "held_out"] = "held_out"
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    cases: list[TestCaseDefinition] = Field(min_length=1)
    version: int = Field(default=1, ge=1)
    frozen: bool = True

    @field_validator("cases")
    @classmethod
    def unique_case_ids(cls, value: list[TestCaseDefinition]) -> list[TestCaseDefinition]:
        ids = [case.id for case in value]
        if len(ids) != len(set(ids)):
            raise ValueError("test case IDs must be unique")
        return value


class CandidateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    kind: Literal["deterministic_rag", "deterministic_agent", "http", "python_callable"]
    variant: str = "baseline_v1"
    endpoint: str | None = None
    timeout_seconds: float = Field(default=10, gt=0, le=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    weight: float = Field(default=1, ge=0)
    config: dict[str, Any] = Field(default_factory=dict)


class GateDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    min_value: float | None = None
    max_value: float | None = None
    max_drop_pp: float | None = None
    max_increase_pp: float | None = None
    description: str = ""


class SystemOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = ""
    facts: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    refusal: bool = False
    structured: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0
    cost_usd: float = 0
    raw: dict[str, Any] = Field(default_factory=dict)


class GraderResultModel(BaseModel):
    grader: str
    passed: bool
    score: float = Field(ge=0, le=1)
    labels: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class CaseEvaluation(BaseModel):
    case_id: str
    split: str
    output: SystemOutput
    graders: list[GraderResultModel]


class RunReport(BaseModel):
    run_id: str
    candidate: str
    dataset: str
    dataset_version: int
    split: str
    case_count: int
    metrics: dict[str, float]
    metric_samples: dict[str, int] = Field(default_factory=dict)
    slices: dict[str, dict[str, float]] = Field(default_factory=dict)
    failure_groups: dict[str, int] = Field(default_factory=dict)
    case_results: list[CaseEvaluation]
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegressionGateResult(BaseModel):
    metric: str
    baseline: float | None
    candidate: float | None
    delta: float | None
    passed: bool
    reason: str


class ComparisonReport(BaseModel):
    baseline: RunReport
    candidate: RunReport
    gates: list[RegressionGateResult]
    status: Literal["PASS", "BLOCK_RELEASE"]
    summary: str
    bootstrap: dict[str, dict[str, float | int | str]] = Field(default_factory=dict)
