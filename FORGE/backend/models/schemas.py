"""
schemas.py - all request/response Pydantic models for the FORGE API, plus the
two constant lists (EXPERIENCE_LEVELS, PRIMARY_GOALS) that both the engine and
the schemas need to agree on.

WHY THIS EXISTS
This used to live inline at the top of backend/main.py. Pulled out so that:
  - backend/services/program_builder.py can import WorkoutRequest/ProgramRequest
    without importing all of main.py (which would import program_builder.py
    right back - a cycle).
  - main.py stays focused on the engine + routes (Phase 2 of the roadmap:
    api/models/services split).

Nothing about field names, defaults, or validation changed for the schemas
that already existed in main.py - this is a pure move, except for the two
new WorkoutRequest fields (target_categories, target_muscles, exercise_limit)
and the new ProgramRequest model, both added to support the Program Builder
(backend/services/program_builder.py).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

EXPERIENCE_LEVELS = ["Beginner", "Novice", "Intermediate", "Advanced", "Elite"]

# The 8 goals the Program Builder wizard offers (spec: "Program Builder ->
# Primary Goal", extended with "Power / Explosiveness" for power/speed-
# focused athletes previously unserved by "Get Strong" (max strength) or
# "Athletic Performance" (general sport athleticism)). Keys of GOAL_PROFILES in program_builder.py must match this
# list exactly - GOAL_PROFILES falls back to "General Fitness" for anything
# unrecognized, but the API-facing list of *valid* choices is this one.
PRIMARY_GOALS = [
    "Build Muscle",
    "Get Strong",
    "Power / Explosiveness",
    "Lose Fat",
    "Athletic Performance",
    "Conditioning",
    "Skill Development",
    "General Fitness",
]

# The 4 energy-system emphases a coach would actually program a Conditioning/
# Jump/Power exercise's work:rest interval around, instead of one flat
# difficulty-only formula regardless of what the athlete is training:
#   - Alactic (Power/Speed) - phosphagen system, ~5-15s max-effort bursts,
#     near-full recovery between them (long rest so quality never degrades).
#   - Lactic (Anaerobic Capacity) - glycolytic system, ~20-60s sustained
#     high-output efforts, moderate incomplete recovery (the "burn" zone).
#   - Aerobic (Endurance) - steady-state / long intervals, short rest
#     relative to work so heart rate stays elevated across the set.
#   - Mixed - no specific emphasis; reproduces the engine's original
#     difficulty-only formula (default, fully backward compatible).
CONDITIONING_EMPHASES = ["Alactic", "Lactic", "Aerobic", "Mixed"]

# The 5 phases a competition-calendar-driven mesocycle moves through, per
# Combat Sports & Rugby S&C Manual Part 9.3 ("Periodization: Fitting S&C
# Into a Training Year"). Optional on ProgramRequest - omitting it (None,
# the default) preserves every existing caller's behavior exactly
# (days_per_week/goal/sport picks the split, as before). Setting it lets
# the Program Builder follow the manual's phase -> split -> volume ->
# conditioning-focus table instead (see program_builder.PHASE_GUIDANCE).
TRAINING_PHASES = [
    "Off-Season",
    "Pre-Season",
    "In-Season / Fight Camp",
    "Fight Week",
    "Post-Competition",
]


# ==========================================
# Shared building blocks
# ==========================================

class ProgressionOverride(BaseModel):
    exercise_id: str
    # Bounded length: this string round-trips straight into API responses
    # (and from there into the frontend's DOM), so it's kept short and plain
    # even though the web UI already HTML-escapes every name it renders -
    # belt and suspenders, and it stops absurdly large payloads too.
    custom_name: Optional[str] = Field(default=None, max_length=120)
    prerequisites: Optional[List[str]] = None
    equipment: Optional[str] = None
    difficulty: Optional[int] = None


class ReadinessInputs(BaseModel):
    """Optional breakdown behind the single `readiness` slider. Every field is
    optional and independent - send just the ones you actually collected (a
    quick-start caller can still send only `readiness` and skip this entirely).
    When any of these are present, the engine builds a weighted composite
    recovery score instead of using the flat `readiness` number alone, and
    poor sleep / high soreness specifically cap heavy compound-lift intensity
    even on a day where the overall composite doesn't dip into deload range -
    matching how a coach actually reasons ("bad sleep -> lighter on the big
    barbell lifts today", not just "everything x0.9").
    """
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=14, description="Hours slept last night.")
    soreness: Optional[int] = Field(default=None, ge=1, le=5, description="Muscle soreness: 1=none, 5=very sore.")
    stress: Optional[int] = Field(default=None, ge=1, le=5, description="Life/training stress: 1=low, 5=high.")
    energy: Optional[int] = Field(default=None, ge=1, le=5, description="Subjective energy: 1=low, 5=high.")
    motivation: Optional[int] = Field(default=None, ge=1, le=5, description="Motivation to train: 1=low, 5=high.")


class UserBiometrics(BaseModel):
    height_cm: float = Field(..., gt=0, description="Height in cm")
    weight_kg: float = Field(..., gt=0, description="Weight in kg")
    bench_press_1rm: Optional[float] = Field(default=0.0, ge=0, description="Bench Press 1RM in kg")
    squat_1rm: Optional[float] = Field(default=0.0, ge=0, description="Squat 1RM in kg")
    deadlift_1rm: Optional[float] = Field(default=0.0, ge=0, description="Deadlift 1RM in kg")
    pullups_max_reps: Optional[int] = Field(default=0, ge=0, description="Max unbroken bodyweight pull-ups")
    pushups_max_reps: Optional[int] = Field(default=0, ge=0, description="Max unbroken bodyweight push-ups")
    # Optional, and used for exactly one thing: picking which table
    # strength_standards.classify_strength_level() reads (male/female
    # thresholds diverge most in upper-body pressing, less in hip-dominant
    # lifts - see that module's docstring). Omitting it falls back to a
    # blended table, flagged lower-confidence rather than guessed.
    sex: Optional[Literal["male", "female"]] = Field(
        default=None,
        description="Optional - improves the accuracy of the strength-level estimate (GET/POST .../estimate-level). Omit for a blended, lower-confidence estimate.",
    )


# ==========================================
# Single-session request
# ==========================================

class WorkoutRequest(BaseModel):
    mode: Literal["preset", "custom"] = "preset"
    sport: str = "Special Forces"
    experience_level: Literal["Beginner", "Novice", "Intermediate", "Advanced", "Elite"] = "Intermediate"
    equipment_available: List[str] = Field(default_factory=lambda: ["Bodyweight"])
    readiness: int = Field(default=80, ge=1, le=100)
    readiness_inputs: Optional[ReadinessInputs] = Field(
        default=None,
        description="Optional sleep/soreness/stress/energy/motivation breakdown - see ReadinessInputs.",
    )
    injuries: List[str] = Field(
        default_factory=list,
        description=(
            "Active injuries. Prefer specific, severity-tagged entries from "
            "GET /api/v1/metadata's 'injuries' list, e.g. "
            "['ACL/Ligament Tear - Grade 2 (Partial Tear)', 'Rotator Cuff Tear - Small (<1cm)']"
            " - these carry a severity tier that scales how much difficulty is still safe "
            "on that joint. Bare joint names or legacy flat tags (e.g. 'Knee', "
            "'Tennis Elbow') still work as a hard block on any exercise stressing that joint."
        ),
    )
    biometrics: Optional[UserBiometrics] = None
    custom_progressions: Optional[List[ProgressionOverride]] = None

    # Which energy system Conditioning/Jump/Power exercises should be
    # prescribed for - see CONDITIONING_EMPHASES above. "Mixed" (default)
    # is fully backward compatible with every existing caller.
    conditioning_emphasis: Literal["Alactic", "Lactic", "Aerobic", "Mixed"] = "Mixed"

    # --- Custom mode (mode="custom") ---
    # When mode is "custom", the engine skips its own exercise selection and
    # instead evaluates exactly this list, in this order (still running every
    # equipment/injury/strength/level safety check per exercise, so a pick
    # that's genuinely unsafe still lands in excluded_exercises with why -
    # "custom" means "you choose the exercises", not "skip the safety net").
    # Ignored (behaves exactly as before) when mode is "preset" or this is empty.
    selected_exercise_ids: Optional[List[str]] = Field(
        default=None,
        description="Exercise ids to build the session from when mode='custom'. See GET /api/v1/exercises.",
    )

    # --- Program Builder support (backend/services/program_builder.py) ---
    # None/None/None (the default, and every existing single-session caller)
    # means "no session-focus filtering" - unchanged behavior for the plain
    # /api/v1/generate-workout endpoint. A program request scopes each day
    # to a slice of the database (e.g. a PPL "Push" day) by setting one or
    # both of target_categories/target_muscles; exercise_limit caps how many
    # exercises come back, sized off the requested session duration.
    target_categories: Optional[List[str]] = Field(
        default=None,
        description="Restrict to exercises whose category or movement_pattern is in this list.",
    )
    target_muscles: Optional[List[str]] = Field(
        default=None,
        description="Restrict to exercises whose primary/secondary muscles intersect this list.",
    )
    exercise_limit: Optional[int] = Field(default=None, ge=1, le=20)

    # --- Exercise variety / anti-repetition ---
    # Exercise ids used recently (e.g. last session, or the same day-slot in
    # a previous week of a program) - when the engine has to trim down to
    # exercise_limit, it prefers NOT to repeat these among near-tied
    # candidates for the same role, instead of always returning the single
    # highest-scoring exercise every time. Doesn't exclude them outright
    # (if nothing else qualifies, a repeat is still better than an empty
    # slot) - just deprioritizes them.
    exclude_exercise_ids: Optional[List[str]] = Field(
        default=None,
        description="Exercise ids to deprioritize (not hard-exclude) when trimming to exercise_limit, to avoid repeating recent picks.",
    )
    # Seeds the rotation among near-tied candidates so the same request run
    # twice with the same seed reproduces the same pick, but a different
    # seed (e.g. a different week number) can surface a different, equally
    # valid exercise instead of always the top scorer.
    variety_seed: int = Field(default=0, description="Seed controlling rotation among near-tied exercise choices.")


# ==========================================
# Multi-week program request (Program Builder)
# ==========================================

class ProgramRequest(BaseModel):
    primary_goal: Literal[
        "Build Muscle",
        "Get Strong",
        "Power / Explosiveness",
        "Lose Fat",
        "Athletic Performance",
        "Conditioning",
        "Skill Development",
        "General Fitness",
    ] = "General Fitness"
    sport: str = "Special Forces"
    experience_level: Literal["Beginner", "Novice", "Intermediate", "Advanced", "Elite"] = "Intermediate"
    equipment_available: List[str] = Field(default_factory=lambda: ["Bodyweight"])
    readiness: int = Field(default=80, ge=1, le=100)
    readiness_inputs: Optional[ReadinessInputs] = Field(
        default=None,
        description="Optional sleep/soreness/stress/energy/motivation breakdown - see ReadinessInputs.",
    )
    injuries: List[str] = Field(default_factory=list)
    biometrics: Optional[UserBiometrics] = None
    conditioning_emphasis: Literal["Alactic", "Lactic", "Aerobic", "Mixed"] = "Mixed"

    # Optional competition-calendar phase (see TRAINING_PHASES above). When
    # set, overrides the days/goal/sport split heuristic with the manual's
    # Part 9.3 phase table and scales session volume accordingly (see
    # program_builder.PHASE_GUIDANCE / _apply_phase_volume_scaling). None
    # (default) = unchanged legacy behavior.
    training_phase: Optional[Literal[
        "Off-Season", "Pre-Season", "In-Season / Fight Camp", "Fight Week", "Post-Competition",
    ]] = None

    days_per_week: int = Field(default=3, ge=1, le=7)
    weeks: int = Field(default=4, ge=1, le=16, description="Mesocycle length. 3+ weeks auto-appends a deload week.")
    session_duration_minutes: int = Field(default=60, ge=15, le=180)

    # A specific SPLIT_TEMPLATES key (see GET /api/v1/splits), or "auto" to
    # let recommend_split() pick one from days_per_week + primary_goal.
    preferred_split: str = "auto"
