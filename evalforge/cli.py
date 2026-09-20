from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .adapters import build_adapter
from .benchmark import run_full_benchmark
from .graders import default_agent_graders, default_rag_graders
from .regression import compare_runs
from .runner import run_dataset
from .schemas import CandidateConfig, DatasetDefinition, RunReport


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main() -> None:
    parser = argparse.ArgumentParser(prog="evalforge")
    sub = parser.add_subparsers(dest="command", required=True)
    benchmark = sub.add_parser("benchmark", help="run the deterministic RAG and agent benchmarks")
    benchmark.add_argument("--output-dir", default="reports")
    run = sub.add_parser("run", help="run a versioned dataset against a candidate system")
    run.add_argument("dataset", type=Path)
    run.add_argument("--system", required=True, type=Path)
    run.add_argument("--output", default="reports/run.json")
    run.add_argument("--split", default="held_out")
    compare = sub.add_parser("compare", help="apply regression gates to two run reports")
    compare.add_argument("baseline", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--output", default="reports/comparison.json")
    args = parser.parse_args()
    if args.command == "benchmark":
        reports = run_full_benchmark(args.output_dir)
        print(json.dumps(reports["comparison"], indent=2))
        return
    if args.command == "run":
        dataset = DatasetDefinition.model_validate(_load_yaml(args.dataset))
        config = CandidateConfig.model_validate(_load_yaml(args.system))
        graders = (
            default_agent_graders()
            if config.kind == "deterministic_agent"
            else default_rag_graders()
        )
        report = run_dataset(
            dataset, build_adapter(config), graders, split=args.split, candidate_name=config.name
        )
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report.model_dump_json(indent=2), encoding="utf-8")
        print(report.model_dump_json(indent=2))
        return
    if args.command == "compare":
        baseline = RunReport.model_validate_json(args.baseline.read_text(encoding="utf-8"))
        candidate = RunReport.model_validate_json(args.candidate.read_text(encoding="utf-8"))
        comparison = compare_runs(baseline, candidate)
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(comparison.model_dump_json(indent=2), encoding="utf-8")
        print(comparison.model_dump_json(indent=2))
        if comparison.status == "BLOCK_RELEASE":
            raise SystemExit(1)
