from __future__ import annotations

import math
import random
from collections.abc import Iterable
from statistics import mean


def percentile(values: Iterable[float], percentile_value: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percentile_value) - 1))
    return round(ordered[index], 6)


def proportion_interval(
    successes: int, total: int, z: float = 1.96
) -> dict[str, float | int | str]:
    if total <= 0:
        return {
            "successes": successes,
            "total": total,
            "low": 0.0,
            "high": 0.0,
            "warning": "no samples",
        }
    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    result: dict[str, float | int | str] = {
        "successes": successes,
        "total": total,
        "low": round(max(0, centre - margin), 6),
        "high": round(min(1, centre + margin), 6),
    }
    if total < 30:
        result["warning"] = "small sample; interval is descriptive"
    return result


def bootstrap_difference(
    baseline: list[float], candidate: list[float], seed: int = 7, samples: int = 1000
) -> dict[str, float | int | str]:
    if not baseline or not candidate:
        return {
            "difference": 0.0,
            "low": 0.0,
            "high": 0.0,
            "samples": 0,
            "warning": "missing samples",
        }
    rng = random.Random(seed)
    differences: list[float] = []
    for _ in range(samples):
        baseline_draw = [baseline[rng.randrange(len(baseline))] for _ in baseline]
        candidate_draw = [candidate[rng.randrange(len(candidate))] for _ in candidate]
        differences.append(mean(candidate_draw) - mean(baseline_draw))
    return {
        "difference": round(mean(candidate) - mean(baseline), 6),
        "low": round(percentile(differences, 0.025), 6),
        "high": round(percentile(differences, 0.975), 6),
        "samples": samples,
        "warning": "descriptive bootstrap; not a significance claim"
        if len(baseline) < 30 or len(candidate) < 30
        else "descriptive bootstrap",
    }
