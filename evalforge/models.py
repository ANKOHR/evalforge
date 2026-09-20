from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:18]}"


def now_utc() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("proj"))
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("data"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(120))
    latest_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    __table_args__ = (UniqueConstraint("project_id", "slug", name="uq_dataset_project_slug"),)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("dver"))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    cases: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    split_counts: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    frozen: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    __table_args__ = (UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),)


class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("case"))
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(160))
    split: Mapped[str] = mapped_column(String(30), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class CandidateSystem(Base):
    __tablename__ = "candidate_systems"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("cand"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Grader(Base):
    __tablename__ = "graders"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("grad"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("run"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    candidate_system_id: Mapped[str] = mapped_column(ForeignKey("candidate_systems.id"))
    split: Mapped[str] = mapped_column(String(30), default="held_out")
    status: Mapped[str] = mapped_column(String(30), default="RUNNING")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GraderResult(Base):
    __tablename__ = "grader_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("gres"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"), index=True)
    grader_name: Mapped[str] = mapped_column(String(160))
    passed: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Metric(Base):
    __tablename__ = "metrics"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("metric"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    value: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Regression(Base):
    __tablename__ = "regressions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("reg"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    baseline_run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    candidate_run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    status: Mapped[str] = mapped_column(String(30))
    gates: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("art"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    path: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("exp"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
