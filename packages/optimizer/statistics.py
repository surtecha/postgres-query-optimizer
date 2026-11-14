"""Paired warm-cache statistics and an explicit conservative acceptance policy."""
import math
import random
import statistics as stats
from typing import Any


def summary(samples: list[float]) -> dict[str, Any]:
    if len(samples) < 2 or any(not math.isfinite(x) or x <= 0 for x in samples):
        raise ValueError("At least two finite positive samples required")
    mean = stats.mean(samples)
    return {"n": len(samples), "median_ms": stats.median(samples), "min_ms": min(samples),
            "max_ms": max(samples), "stdev_ms": stats.stdev(samples),
            "cv": stats.stdev(samples) / mean,
            "p95_ms": stats.quantiles(samples, n=100, method="inclusive")[94] if len(samples) >= 40 else None}


def comparison(baseline: list[float], candidate: list[float], seed: int = 42) -> dict[str, Any]:
    if len(baseline) != len(candidate) or len(baseline) < 5:
        raise ValueError("At least five paired trials required")
    a, b = summary(baseline), summary(candidate)
    ratios = [x / y for x, y in zip(baseline, candidate, strict=True)]
    rng = random.Random(seed)
    boot = sorted(stats.median(rng.choices(ratios, k=len(ratios))) for _ in range(2000))
    return {"baseline": a, "candidate": b, "median_speedup": stats.median(ratios),
            "absolute_saved_ms": a["median_ms"] - b["median_ms"],
            "speedup_ci95": [boot[49], boot[1949]], "bootstrap_seed": seed,
            "confidence_method": "paired nonparametric bootstrap of median ratios, 2000 resamples",
            "small_sample_warning": len(baseline) < 20}


def accept(result: dict[str, Any], *, validated: bool, min_improvement: float,
           max_cv: float, index_bytes: int = 0, max_index_bytes: int = 67108864,
           protected_pass: bool = True) -> tuple[bool, list[str]]:
    reasons = []
    if not validated:
        reasons.append("Equivalence is not differentially validated")
    threshold = 1 / (1 - min_improvement)
    if result["median_speedup"] < threshold or result["speedup_ci95"][0] <= 1:
        reasons.append("Improvement threshold or confidence requirement failed")
    if max(result["baseline"]["cv"], result["candidate"]["cv"]) > max_cv:
        reasons.append("Measurement variance exceeds policy")
    if index_bytes > max_index_bytes:
        reasons.append("Index storage exceeds policy")
    if not protected_pass:
        reasons.append("Protected workload regression gate failed")
    return not reasons, reasons
