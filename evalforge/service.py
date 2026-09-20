from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    CandidateSystem,
    Dataset,
    DatasetVersion,
    GraderResult,
    Metric,
    Project,
    Regression,
    Run,
    TestCase,
)
from .schemas import CandidateConfig, DatasetDefinition, RunReport


def content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ensure_project(
    session: Session, name: str = "EvalForge Demo", slug: str = "evalforge-demo"
) -> Project:
    project = session.scalar(select(Project).where(Project.slug == slug))
    if project is None:
        project = Project(
            name=name, slug=slug, description="Deterministic RAG and agent evaluation fixtures"
        )
        session.add(project)
        session.flush()
    return project


def persist_dataset(
    session: Session, project: Project, dataset: DatasetDefinition
) -> tuple[Dataset, DatasetVersion]:
    existing = session.scalar(
        select(Dataset).where(Dataset.project_id == project.id, Dataset.slug == dataset.slug)
    )
    if existing is None:
        existing = Dataset(project_id=project.id, name=dataset.name, slug=dataset.slug)
        session.add(existing)
        session.flush()
    version = session.scalar(
        select(DatasetVersion).where(
            DatasetVersion.dataset_id == existing.id, DatasetVersion.version == dataset.version
        )
    )
    if version is None:
        serialized = [case.model_dump(mode="json") for case in dataset.cases]
        version = DatasetVersion(
            dataset_id=existing.id,
            version=dataset.version,
            cases=serialized,
            split_counts=_split_counts(dataset),
            content_hash=content_hash(serialized),
            frozen=dataset.frozen,
        )
        session.add(version)
        session.flush()
        for case in dataset.cases:
            session.add(
                TestCase(
                    dataset_version_id=version.id,
                    external_id=case.id,
                    split=case.split,
                    payload=case.model_dump(mode="json"),
                )
            )
        existing.latest_version_id = version.id
    session.commit()
    return existing, version


def persist_report(
    session: Session,
    project: Project,
    dataset_version: DatasetVersion,
    config: CandidateConfig,
    report: RunReport,
) -> Run:
    candidate = CandidateSystem(
        project_id=project.id, name=config.name, config=config.model_dump(mode="json")
    )
    session.add(candidate)
    session.flush()
    run = Run(
        project_id=project.id,
        dataset_version_id=dataset_version.id,
        candidate_system_id=candidate.id,
        split=report.split,
        status="SUCCESS",
        seed=7,
        metadata_json=report.metadata,
    )
    session.add(run)
    session.flush()
    test_cases = {
        case.external_id: case
        for case in session.scalars(
            select(TestCase).where(TestCase.dataset_version_id == dataset_version.id)
        ).all()
    }
    for evaluation in report.case_results:
        db_case = test_cases[evaluation.case_id]
        for grader in evaluation.graders:
            session.add(
                GraderResult(
                    run_id=run.id,
                    test_case_id=db_case.id,
                    grader_name=grader.grader,
                    passed=grader.passed,
                    score=grader.score,
                    labels=grader.labels,
                    details=grader.details,
                )
            )
    for name, value in report.metrics.items():
        session.add(Metric(run_id=run.id, name=name, value=value, sample_count=report.case_count))
    session.commit()
    return run


def persist_regression(
    session: Session, project: Project, baseline: Run, candidate: Run, comparison
) -> Regression:
    regression = Regression(
        project_id=project.id,
        baseline_run_id=baseline.id,
        candidate_run_id=candidate.id,
        status=comparison.status,
        gates=[gate.model_dump(mode="json") for gate in comparison.gates],
        summary={"text": comparison.summary, "bootstrap": comparison.bootstrap},
    )
    session.add(regression)
    session.commit()
    return regression


def _split_counts(dataset: DatasetDefinition) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in dataset.cases:
        counts[case.split] = counts.get(case.split, 0) + 1
    return counts
