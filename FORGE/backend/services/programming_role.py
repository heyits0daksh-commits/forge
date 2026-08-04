"""
programming_role.py — what job an exercise does INSIDE a session, and where
a coach would put it in the running order.

WHY THIS EXISTS
Every prior version of FORGE produced a workout as a bag of qualifying
exercises sorted by a single sport-priority number. That's a filter, not a
session - a real coach doesn't run a max-effort deadlift after twelve minutes
of conditioning, and doesn't bury a technical throw-entry drill at the end of
a session once the CNS is fried. Sequencing is part of what "reasoning like a
coach" means, and it's driven by fields the engine already derives (category,
force_type, CNS_fatigue, difficulty) - so, same principle as
exercise_metadata.py and sport_profiles.py, this is one small ruleset applied
consistently rather than a hand-typed order per exercise.

ROLE TAXONOMY (session_order_rank = the order a coach runs them in):
    1. Primer / Activation   - low-fatigue, low-difficulty stability/mobility
                                work that wakes a joint/pattern up.
    2. Skill / Technical     - sport-specific technical work; needs a fresh
                                CNS more than it needs load.
    3. Power & Explosive     - jumps/throws/ballistic work; also needs CNS
                                freshness, done before heavy grinding lifts.
    4. Primary Strength      - the heavy loaded lifts the session is built
                                around.
    5. Accessory / Hypertrophy - lighter loaded work, built after the main
                                lift(s), tolerant of accumulated fatigue.
    6. Core & Stability      - trunk/grip/carry work; deliberately placed
                                after strength work, since a fatigued trunk
                                under light load is still safe and effective.
    7. Conditioning / Finisher - the highest metabolic-fatigue work, run last
                                so it doesn't compromise technique or load
                                elsewhere in the session.
"""

from typing import Dict, Tuple

ROLE_ORDER = [
    "Primer / Activation",
    "Skill / Technical",
    "Power & Explosive",
    "Primary Strength",
    "Accessory / Hypertrophy",
    "Core & Stability",
    "Conditioning / Finisher",
]
ROLE_RANK = {role: i + 1 for i, role in enumerate(ROLE_ORDER)}

_LOADED_STRENGTH_CATEGORIES = {
    "Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull",
    "Squat", "Hinge",
}
_TRUNK_CATEGORIES = {"Core", "Grip", "Carry"}


def classify_programming_role(ex: Dict) -> Tuple[str, str]:
    """Returns (role, rationale). Pure function of fields the exercise
    already carries (category, force_type, CNS_fatigue, fatigue_cost,
    difficulty) - no per-exercise hand-tagging required."""
    category = ex.get("category", "")
    force_type = ex.get("force_type", "")
    difficulty = ex.get("difficulty", 1)
    cns_fatigue = ex.get("CNS_fatigue", difficulty * 15)
    fatigue_cost = ex.get("fatigue_cost", difficulty * 14)

    if category == "Conditioning" or fatigue_cost >= 60:
        return (
            "Conditioning / Finisher",
            "High metabolic fatigue cost - placed last so it doesn't compromise technique or load elsewhere.",
        )

    if category == "Sport Specific":
        return (
            "Skill / Technical",
            "Sport-specific technical work - sequenced early, while the CNS is still fresh enough for precision.",
        )

    if category in ("Jump", "Power") or force_type == "Stretch-Shortening Cycle":
        return (
            "Power & Explosive",
            "Reactive/ballistic output degrades fast with fatigue - run before the grinding strength work.",
        )

    if category in _TRUNK_CATEGORIES:
        if difficulty >= 3:
            return (
                "Core & Stability",
                "Demanding trunk/grip/carry work - tolerant of accumulated fatigue, so it runs after strength work.",
            )
        return (
            "Primer / Activation",
            "Low-difficulty stability work - suited to waking the pattern up before the session loads it.",
        )

    if category in _LOADED_STRENGTH_CATEGORIES:
        if difficulty >= 3:
            return (
                "Primary Strength",
                "The heaviest loaded lift class in this category - the session is built around it.",
            )
        return (
            "Accessory / Hypertrophy",
            "Lighter loaded work - built around the main lift(s), tolerant of accumulated fatigue.",
        )

    if difficulty <= 2 and cns_fatigue < 30:
        return (
            "Primer / Activation",
            "Low CNS demand - suited to waking the pattern up early in the session.",
        )

    return (
        "Accessory / Hypertrophy",
        "General supporting work - slotted after the session's primary demands.",
    )


def session_order_rank(role: str) -> int:
    return ROLE_RANK.get(role, len(ROLE_ORDER))
