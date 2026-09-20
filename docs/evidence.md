# Evidence ledger

Updated: 2026-09-20

## Verified locally

- 52 pytest cases pass across graders, dataset versioning, runner metrics, regression gates, API health and persistence.
- Ruff passes over `evalforge`, `scripts` and `tests`.
- The synthetic RAG dataset contains 120 cases split 72 train / 24 dev / 24 held out.
- The agent benchmark contains 50 deterministic tool-policy cases.
- `reports/evalforge-demo.json` records baseline, candidate, broken candidate, comparison and agent reports.
- Candidate v2 improves held-out answer fact correctness from 91.67% to 100% but fails citation correctness and unsupported-claim gates, producing `BLOCK_RELEASE`.
- No API key, paid provider or third-party knowledge base is used.

## Verified publicly

- The static-first Next.js dashboard is deployed at [evalforge-web.vercel.app](https://evalforge-web.vercel.app).
- The public page returns HTTP 200, renders the deterministic `BLOCK_RELEASE` comparison, and serves the generated report artifact.
- The implementation and evidence ledger are publicly inspectable at [github.com/ANKOHR/evalforge](https://github.com/ANKOHR/evalforge) on the `main` branch.

## Not verified or not claimed

- No live OpenAI or Anthropic call was made.
- No customer accuracy, production latency or real-world retrieval claim is made.
- Bootstrap intervals are descriptive and small-sample warnings are intentional.
- HTTP and Python-callable adapters are implemented as boundaries; no external production endpoint is claimed.
- The public dashboard is a static presentation of the deterministic report; the FastAPI service, database and candidate execution remain locally verified only.
