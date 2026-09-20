# Architecture

```text
Next.js comparison dashboard
             │
        FastAPI API
             │
 SQLAlchemy persistence ─── SQLite fallback / PostgreSQL-ready URL
             │
      Evaluation runner
       ┌─────┴───────────────┐
 deterministic fixtures   adapters
       │                 ┌───┴──────────────┐
       │                 │ HTTP / callable  │
       │                 │ optional provider│
       ▼                 └──────────────────┘
 versioned cases → graders → metrics → gates → reproducible report
```

Datasets are frozen `DatasetVersion` rows containing serialized `TestCase` records and a content hash. Runs reference a specific dataset version and candidate configuration. Grader results are stored per case and grader, while aggregate `Metric` rows provide dashboard and CI summaries. A `Regression` stores the complete gate decision and bootstrap metadata.

The runner is intentionally adapter-oriented. A candidate system returns a typed `SystemOutput`; EvalForge does not need to know whether the output came from a deterministic fixture, a Python callable, an HTTP endpoint or an optional model provider.
