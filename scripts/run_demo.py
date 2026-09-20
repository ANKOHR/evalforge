from __future__ import annotations

import json
from pathlib import Path

from evalforge.benchmark import run_full_benchmark

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    reports = run_full_benchmark(ROOT / "reports")
    public = ROOT / "apps" / "web" / "public" / "demo"
    public.mkdir(parents=True, exist_ok=True)
    (public / "evalforge-demo.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    summary = reports["comparison"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "summary": summary["summary"],
                "rag_cases": reports["dataset"]["rag_cases"],
                "held_out_cases": reports["baseline"]["case_count"],
                "agent_cases": reports["dataset"]["agent_cases"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
