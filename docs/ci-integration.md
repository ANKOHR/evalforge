# CI integration

The intended CI contract is simple: run the held-out evaluation, compare it with the checked-in baseline, and fail the job when a gate fails.

```yaml
- name: Run candidate evaluation
  run: evalforge run datasets/rag.yaml --system systems/candidate.yaml --output reports/candidate.json
- name: Apply release gates
  run: evalforge compare reports/baseline.json reports/candidate.json --output reports/comparison.json
```

The example workflow in `.github/workflows/ci.yml` runs Ruff, 50+ tests, the deterministic benchmark and the dashboard production build. The `compare` command returns exit code 1 for `BLOCK_RELEASE` after writing the complete comparison report, so CI can stop a release without losing the failure analysis.
