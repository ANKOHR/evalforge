# EvalForge

[![EvalForge CI](https://github.com/ANKOHR/evalforge/actions/workflows/ci.yml/badge.svg)](https://github.com/ANKOHR/evalforge/actions/workflows/ci.yml)

Regression testing for LLM, RAG and agent systems.

EvalForge is evaluation infrastructure rather than another chatbot. It freezes datasets, runs deterministic or externally-adapted candidate systems, scores outputs with explicit graders, groups failures and applies release gates. The verified demo requires no API key and uses synthetic RAG and tool-calling fixtures.

[Dashboard](https://evalforge-web.vercel.app) · [GitHub](https://github.com/ANKOHR/evalforge) · [Evidence](https://github.com/ANKOHR/evalforge/blob/main/docs/evidence.md) · [TraceBrowser sibling project](https://tracebrowser-web.vercel.app)

## 60-second reviewer path

1. Open the [dashboard](https://evalforge-web.vercel.app) and inspect the baseline-vs-candidate comparison.
2. Read the [evidence record](https://github.com/ANKOHR/evalforge/blob/main/docs/evidence.md) for the exact synthetic/live claim boundary.
3. Run `py -3.13 scripts/run_demo.py` to regenerate the deterministic showcase report.
4. Check the [CI workflow](https://github.com/ANKOHR/evalforge/actions/workflows/ci.yml) for lint, tests, demo regeneration and frontend build verification.

## The flagship proof

The built-in comparison runs two deterministic RAG candidates over a 120-case versioned dataset:

| Metric | baseline_v1 | candidate_v2 |
| --- | ---: | ---: |
| Answer fact correctness | 91.67% | 100.00% |
| Citation correctness | 95.83% | 87.50% |
| Unsupported-claim rate | 0.00% | 4.17% |
| p95 latency | 388ms | 238ms |

Candidate v2 improves answer facts and latency, but its citation regression and unsupported claims fail the configured release gates. The result is `BLOCK_RELEASE`, not a green score.

These measurements are deterministic synthetic-fixture results, not claims about a live model or customer system.

## Run it locally

```powershell
py -3.13 -m pip install -e ".[dev]"
py -3.13 -m ruff check evalforge scripts tests
py -3.13 -m pytest
py -3.13 scripts/run_demo.py
```

The demo writes `reports/evalforge-demo.json` and copies the same report into the static dashboard at `apps/web/public/demo/evalforge-demo.json`.

Use the installed CLI directly:

```powershell
evalforge run examples/minimal-rag.yaml --system examples/candidate.yaml --output reports/minimal-run.json
evalforge compare reports/baseline.json reports/candidate.json --output reports/comparison.json
```

Or run the complete benchmark:

```powershell
evalforge benchmark --output-dir reports
```

## Included capabilities

- Frozen, versioned datasets with train/dev/held-out splits and content hashes.
- Deterministic graders for exact match, facts, schema, numeric tolerance, citation presence/correctness, tool sequence, tool arguments, refusal, latency and cost.
- Optional `LLMJudgeGrader` adapter boundary that reports `UNVERIFIED_LLM_JUDGE` when no provider is configured.
- Python callable and HTTP candidate adapters plus deterministic RAG and agent fixtures.
- Retrieval recall@3, MRR, grounded fact correctness, citation correctness, refusal correctness, unsupported claims, latency and cost metrics.
- Failure taxonomy including `RETRIEVAL_MISS`, `UNSUPPORTED_CLAIM`, `WRONG_CITATION`, `SCHEMA_FAILURE`, `NUMERIC_ERROR`, `WRONG_TOOL`, `TOOL_ARGUMENT_ERROR`, `FAILED_REFUSAL` and budget regressions.
- Baseline/candidate comparison with configurable minimums, maximums and percentage-point drop budgets.
- Descriptive Wilson intervals and seeded bootstrap deltas with small-sample warnings.
- FastAPI API and static-first Next.js comparison dashboard.
- PostgreSQL-ready SQLAlchemy models with SQLite local fallback.

## Evaluation hygiene

The held-out slice is generated and reported separately from the train/dev cases. Do not tune a system repeatedly against the held-out cases and then present them as unseen. Every report records the dataset version, candidate variant, seed, split and fixture boundary.

## Truth boundary

EvalForge does not claim live OpenAI/Anthropic evaluation, real-world model accuracy, statistical significance, or customer outcomes. Provider interfaces are deliberately optional. The public dashboard and reports identify deterministic/synthetic measurements clearly.
