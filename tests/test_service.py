from __future__ import annotations

from sqlalchemy import select

from evalforge.adapters import DeterministicRAGAdapter
from evalforge.fixtures import rag_dataset
from evalforge.graders import default_rag_graders
from evalforge.models import DatasetVersion, GraderResult, Metric, Run
from evalforge.models import TestCase as DbTestCase
from evalforge.runner import run_dataset
from evalforge.schemas import CandidateConfig
from evalforge.service import ensure_project, persist_dataset, persist_report


def test_dataset_version_is_frozen_and_hashed(db_session):
    project = ensure_project(db_session)
    dataset, version = persist_dataset(db_session, project, rag_dataset(4))
    assert version.frozen is True
    assert len(version.content_hash) == 64
    assert dataset.latest_version_id == version.id


def test_dataset_version_persists_cases(db_session):
    project = ensure_project(db_session)
    _, version = persist_dataset(db_session, project, rag_dataset(4))
    assert (
        db_session.scalar(select(DatasetVersion).where(DatasetVersion.id == version.id)) is not None
    )
    assert (
        len(
            db_session.scalars(
                select(DbTestCase).where(DbTestCase.dataset_version_id == version.id)
            ).all()
        )
        == 4
    )


def test_persist_report_creates_run_grader_results_and_metrics(db_session):
    project = ensure_project(db_session)
    _dataset, version = persist_dataset(db_session, project, rag_dataset(10))
    report = run_dataset(rag_dataset(10), DeterministicRAGAdapter(), default_rag_graders())
    run = persist_report(
        db_session,
        project,
        version,
        CandidateConfig(name="baseline", kind="deterministic_rag"),
        report,
    )
    assert db_session.scalar(select(Run).where(Run.id == run.id)).status == "SUCCESS"
    assert db_session.scalar(select(GraderResult).where(GraderResult.run_id == run.id)) is not None
    assert db_session.scalar(select(Metric).where(Metric.run_id == run.id)).value >= 0


def test_persist_dataset_reuses_same_frozen_version(db_session):
    project = ensure_project(db_session)
    definition = rag_dataset(4)
    _, first = persist_dataset(db_session, project, definition)
    _, second = persist_dataset(db_session, project, definition)
    assert first.id == second.id
    assert len(db_session.scalars(select(DatasetVersion)).all()) == 1


def test_new_project_is_reused_by_slug(db_session):
    first = ensure_project(db_session, name="A", slug="same")
    second = ensure_project(db_session, name="B", slug="same")
    assert first.id == second.id
