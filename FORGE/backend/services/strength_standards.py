"""
strength_standards.py — turns raw 1RM / rep-max numbers into an *estimated*
overall training level (Beginner..Elite), instead of relying on self-report
alone.

WHY THIS EXISTS
`experience_level` (schemas.py) has always been a field the *person* picks
from a dropdown - nothing anywhere in the engine ever checked whether that
pick matched what their own numbers say. Self-assessed training level is
notoriously unreliable (most lifters over- or under-rate themselves), and
`experience_level` isn't cosmetic here - it's a hard ceiling on exercise
difficulty (main.py's `level_ok` check), on which split templates are even
offered (program_builder.py's `EXPERIENCE_SPLIT_ALLOWLIST`), and on which
periodization model gets used (linear vs. daily-undulating). A mis-stated
level quietly flows through all three - e.g. someone who's actually a
beginner but self-rates "Advanced" gets routed straight into a Bro Split or
PHAT, the exact "specialization before the technique/work-capacity base is
there" mismatch `program_builder.py` already warns about in its own
comments.

This module doesn't override the person's stated `experience_level` - it
computes a second, independent estimate from their actual lift numbers
(relative to bodyweight) and bodyweight-exercise rep maxes, so the frontend
can suggest/pre-fill a level and show its work, while the person keeps
final say. See `backend/main.py`'s `POST /api/v1/estimate-level` and
`evaluate_biometrics_and_strength`.

THE STANDARDS THEMSELVES
Bodyweight-ratio thresholds below are *approximate*, commonly-cited
benchmarks in the strength-training community (the same rough shape you'll
see published across sources like Lon Kilgore's standards tables,
StrengthLevel.com's aggregated lifter data, and ExRx.net's strength
standards) - not a clinical or federation-verified scale, and different
sources disagree by 10-20% at the margins. Treat this as a reasonable,
transparent default a person can always override by hand, not a verdict.

Men's and women's tables are kept separate rather than one table scaled by
a flat percentage: the sex gap in relative (bodyweight-adjusted) strength is
well-documented as uneven across movements - largest in upper-body pressing,
smaller in hip-dominant lifts like the squat and deadlift - so a single
scaled table would misrepresent that shape. Sex is optional; omitting it
falls back to a blended men's/women's table, flagged as lower-confidence.
"""

import math
from typing import Dict, List, Optional

EXPERIENCE_LEVELS = ["Beginner", "Novice", "Intermediate", "Advanced", "Elite"]

# ratio = 1RM / bodyweight, both in the same units. Each value is the
# MINIMUM ratio to be considered "at" that level - Beginner's own threshold
# is the floor (below it is still Beginner; there's no lower tier to fall
# into).
_BARBELL_STANDARDS: Dict[str, Dict[str, List[float]]] = {
    "male": {
        "bench_press_1rm": [0.50, 0.75, 1.00, 1.50, 2.00],
        "squat_1rm":       [0.75, 1.00, 1.50, 2.00, 2.50],
        "deadlift_1rm":    [1.00, 1.50, 2.00, 2.50, 3.00],
    },
    "female": {
        "bench_press_1rm": [0.35, 0.50, 0.75, 1.00, 1.25],
        "squat_1rm":       [0.50, 0.75, 1.25, 1.75, 2.25],
        "deadlift_1rm":    [0.75, 1.25, 1.75, 2.25, 2.75],
    },
}

# Reps, not a ratio - unbroken/strict max.
_BODYWEIGHT_STANDARDS: Dict[str, Dict[str, List[float]]] = {
    "male": {
        "pullups_max_reps": [1, 3, 8, 15, 20],
        "pushups_max_reps": [10, 20, 35, 50, 70],
    },
    "female": {
        "pullups_max_reps": [0, 1, 5, 10, 15],
        "pushups_max_reps": [5, 12, 20, 35, 50],
    },
}

_METRIC_LABELS = {
    "bench_press_1rm": "Bench Press",
    "squat_1rm": "Squat",
    "deadlift_1rm": "Deadlift",
    "pullups_max_reps": "Pull-ups",
    "pushups_max_reps": "Push-ups",
}


def _blended(table: Dict[str, Dict[str, List[float]]], key: str) -> List[float]:
    """Average of the men's/women's thresholds for one metric - used only
    when sex isn't given. Flagged by callers as lower-confidence, since it
    doesn't match either table's actual tested population, but that beats
    refusing to estimate at all."""
    male = table["male"][key]
    female = table["female"][key]
    return [round((m + f) / 2, 3) for m, f in zip(male, female)]


def _standards_for(sex: Optional[str]) -> (Dict[str, List[float]], Dict[str, List[float]]):
    sex_key = sex if sex in ("male", "female") else None
    if sex_key:
        return _BARBELL_STANDARDS[sex_key], _BODYWEIGHT_STANDARDS[sex_key]
    barbell = {k: _blended(_BARBELL_STANDARDS, k) for k in _BARBELL_STANDARDS["male"]}
    bodyweight = {k: _blended(_BODYWEIGHT_STANDARDS, k) for k in _BODYWEIGHT_STANDARDS["male"]}
    return barbell, bodyweight


def _bucket(value: float, thresholds: List[float]) -> int:
    """Index (0-4) of the highest tier `value` clears. Never negative -
    below the Beginner threshold is still tier 0 (Beginner); it just means
    "early" Beginner rather than a lower tier that doesn't exist."""
    idx = 0
    for i, t in enumerate(thresholds):
        if value >= t:
            idx = i
    return idx


def _progress_note(value: float, unit_label: str, thresholds: List[float], idx: int) -> str:
    level = EXPERIENCE_LEVELS[idx]
    formatted = f"{value:.2f}{unit_label}"
    if idx == len(thresholds) - 1:
        return f"{formatted} — {level} (at or above the highest commonly-published benchmark)"
    nxt = thresholds[idx + 1]
    return f"{formatted} — {level} ({EXPERIENCE_LEVELS[idx + 1]} starts around {nxt:.2f}{unit_label})"


def classify_strength_level(
    *,
    weight_kg: float,
    bench_press_1rm: float = 0.0,
    squat_1rm: float = 0.0,
    deadlift_1rm: float = 0.0,
    pullups_max_reps: float = 0,
    pushups_max_reps: float = 0,
    sex: Optional[str] = None,
) -> Dict:
    """Best-effort *estimate* of overall training level from whatever
    metrics are actually present.

    0 is treated as "not entered" for every metric here, not as a real max
    of zero - the same convention `evaluate_biometrics_and_strength` already
    uses elsewhere in this engine (a 1RM of 0 means "untested", not "can't
    lift anything"), applied consistently rather than re-decided per field.

    Returns `level: None` with a plain explanation if nothing usable was
    entered (need a positive `weight_kg` and at least one lift or rep-max
    above zero) - callers should fall back to letting the person self-report
    rather than guessing from nothing.
    """
    barbell, bodyweight_std = _standards_for(sex)
    sex_key = sex if sex in ("male", "female") else None

    breakdown: List[Dict] = []
    ranks: List[int] = []

    if weight_kg and weight_kg > 0:
        for key, raw in (
            ("bench_press_1rm", bench_press_1rm),
            ("squat_1rm", squat_1rm),
            ("deadlift_1rm", deadlift_1rm),
        ):
            if raw and raw > 0:
                ratio = raw / weight_kg
                idx = _bucket(ratio, barbell[key])
                ranks.append(idx)
                breakdown.append({
                    "metric": _METRIC_LABELS[key],
                    "value": round(ratio, 2),
                    "unit": "x bodyweight",
                    "estimated_level": EXPERIENCE_LEVELS[idx],
                    "note": _progress_note(ratio, "x BW", barbell[key], idx),
                })

    for key, raw in (
        ("pullups_max_reps", pullups_max_reps),
        ("pushups_max_reps", pushups_max_reps),
    ):
        if raw and raw > 0:
            idx = _bucket(raw, bodyweight_std[key])
            ranks.append(idx)
            breakdown.append({
                "metric": _METRIC_LABELS[key],
                "value": raw,
                "unit": "reps",
                "estimated_level": EXPERIENCE_LEVELS[idx],
                "note": _progress_note(raw, " reps", bodyweight_std[key], idx),
            })

    if not ranks:
        return {
            "level": None,
            "level_rank": None,
            "confidence": "none",
            "metrics_used": 0,
            "breakdown": [],
            "rationale": (
                "Not enough data to estimate a level yet - enter at least one 1RM "
                "(bench/squat/deadlift) or a pull-up/push-up max."
            ),
        }

    avg_rank = sum(ranks) / len(ranks)
    # Explicit round-half-up rather than bare round() (Python's round() uses
    # round-half-to-even, so an exact tie like 2.5 would silently go to 2,
    # not 3) - a tie between two adjacent tiers is genuinely ambiguous, and
    # rounding up is the more defensible default given the ceiling checks
    # downstream (level_ok, EXPERIENCE_SPLIT_ALLOWLIST) already treat the
    # stated level conservatively elsewhere.
    overall_idx = max(0, min(4, math.floor(avg_rank + 0.5)))
    confidence = "high" if len(ranks) >= 3 else ("medium" if len(ranks) == 2 else "low")
    sex_note = "" if sex_key else " (sex not given, so this uses a blended men's/women's table - less precise)"

    return {
        "level": EXPERIENCE_LEVELS[overall_idx],
        "level_rank": round(avg_rank, 2),
        "confidence": confidence,
        "metrics_used": len(ranks),
        "breakdown": breakdown,
        "rationale": (
            f"Based on {len(ranks)} metric{'s' if len(ranks) != 1 else ''} entered, this "
            f"looks like {EXPERIENCE_LEVELS[overall_idx]} overall{sex_note}."
        ),
    }


def level_check(stated_level: str, estimate: Dict) -> Dict:
    """Compares a person's self-reported `experience_level` against the
    independent estimate from `classify_strength_level`, for display
    alongside a session or program response.

    This is the one place that reasons about the *gap* between stated and
    estimated - callers (main.py's `generate_session`, program_builder.py's
    `generate_program`) both need this same comparison and shouldn't each
    re-derive their own gap thresholds/wording, which would drift apart the
    first time one gets tuned and the other doesn't.

    Advisory only, same as the module as a whole: never changes level_ok,
    EXPERIENCE_SPLIT_ALLOWLIST, or which periodization model gets picked -
    those still key off `stated_level` exactly as before. This just makes a
    mismatch *visible* instead of silently flowing through, per the module
    docstring - the frontend can act on it (e.g. suggest updating the
    dropdown); the engine itself doesn't.
    """
    estimated_level = estimate.get("level")
    result = {
        "stated_level": stated_level,
        "estimated_level": estimated_level,
        "confidence": estimate.get("confidence", "none"),
        "metrics_used": estimate.get("metrics_used", 0),
        "agrees": None,
        "note": None,
    }

    if estimated_level is None:
        result["note"] = (
            "Not enough lift data entered to estimate a level - using your selected "
            f"'{stated_level}' as-is."
        )
        return result

    if stated_level not in EXPERIENCE_LEVELS:
        result["note"] = (
            f"Numbers entered suggest '{estimated_level}' - no valid stated level to compare against."
        )
        return result

    stated_rank = EXPERIENCE_LEVELS.index(stated_level)
    estimated_rank = EXPERIENCE_LEVELS.index(estimated_level)
    gap = estimated_rank - stated_rank
    result["agrees"] = gap == 0

    if gap == 0:
        result["note"] = f"Your entered numbers line up with your selected '{stated_level}'."
    elif gap > 0:
        result["note"] = (
            f"Your entered numbers look more like '{estimated_level}' than your selected "
            f"'{stated_level}' - this was still built for '{stated_level}'. Update your "
            "level if you want it to reflect the higher one."
        )
    else:
        result["note"] = (
            f"Your entered numbers look more like '{estimated_level}' than your selected "
            f"'{stated_level}' - this was still built for '{stated_level}'. Update your "
            "level if you'd rather train at the lower one."
        )
    return result
