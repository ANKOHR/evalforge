from __future__ import annotations

import sys

import pytest

from evalforge import cli
from evalforge.adapters import DeterministicRAGAdapter
from evalforge.fixtures import rag_dataset
from evalforge.graders import default_rag_graders
from evalforge.runner import run_dataset


def test_cli_run_writes_report(tmp_path, monkeypatch):
    output = tmp_path / "run.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evalforge",
            "run",
            "examples/minimal-rag.yaml",
            "--system",
            "examples/candidate.yaml",
            "--output",
            str(output),
        ],
    )
    cli.main()
    assert output.exists()


def test_cli_compare_returns_exit_code_one_for_blocked_release(tmp_path, monkeypatch):
    dataset = rag_dataset(120)
    baseline = run_dataset(
        dataset,
        DeterministicRAGAdapter("baseline_v1"),
        default_rag_graders(),
        candidate_name="baseline",
    )
    candidate = run_dataset(
        dataset,
        DeterministicRAGAdapter("candidate_v2"),
        default_rag_graders(),
        candidate_name="candidate",
    )
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    output = tmp_path / "comparison.json"
    baseline_path.write_text(baseline.model_dump_json(), encoding="utf-8")
    candidate_path.write_text(candidate.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["evalforge", "compare", str(baseline_path), str(candidate_path), "--output", str(output)],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    assert output.exists()
