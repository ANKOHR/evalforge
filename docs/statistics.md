# Statistics

EvalForge reports descriptive uncertainty rather than pretending a small fixture proves statistical significance.

- `proportion_interval` uses a Wilson interval for pass proportions.
- `bootstrap_difference` uses a seeded resampling procedure to report a candidate-minus-baseline difference and an empirical 95% interval.
- Samples, seed and warnings are retained in reports.
- Proportions with fewer than 30 cases receive a `small sample; interval is descriptive` warning.

The interval does not correct for repeated tuning, dataset leakage, distribution shift or correlated test cases. Those limitations belong in the interpretation of the result.
