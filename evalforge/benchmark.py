from __future__ import annotations

import json
from pathlib import Path

from .adapters import DeterministicAgentAdapter, DeterministicRAGAdapter
from .fixtures import agent_dataset, rag_dataset
from .graders import default_agent_graders, default_rag_graders
from .regression import compare_runs
from .runner import run_dataset


def run_full_benchmark(output_dir: str | Path = "reports") -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rag = rag_dataset(120)
    baseline = run_dataset(
        rag,
        DeterministicRAGAdapter("baseline_v1"),
        default_rag_graders(),
        candidate_name="baseline_v1",
    )
    candidate = run_dataset(
        rag,
        DeterministicRAGAdapter("candidate_v2"),
        default_rag_graders(),
        candidate_name="candidate_v2",
    )
    broken = run_dataset(
        rag,
        DeterministicRAGAdapter("broken_candidate"),
        default_rag_graders(),
        candidate_name="broken_candidate",
    )
    comparison = compare_runs(baseline, candidate)
    agent = agent_dataset(50)
    agent_report = run_dataset(
        agent,
        DeterministicAgentAdapter("candidate_v2"),
        default_agent_graders(),
        candidate_name="agent_candidate_v2",
    )
    reports = {
        "baseline": baseline.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "broken": broken.model_dump(mode="json"),
        "comparison": comparison.model_dump(mode="json"),
        "agent": agent_report.model_dump(mode="json"),
        "dataset": {
            "rag_cases": len(rag.cases),
            "rag_splits": _split_counts(rag),
            "agent_cases": len(agent.cases),
        },
    }
    (output / "evalforge-demo.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    return reports


def _split_counts(dataset) -> dict[str, int]:
    result: dict[str, int] = {}
    for case in dataset.cases:
        result[case.split] = result.get(case.split, 0) + 1
    return result
