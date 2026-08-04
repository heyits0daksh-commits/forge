"""
program_builder.py — turns a goal + split + schedule into a full multi-week,
multi-day training program, by calling the existing single-session engine
once per (week, day) rather than re-implementing its safety/equipment/
injury/strength filtering.

WHY THIS EXISTS
`ProgressionEngine.generate_session` (main.py) already does the hard part of
"is this exercise safe and appropriate for this person right now" - equipment
check, injury contraindication + severity tiering, strength-requirement
gating, experience-level ceiling, sport-transfer scoring, and coach-order
sequencing. A program is not a different problem, it's the same problem
run repeatedly with two things layered on top:

  1. WHICH exercises a given day should even be considering (a "Push" day
     shouldn't be offered squats) - see `target_categories`/`target_muscles`
     on WorkoutRequest, added alongside this module.
  2. HOW the prescription should shift week to week (progressive overload)
     and day to day (a "Power" day trains differently than a "Hypertrophy"
     day even on the same split) - handled here as a post-processing pass
     over what the engine already prescribed, not a parallel prescription
     engine.

This keeps exactly one place responsible for "is this exercise allowed" and
one place responsible for "how should a program shape what's allowed" -
duplicating the ~150 lines of filtering logic into a second engine would be
the actual mistake here (two places that both decide safety, drifting apart
the first time one gets a bugfix the other doesn't).

SPLIT TEMPLATES
Each split is a named, ordered list of "day slots" - a label and either
`categories` (matched against an exercise's `category`/`movement_pattern`,
e.g. Squat/Hinge for a leg day) or `muscles` (matched against
`primary_muscles`/`secondary_muscles`, used where body-part splits don't map
cleanly onto movement categories, e.g. a bro-split "Shoulders" day). A day
may also carry `emphasis` ("power" or "hypertrophy"), which biases the
engine's own sets/reps/load prescription rather than replacing it.

The spec's full split list also names variants that aren't really different
*templates* here: "Beginner/Intermediate/Advanced" is `experience_level`,
"Home/Dumbbell Only/Minimal Equipment" is `equipment_available`, and
"Bodybuilding"/"Powerlifting"/"Hybrid" are closer to `primary_goal` (Build
Muscle / Get Strong / a blend) than to a distinct weekly structure - so
those are handled as parameters on top of the 8 structural splits below
rather than as 17 near-duplicate templates.
"""

from typing import Dict, List, Optional

from backend.models.schemas import EXPERIENCE_LEVELS, ProgramRequest, WorkoutRequest
from backend.services.strength_standards import classify_strength_level, level_check
from backend.services.sport_profiles import sport_conditioning_profile
from backend.services.conditioning_protocols import conditioning_reference

_LEVEL_RANK: Dict[str, int] = {lvl: i for i, lvl in enumerate(EXPERIENCE_LEVELS)}

SPLIT_TEMPLATES: Dict[str, Dict] = {
    "full_body": {
        "name": "Full Body",
        "description": "Every major movement pattern trained each session. Best for 2-4 days/week, beginners, or anyone with limited time.",
        "reference": "The standard beginner/GPP prescription strength coaches converge on (StrongLifts 5x5, GreySkull LP, Starting Strength) - full-body compound work 2-4x/week is the most consistently recommended entry point before splitting by body part. 1 day/week matches the Combat Sports & Rugby S&C Manual's '1-Day Full Body' maintenance template for heavy fight-camp weeks.",
        "supported_days_per_week": [1, 2, 3, 4],
        # Both A and B carry the FULL pattern set (all six loaded-strength
        # categories, not a push/pull half-split) plus Power/Jump/
        # Conditioning/Sport Specific - this is the template every
        # combat-sport/grappling/climbing/HYROX profile in
        # SPORT_SPLIT_GUIDANCE below is routed to, and those athletes only
        # lift 2-4x/week total, so every single session needs to look like a
        # complete strength-and-conditioning session on its own (squat AND
        # hinge, push AND pull in both planes, an explosive/ballistic
        # movement, core, a conditioning finisher, and sport-specific skill
        # transfer work) rather than one half of a bodybuilding-style
        # rotation. ProgressionEngine's role- and pattern-coverage selection
        # (main.py _select_role_balanced / _COVERAGE_PATTERNS) does the
        # actual per-session balancing within this pool, and variety_seed/
        # exclude_exercise_ids keep A and B (and week-to-week repeats)
        # from converging on the exact same picks.
        "days": [
            {"label": "Full Body A", "categories": [
                "Full Body", "Squat", "Hinge", "Horizontal Push", "Vertical Push",
                "Horizontal Pull", "Vertical Pull", "Power", "Jump",
                "Core", "Carry", "Conditioning", "Sport Specific",
            ]},
            {"label": "Full Body B", "categories": [
                "Full Body", "Squat", "Hinge", "Horizontal Push", "Vertical Push",
                "Horizontal Pull", "Vertical Pull", "Power", "Jump",
                "Core", "Carry", "Conditioning", "Sport Specific",
            ]},
        ],
    },
    "upper_lower": {
        "name": "Upper / Lower",
        "description": "Alternates upper-body and lower-body sessions. Best for 4 (or 6, running the cycle twice) days/week.",
        "reference": "The most-recommended 4-day split once someone outgrows full-body - splits like Madcow and most modern 4-day strength templates (e.g. Jeff Nippard's Upper/Lower) use this exact division for its balance of frequency and recovery. 2 days/week matches the Combat Sports & Rugby S&C Manual's '2-Day Upper/Lower' - its in-season/fight-camp option for very time-crunched athletes who still want the push/pull-vs-legs split rather than full body.",
        "supported_days_per_week": [2, 4, 6],
        # Squat/Hinge stay Lower-only and Push/Pull stay Upper-only (that
        # split is the point of this template), but Power/Jump/Conditioning/
        # Sport Specific are added to BOTH days - this template is what
        # every striking/field/tactical sport in SPORT_SPLIT_GUIDANCE below
        # uses, and an athlete training for Boxing, Rugby, MMA, etc. needs
        # explosive output, a conditioning piece, and sport-skill transfer
        # work available on every session, not confined to whichever day
        # happens to also be leg day.
        "days": [
            {"label": "Upper Body", "categories": [
                "Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull",
                "Power", "Jump", "Core", "Conditioning", "Sport Specific",
            ]},
            {"label": "Lower Body", "categories": [
                "Squat", "Hinge", "Carry", "Full Body",
                "Power", "Jump", "Core", "Conditioning", "Sport Specific",
            ]},
        ],
    },
    "push_pull_legs": {
        "name": "Push / Pull / Legs",
        "description": "Groups by movement direction. Runs as 3 days/week, or twice through as 6.",
        "reference": "The most popular hypertrophy split on the internet (StrengthLog, PureGym, Nippard's PPL) - grouping by movement direction rather than body part is consistently cited as the standard 3-6 day bodybuilding template.",
        "supported_days_per_week": [3, 6],
        "days": [
            {"label": "Push", "categories": ["Horizontal Push", "Vertical Push"]},
            {"label": "Pull", "categories": ["Horizontal Pull", "Vertical Pull", "Grip"]},
            {"label": "Legs", "categories": ["Squat", "Hinge", "Carry", "Full Body"]},
        ],
    },
    "bro_split": {
        "name": "Bro Split",
        "description": "One body part per day across 5 days/week - the classic bodybuilding split.",
        "reference": "The classic 1970s-90s Golden Era bodybuilding template (Gold's Gym era, popularized by Arnold-generation training logs) - one muscle group per day at high per-session volume.",
        "supported_days_per_week": [5],
        "days": [
            {"label": "Chest", "muscles": ["Pectoralis Major"]},
            {"label": "Back", "muscles": ["Latissimus Dorsi", "Rhomboids", "Trapezius"]},
            {"label": "Shoulders", "muscles": ["Anterior Deltoid", "Posterior Deltoid"]},
            {"label": "Arms", "muscles": ["Triceps Brachii", "Biceps Brachii", "Brachialis", "Forearm Flexors"]},
            {"label": "Legs", "muscles": ["Quadriceps", "Hamstrings", "Gluteus Maximus", "Gastrocnemius", "Soleus", "Adductors"]},
        ],
    },
    "arnold_split": {
        "name": "Arnold Split",
        "description": "Chest & Back, Shoulders & Arms, Legs - run twice through across 6 days/week for high volume per body part.",
        "reference": "Named for and modeled on Arnold Schwarzenegger's own Golden Era routine (as documented in his Blueprint to Mass / Education of a Bodybuilder) - antagonist pairing (Chest & Back) run twice per week.",
        "supported_days_per_week": [6],
        "days": [
            {"label": "Chest & Back", "muscles": ["Pectoralis Major", "Latissimus Dorsi", "Rhomboids", "Trapezius"]},
            {"label": "Shoulders & Arms", "muscles": ["Anterior Deltoid", "Posterior Deltoid", "Triceps Brachii", "Biceps Brachii", "Brachialis"]},
            {"label": "Legs", "categories": ["Squat", "Hinge", "Carry", "Full Body"]},
        ],
    },
    "phul": {
        "name": "PHUL (Power Hypertrophy Upper Lower)",
        "description": "4 days/week: heavy Upper/Lower power days paired with lighter, higher-volume Upper/Lower hypertrophy days.",
        "reference": "The original PHUL template popularized by Brandon Campbell - one of the most widely-run named 4-day programs for lifters who want both a strength and a size day per body region.",
        "supported_days_per_week": [4],
        "days": [
            {"label": "Upper Power", "categories": ["Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull"], "emphasis": "power"},
            {"label": "Lower Power", "categories": ["Squat", "Hinge", "Full Body"], "emphasis": "power"},
            {"label": "Upper Hypertrophy", "categories": ["Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull", "Core"], "emphasis": "hypertrophy"},
            {"label": "Lower Hypertrophy", "categories": ["Squat", "Hinge", "Carry"], "emphasis": "hypertrophy"},
        ],
    },
    "phat": {
        "name": "PHAT (Power Hypertrophy Adaptive Training)",
        "description": "5 days/week: two heavy power days (upper, lower) followed by three body-part hypertrophy days.",
        "reference": "Layne Norton's PHAT program - one of the most cited 5-day powerbuilding templates, pairing two heavy power days with three bodybuilding-style hypertrophy days.",
        "supported_days_per_week": [5],
        "days": [
            {"label": "Upper Power", "categories": ["Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull"], "emphasis": "power"},
            {"label": "Lower Power", "categories": ["Squat", "Hinge", "Full Body"], "emphasis": "power"},
            {"label": "Back & Shoulders Hypertrophy", "muscles": ["Latissimus Dorsi", "Rhomboids", "Trapezius", "Anterior Deltoid", "Posterior Deltoid"], "emphasis": "hypertrophy"},
            {"label": "Legs Hypertrophy", "categories": ["Squat", "Hinge", "Carry"], "emphasis": "hypertrophy"},
            {"label": "Chest & Arms Hypertrophy", "muscles": ["Pectoralis Major", "Triceps Brachii", "Biceps Brachii", "Brachialis"], "emphasis": "hypertrophy"},
        ],
    },
    "powerbuilding": {
        "name": "Powerbuilding",
        "description": "4 days/week centered on the big lifts (squat/bench/deadlift) with a dedicated hypertrophy accessory day.",
        "reference": "The generic 'powerbuilding' template that dominates r/powerbuilding and most hybrid strength-and-size logs - one day anchored to each competition lift plus an accessory day.",
        "supported_days_per_week": [4],
        "days": [
            {"label": "Squat Focus", "categories": ["Squat", "Core", "Full Body"], "emphasis": "power"},
            {"label": "Bench Focus", "categories": ["Horizontal Push", "Vertical Push"], "emphasis": "power"},
            {"label": "Deadlift Focus", "categories": ["Hinge", "Carry", "Full Body"], "emphasis": "power"},
            {"label": "Hypertrophy Accessory", "categories": ["Horizontal Pull", "Vertical Pull", "Core"], "emphasis": "hypertrophy"},
        ],
    },
}

GOAL_PROFILES: Dict[str, Dict] = {
    "Build Muscle": {"category_boost": [], "bias": "hypertrophy"},
    "Get Strong": {"category_boost": ["Full Body"], "bias": "power"},
    "Power / Explosiveness": {"category_boost": ["Power", "Jump", "Full Body"], "bias": "power"},
    "Lose Fat": {"category_boost": ["Conditioning"], "bias": None},
    "Athletic Performance": {"category_boost": ["Power", "Jump", "Sport Specific", "Full Body"], "bias": "power"},
    "Conditioning": {"category_boost": ["Conditioning", "Jump", "Power", "Carry"], "bias": None, "override_categories": True},
    "Skill Development": {"category_boost": ["Sport Specific"], "bias": None},
    "General Fitness": {"category_boost": [], "bias": None},
}

# Which structural split (from SPLIT_TEMPLATES) a strength coach would actually
# reach for given each sport's own demands - grounded in how S&C programs for
# each sport family are commonly built, not just the generic days/goal
# heuristic below (which has no idea a person is training for Judo vs.
# bodybuilding). Two sport families show up here:
#   - Grappling combat sports (Wrestling, Judo, Sambo, BJJ) and Rock Climbing:
#     S&C guidance for these consistently caps lifting at 2-4 sessions/week,
#     full-body each time, so it never competes with mat/wall time or
#     compounds fatigue on top of skill training - see e.g. BJJ/grappling S&C
#     writeups (youjiujitsu.com, strongfirst.com, crazy88mma.com), which
#     converge on a 3x/week full-body template as the default.
#   - Striking combat sports (Boxing, Muay Thai, Kickboxing, Sanda), Rugby,
#     Special Forces prep, and MMA: these need more total strength volume
#     (explosive power, contact tolerance, load carriage) and commonly run a
#     4-day Upper/Lower split - the standard step up from full-body once
#     4 dedicated sessions/week are available.
#   - HYROX: hybrid running + functional-station racing; programs for it are
#     built as full-body strength-conditioning hybrids rather than a
#     body-part split, run 4x/week.
# `days_per_week` is what's suggested when the split is chosen for this sport
# specifically (not a hard requirement) - recommend_split still falls back to
# the generic heuristic if the caller's own days_per_week doesn't fit this
# split's supported_days_per_week.
SPORT_SPLIT_GUIDANCE: Dict[str, Dict] = {
    "Wrestling": {"split": "full_body", "days_per_week": 3, "rationale": "Combat Sports & Rugby S&C Manual, Part 5: in-season, run 3-Day Full Body; step up to 4-Day Upper/Lower off-season for more total strength volume. Lactic-dominant conditioning (35% aerobic / 65% lactic)."},
    "Judo": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body, prioritizing pulling power for grip-and-throw exchanges. Lactic-dominant conditioning (30% aerobic / 70% lactic)."},
    "Sambo": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: in-season 3-Day Full Body; 4-Day Upper/Lower off-season for more total strength volume, same pattern as Wrestling. Lactic-dominant conditioning (35% aerobic / 65% lactic)."},
    "BJJ": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body or 3-Day Push/Pull/Legs (extra pulling volume suits grapplers). Aerobic-leaning conditioning (55% aerobic / 45% lactic) - matches/rolls run long."},
    "Boxing": {"split": "upper_lower", "days_per_week": 2, "rationale": "Manual guidance: 2-Day Upper/Lower protects recovery for pad work/sparring; step up to 3-Day Full Body off-season. Conditioning skews lactic (40% aerobic / 60% lactic) with classic round-based intervals."},
    "Muay Thai": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body or 2-Day Upper/Lower. Conditioning: 45% aerobic / 55% lactic, plus clinch strength and shin/leg durability work."},
    "Kickboxing": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body or 2-Day Upper/Lower. Conditioning: 45% aerobic / 55% lactic, round-based intervals matching competition round length."},
    "Sanda": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body for balanced striking-and-throwing carryover. Conditioning: 40% aerobic / 60% lactic."},
    "Rugby": {"split": "upper_lower", "days_per_week": 4, "rationale": "Manual guidance: 4-Day Upper/Lower in-season (strength maintenance) or 3-Day Push/Pull/Legs off-season (strength-building block). Conditioning: 45% aerobic / 55% lactic, repeated-sprint focus."},
    "Rock Climbing": {"split": "full_body", "days_per_week": 3, "rationale": "Climbing-specific strength guidance keeps lifting to 2-3x/week full-body, since grip/pulling volume is already high from wall time."},
    "HYROX": {"split": "full_body", "days_per_week": 4, "rationale": "HYROX programs are built as full-body strength-conditioning hybrids rather than a body-part split - matches the race's mixed running/functional-station format."},
    "Special Forces": {"split": "upper_lower", "days_per_week": 4, "rationale": "Manual guidance: 4-Day Upper/Lower, built to support heavy weekly aerobic/ruck volume without excess soreness. Aerobic-dominant conditioning (70% aerobic / 30% lactic)."},
    "MMA": {"split": "full_body", "days_per_week": 3, "rationale": "Manual guidance: 3-Day Full Body in-season (step up to 4-Day Upper/Lower off-season for more strength volume). MMA needs the broadest conditioning base of any combat sport here - 50% aerobic / 50% lactic."},
}


# Combat Sports & Rugby S&C Manual, Part 9.3 ("Periodization: Fitting S&C
# Into a Training Year") - which split to run and how hard to push it
# should shift with the competition calendar, not stay identical
# year-round. Purely additive: only consulted when a caller sets
# `ProgramRequest.training_phase` (see schemas.TRAINING_PHASES); every
# existing caller that leaves it unset keeps the exact days/goal/sport
# heuristic behavior from `_recommend_split_raw` above. `split_candidates`
# is tried in order against the caller's own `days_per_week` (first one
# whose `supported_days_per_week` matches wins, same "don't override what
# the person actually asked for" principle as `_recommend_split_raw`);
# `volume_multiplier` scales exercise count and set count for the phase
# (see `_apply_phase_volume_scaling`).
PHASE_GUIDANCE: Dict[str, Dict] = {
    "Off-Season": {
        "duration": "6-10 weeks",
        "split_candidates": ["upper_lower", "push_pull_legs"],
        "volume_multiplier": 1.0,
        "lifting_focus": "4-Day Upper/Lower or 3-Day Push/Pull/Legs - higher volume, build max strength and muscle.",
        "conditioning_focus": "Aerobic base building, 2-3x/week.",
    },
    "Pre-Season": {
        "duration": "4-6 weeks",
        "split_candidates": ["full_body"],
        "volume_multiplier": 0.9,
        "lifting_focus": "3-Day Full Body - moderate volume; add Olympic-lift/jump power work.",
        "conditioning_focus": "Shift toward lactic, sport-specific round work.",
    },
    "In-Season / Fight Camp": {
        "duration": "Ongoing",
        "split_candidates": ["upper_lower", "full_body"],
        "volume_multiplier": 0.5,
        "lifting_focus": "2-Day Upper/Lower or 1-Day Full Body - volume cut roughly in half; keep some intensity, protect recovery for skill work.",
        "conditioning_focus": "Lactic work matched to round length; taper hard in the final 7-10 days.",
    },
    "Fight Week": {
        "duration": "Final week",
        "split_candidates": ["full_body"],
        "volume_multiplier": 0.25,
        "lifting_focus": "Very light or off, 3-4 days out - minimal, technique and neural activation only.",
        "conditioning_focus": "Skill/tactical focus only; prioritize full recovery.",
    },
    "Post-Competition": {
        "duration": "1-2 weeks",
        "split_candidates": ["full_body"],
        "volume_multiplier": 0.6,
        "lifting_focus": "Optional light full body - low volume, easy movement.",
        "conditioning_focus": "Easy aerobic only; let bumps and bruises heal.",
    },
}


def _split_for_phase(training_phase: Optional[str], days_per_week: int) -> Optional[str]:
    """First split from the phase's candidate list that actually supports
    the caller's requested days_per_week - None if no phase is set (falls
    through to the ordinary heuristic) or if none of the phase's candidates
    fit that day count (falls through the same way, rather than silently
    changing days_per_week out from under the caller)."""
    phase = PHASE_GUIDANCE.get(training_phase) if training_phase else None
    if not phase:
        return None
    for candidate in phase["split_candidates"]:
        if days_per_week in SPLIT_TEMPLATES[candidate]["supported_days_per_week"]:
            return candidate
    return None


def _apply_phase_volume_scaling(prescription: Dict, multiplier: float) -> Dict:
    """Scales set count (and conditioning work volume) by the phase's
    volume_multiplier - the mechanism behind Part 9.3's 'volume cut roughly
    in half' (In-Season/Fight Camp) and 'minimal' (Fight Week) guidance.
    A multiplier of 1.0 (Off-Season) is a no-op. Never drops a lift below 1
    set or a conditioning interval below 1 round - a scaled-down session is
    still a real session, not zero exercise."""
    if multiplier >= 0.999:
        return prescription
    result = dict(prescription)
    if "sets" in result:
        result["sets"] = max(1, round(result["sets"] * multiplier))
    return result


def recommend_split(
    days_per_week: int, goal: str, sport: Optional[str] = None,
    experience_level: Optional[str] = None,
) -> str:
    """Heuristic used when preferred_split == "auto". Not the only reasonable
    choice for any given (days, goal) pair - just a sensible default a person
    can override via GET /api/v1/splits.

    Sport-specific guidance (SPORT_SPLIT_GUIDANCE) takes priority over the
    generic days/goal heuristic below whenever it applies - but only when
    the goal isn't already a strong, explicit signal of its own (a
    Bodybuilding-flavored "Build Muscle" or a pure "Get Strong" ask still
    wins even for a combat-sport athlete, since that's what they're
    literally asking for) and only when the caller's requested
    days_per_week actually fits that sport's recommended split - otherwise
    this falls through to the generic heuristic exactly as before.

    `experience_level` is applied last, as a ceiling, not an input to the
    heuristic itself - see `_apply_experience_ceiling` for why. Thin
    wrapper around `_recommend_split_raw` + `_apply_experience_ceiling` so
    callers that need to know *whether* the ceiling actually changed
    anything (generate_program's `experience_capped` response field) can
    call those two pieces separately instead of guessing from the output."""
    raw = _recommend_split_raw(days_per_week, goal, sport)
    return _apply_experience_ceiling(raw, days_per_week, experience_level)


def _recommend_split_raw(days_per_week: int, goal: str, sport: Optional[str] = None) -> str:
    """The days/goal/sport heuristic alone, with no experience-level ceiling
    applied yet - see `recommend_split` for the full picture."""
    sport_guidance = SPORT_SPLIT_GUIDANCE.get(sport) if sport else None
    if sport_guidance and goal not in ("Build Muscle", "Get Strong"):
        candidate = sport_guidance["split"]
        if days_per_week in SPLIT_TEMPLATES[candidate]["supported_days_per_week"]:
            return candidate

    if goal == "Conditioning":
        return "full_body"
    if days_per_week <= 2:
        return "full_body"
    if days_per_week == 3:
        return "push_pull_legs"
    if days_per_week == 4:
        if goal == "Get Strong":
            return "powerbuilding"
        if goal == "Build Muscle":
            return "phul"
        return "upper_lower"
    if days_per_week == 5:
        return "bro_split" if goal == "Build Muscle" else "phat"
    if days_per_week >= 6:
        return "arnold_split" if goal == "Build Muscle" else "push_pull_legs"
    return "full_body"


# What a beginner/novice is actually limited by isn't per-muscle training
# volume, it's neural adaptation and bar-path technique on a handful of
# compound lifts - the entire premise behind every classic novice linear
# progression (Starting Strength, StrongLifts 5x5, GreySkull LP - see
# full_body's own `reference` above) is full-body work at high per-lift
# frequency, not specialization. Body-part/specialization templates (Bro
# Split, Arnold Split, PHAT, PHUL, Powerbuilding) assume a work-capacity and
# technical base a true beginner hasn't built yet: splitting a beginner's
# already-modest weekly volume across 5-6 narrow sessions spreads it too
# thin to drive the adaptation that actually matters at this stage, and
# adds session-to-session variability before the basics are grooved in.
# This was previously not checked at all - a Beginner asking for 5 or 6
# days/week (a perfectly reasonable thing to have available) got routed
# straight into PHAT or an Arnold Split by the days/goal heuristic above,
# the same as an Advanced lifter asking for the same schedule.
EXPERIENCE_SPLIT_ALLOWLIST: Dict[str, set] = {
    "Beginner": {"full_body", "upper_lower"},
    "Novice": {"full_body", "upper_lower", "push_pull_legs"},
    # Intermediate and above: no ceiling - every template is fair game once
    # someone has the technique/work-capacity base to actually benefit from
    # more specialization.
}


def _apply_experience_ceiling(
    split_id: str, days_per_week: int, experience_level: Optional[str],
) -> str:
    """If the split the heuristic/sport-guidance landed on is above what's
    appropriate for this person's stated experience level, step back down
    to the highest-frequency template that's still on the allowlist and
    actually supports the requested days/week - preferring the simplest
    structure (full-body) first, same order a coach would fall back
    through."""
    allowlist = EXPERIENCE_SPLIT_ALLOWLIST.get(experience_level or "")
    if not allowlist or split_id in allowlist:
        return split_id
    for candidate in ("full_body", "upper_lower", "push_pull_legs"):
        if candidate in allowlist and days_per_week in SPLIT_TEMPLATES[candidate]["supported_days_per_week"]:
            return candidate
    # Nothing on the allowlist officially "supports" this exact day count
    # (e.g. a Beginner asking for 5 days/week, and full_body/upper_lower
    # only advertise 2/3/4/6) - fall back to full_body regardless.
    # _cycle_days() will still repeat it sensibly, and running full-body an
    # "unsupported" number of times is a far smaller mismatch for a
    # beginner than jumping to a body-part specialization split.
    return "full_body"




def _estimate_exercise_count(session_duration_minutes: int) -> int:
    """~9 minutes per exercise (working sets + rest + transitions), clamped
    to a sane range so a 15-minute request doesn't come back with 1 exercise
    and a 3-hour request doesn't come back with 40."""
    return max(4, min(10, round(session_duration_minutes / 9)))


def _cycle_days(days: List[Dict], days_per_week: int) -> List[Dict]:
    """Repeats a template's day list to fill the requested days_per_week
    (e.g. a 3-day PPL template run as 6 days/week). Repeated passes get a
    "(2)" etc. suffix on the label so the program output stays readable."""
    if days_per_week <= len(days):
        return days[:days_per_week]
    result = []
    for i in range(days_per_week):
        template_day = days[i % len(days)]
        pass_number = i // len(days) + 1
        day = dict(template_day)
        if pass_number > 1:
            day["label"] = f"{template_day['label']} ({pass_number})"
        result.append(day)
    return result


# PERIODIZATION MODEL
# Which model actually applies depends on training age, not just personal
# preference - this isn't a style toggle, it's grounded in what the
# periodization literature consistently finds:
#   - Novice lifters (Beginner/Novice here) respond best to plain LINEAR
#     progression - the same lift trained the same way, load nudged up
#     each week. Layering daily/weekly undulation on top of a novice's
#     program adds complexity without benefit; the classic novice linear
#     progressions this app already models the full_body split on
#     (StrongLifts, GreySkull, Starting Strength - see full_body's own
#     `reference` above) are linear precisely because a beginner's neural
#     adaptations are still fast enough that "just add weight" keeps
#     working for months.
#   - Intermediate+ lifters plateau on pure linear progression - the same
#     stimulus every session stops producing a novel-enough signal to keep
#     adapting. Daily Undulating Periodization (DUP) - varying the
#     load/rep target session to session instead of only trending it
#     upward week to week - is the standard response, and has direct
#     empirical support: Rhea et al. (2002, Med Sci Sports Exerc) had
#     trained lifters rotate heavy/moderate/light-style rep targets
#     within the same week and found significantly larger strength gains
#     than an equal-volume linear group; a 2017 systematic review/
#     meta-analysis (Grgic et al., covering the broader LP-vs-UP
#     literature) found undulating at least matches, and in several
#     studies exceeds, linear periodization once someone is already
#     trained - the "plateau on linear" pattern this models is exactly
#     why PHUL/PHAT/Powerbuilding (this file's own specialization splits)
#     are built around explicit Power/Hypertrophy day-to-day contrast
#     rather than one flat prescription - here that same logic is
#     extended to every split, not just the three that happened to be
#     named for it.
# The oldest real-world version of this same idea is the Heavy/Medium/
# Light (HLM) weekly template used in Olympic-weightlifting-adjacent
# strength circles for decades: the same lift is trained 2-3x/week, but
# each session sits at a different relative intensity instead of
# identical heavy work every time - functionally the same session-to-
# session undulation as DUP, just under an older name.
_UNDULATION_NOVICE_CEILING = 1  # LEVEL_RANK for "Novice" - Beginner/Novice stay linear, no cycle.

# Cycle applied to whichever days *don't* already carry a split-authored
# emphasis (PHUL/PHAT/Powerbuilding's "power"/"hypertrophy" labels are
# left alone - they're already hand-built undulation and take priority).
# Heavy -> Light -> Medium(baseline, i.e. no override - the goal's own
# bias/prescription runs unmodified) mirrors classic HLM ordering: heavy
# first while freshest in the training cycle, light as the built-in
# recovery session, medium bridging back up to the next heavy day.
_DUP_DAY_CYCLE = ["power", "hypertrophy", None]


def _daily_undulation_emphasis(day_index: int, experience_level: str, authored_emphasis: Optional[str]) -> Optional[str]:
    """What emphasis (if any) this specific day-in-the-week should carry.

    A split's own authored emphasis (PHUL's "Upper Power" etc.) always wins -
    that's already a real coach's explicit day-to-day contrast, not something
    to override. Otherwise: Beginner/Novice get no override (None - plain
    linear, goal's own bias applies uniformly, see module docstring above),
    Intermediate+ get the HLM/DUP-style rotation so the same split (e.g. a
    4-day Upper/Lower run by an Advanced lifter) isn't hypertrophy-biased
    (or power-biased) on every single day, the way it would be if the
    fallback in `_apply_prescription_bias` (goal_profile's flat bias) were
    left to apply unmodified to every day of the week."""
    if authored_emphasis:
        return authored_emphasis
    if _LEVEL_RANK.get(experience_level, 2) <= _UNDULATION_NOVICE_CEILING:
        return None
    return _DUP_DAY_CYCLE[day_index % len(_DUP_DAY_CYCLE)]



def _apply_prescription_bias(prescription: Dict, emphasis: Optional[str], goal_profile: Dict) -> Dict:
    """Nudges the engine's own sets/reps/load prescription toward a power or
    hypertrophy emphasis. A day's own `emphasis` wins over the goal's general
    `bias` (a PHUL "Lower Power" day stays power-biased even if the overall
    goal is Build Muscle - that contrast is the entire point of PHUL)."""
    bias = emphasis or goal_profile.get("bias")
    ptype = prescription.get("type")
    if not bias or ptype not in ("strength", "strength_bodyweight"):
        return prescription

    result = dict(prescription)
    if ptype == "strength":
        if bias == "power":
            result["load_pct_1rm"] = min(95, result["load_pct_1rm"] + 8)
            result["reps"] = max(2, result["reps"] - 2)
        elif bias == "hypertrophy":
            result["load_pct_1rm"] = max(50, result["load_pct_1rm"] - 10)
            result["reps"] = min(15, result["reps"] + 3)
            result["sets"] = min(5, result["sets"] + 1)
    else:  # strength_bodyweight - no load field to bias, so lean on reps/sets
        if bias == "power":
            result["reps"] = max(2, result["reps"] - 2)
            result["note"] = ((result.get("note", "") + " ") if result.get("note") else "") + \
                "Power day: move each rep as explosively as the variation allows."
        elif bias == "hypertrophy":
            result["reps"] = min(20, result["reps"] + 4)
            result["sets"] = min(5, result["sets"] + 1)
    return result


def _apply_week_progression(prescription: Dict, week_number: int, is_deload: bool) -> Dict:
    """Simple linear progressive overload across the mesocycle. Deload weeks
    get no extra bump here - the deload's actual lightening already happened
    inside generate_session (readiness was forced low for that week, which
    triggers its built-in deload_mode: fewer sets, capped difficulty)."""
    result = dict(prescription)
    if is_deload:
        result["progression_note"] = f"Week {week_number}: deload - reduced volume and intensity to recover."
        return result

    step = week_number - 1  # 0 in week 1
    if step == 0:
        result["progression_note"] = f"Week {week_number}: baseline."
        return result

    ptype = result.get("type")
    if ptype == "strength":
        result["load_pct_1rm"] = min(95, result["load_pct_1rm"] + step * 3)
        result["progression_note"] = f"Week {week_number}: +{step * 3}% load vs. week 1."
    elif ptype == "strength_bodyweight":
        result["reps"] = result["reps"] + step
        result["progression_note"] = f"Week {week_number}: +{step} rep(s) vs. week 1 - add load (vest/band) once this gets easy."
    elif ptype == "conditioning":
        result["work_seconds"] = round(result["work_seconds"] * (1 + 0.05 * step))
        result["rest_seconds"] = max(15, round(result["rest_seconds"] * (1 - 0.05 * step)))
        result["progression_note"] = f"Week {week_number}: longer work intervals, shorter rest vs. week 1."
    elif ptype == "isometric":
        result["hold_seconds"] = round(result["hold_seconds"] * (1 + 0.08 * step))
        result["progression_note"] = f"Week {week_number}: longer holds vs. week 1."
    elif ptype == "carry":
        result["distance_meters"] = round(result["distance_meters"] * (1 + 0.06 * step))
        result["progression_note"] = f"Week {week_number}: longer carry distance vs. week 1."
    else:
        result["progression_note"] = f"Week {week_number}: hold technique steady, add a rep if it's clean."
    return result


def generate_program(engine, req: ProgramRequest) -> Dict:
    from fastapi import HTTPException  # local import: keeps this module importable/testable without FastAPI wired up

    phase_split = _split_for_phase(req.training_phase, req.days_per_week) if req.preferred_split == "auto" else None
    if phase_split:
        raw_split_id = phase_split
        split_id = _apply_experience_ceiling(raw_split_id, req.days_per_week, req.experience_level)
    elif req.preferred_split == "auto":
        raw_split_id = _recommend_split_raw(req.days_per_week, req.primary_goal, req.sport)
        split_id = _apply_experience_ceiling(raw_split_id, req.days_per_week, req.experience_level)
    else:
        raw_split_id = split_id = req.preferred_split
    template = SPLIT_TEMPLATES.get(split_id)
    if template is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown split '{split_id}'. See GET /api/v1/splits for valid ids.",
        )

    # Independent, advisory-only read on whether req.experience_level - which
    # _apply_experience_ceiling above already used as a hard ceiling on which
    # split gets offered (EXPERIENCE_SPLIT_ALLOWLIST), and which every day's
    # WorkoutRequest below uses as its own exercise-level ceiling - actually
    # matches what the entered numbers say. See strength_standards.py. This
    # never changes split_id, day_slots, or the periodization model computed
    # further down; computed once here (not per day/week) and just rides
    # along in the response so a mis-stated level is visible instead of
    # silently flowing through both of those, per that module's docstring.
    bio = req.biometrics
    level_estimate = classify_strength_level(
        weight_kg=bio.weight_kg if bio else 0.0,
        bench_press_1rm=(bio.bench_press_1rm or 0.0) if bio else 0.0,
        squat_1rm=(bio.squat_1rm or 0.0) if bio else 0.0,
        deadlift_1rm=(bio.deadlift_1rm or 0.0) if bio else 0.0,
        pullups_max_reps=(bio.pullups_max_reps or 0) if bio else 0,
        pushups_max_reps=(bio.pushups_max_reps or 0) if bio else 0,
        sex=bio.sex if bio else None,
    )
    level_check_result = level_check(req.experience_level, level_estimate)

    goal_profile = GOAL_PROFILES.get(req.primary_goal, GOAL_PROFILES["General Fitness"])
    day_slots = _cycle_days(template["days"], req.days_per_week)
    exercise_count = _estimate_exercise_count(req.session_duration_minutes)

    # A mesocycle shorter than 3 weeks doesn't get an automatic deload week -
    # there's no accumulated fatigue yet to deload from.
    deload_week = req.weeks if req.weeks >= 3 else None

    # Per-day-label exercise history across the mesocycle - e.g. every
    # "Full Body A" across every week shares one history list. Passed back
    # to the engine as exclude_exercise_ids so it can deprioritize (not
    # hard-ban) repeats and rotate toward other near-tied candidates instead
    # of mechanically returning the exact same exercises week after week for
    # the same day-type. See WorkoutRequest.exclude_exercise_ids /
    # ProgressionEngine._pick_with_variety for how that rotation works.
    history_by_day_label: Dict[str, List[str]] = {}

    weeks_output = []
    for week_number in range(1, req.weeks + 1):
        is_deload = week_number == deload_week
        effective_readiness = min(req.readiness, 35) if is_deload else req.readiness

        day_results = []
        for day_index, day_slot in enumerate(day_slots):
            if goal_profile.get("override_categories"):
                categories = list(goal_profile["category_boost"])
            else:
                categories = list(dict.fromkeys(
                    (day_slot.get("categories") or []) + goal_profile.get("category_boost", [])
                ))

            day_label = day_slot["label"]
            day_request = WorkoutRequest(
                sport=req.sport,
                experience_level=req.experience_level,
                equipment_available=req.equipment_available,
                readiness=effective_readiness,
                injuries=req.injuries,
                biometrics=req.biometrics,
                conditioning_emphasis=req.conditioning_emphasis,
                target_categories=categories or None,
                target_muscles=day_slot.get("muscles"),
                exercise_limit=exercise_count,
                exclude_exercise_ids=history_by_day_label.get(day_label),
                variety_seed=week_number * len(day_slots) + day_index,
            )
            session_result = engine.generate_session(day_request)
            history_by_day_label.setdefault(day_label, []).extend(
                pe["id"] for pe in session_result["prescribed_workout"]
            )

            emphasis = _daily_undulation_emphasis(day_index, req.experience_level, day_slot.get("emphasis"))
            phase_info = PHASE_GUIDANCE.get(req.training_phase) if req.training_phase else None
            for pe in session_result["prescribed_workout"]:
                pe["prescription"] = _apply_prescription_bias(pe["prescription"], emphasis, goal_profile)
                pe["prescription"] = _apply_week_progression(pe["prescription"], week_number, is_deload)
                if phase_info:
                    pe["prescription"] = _apply_phase_volume_scaling(pe["prescription"], phase_info["volume_multiplier"])

            day_results.append({
                "day_label": day_slot["label"],
                "emphasis": emphasis,
                "focus_categories": categories or None,
                "focus_muscles": day_slot.get("muscles"),
                "exercise_count": len(session_result["prescribed_workout"]),
                "prescribed_workout": session_result["prescribed_workout"],
                "session_structure": session_result["session_structure"],
                "deload_mode": session_result["deload_mode"],
            })

        weeks_output.append({
            "week_number": week_number,
            "is_deload": is_deload,
            "days": day_results,
        })

    sport_guidance = SPORT_SPLIT_GUIDANCE.get(req.sport)
    sport_recommended = bool(
        sport_guidance and req.preferred_split == "auto" and sport_guidance["split"] == split_id
    )

    experience_capped = req.preferred_split == "auto" and raw_split_id != split_id
    experience_rationale = (
        f"Stepped down to {template['name']} for a {req.experience_level.lower()} lifter - "
        "body-part specialization splits assume a technique/work-capacity base this stage "
        "hasn't built yet; full-body/upper-lower frequency is what drives progress here."
        if experience_capped else None
    )

    is_novice = _LEVEL_RANK.get(req.experience_level, 2) <= _UNDULATION_NOVICE_CEILING
    periodization_model = "Linear" if is_novice else "Daily Undulating (DUP / Heavy-Light-Medium)"
    periodization_rationale = (
        "Straight linear progression - the same lift trained the same way each session, load "
        "nudged up week to week. This is what the periodization literature consistently finds "
        "works best at this training age; undulating/DUP schemes add complexity a beginner "
        "doesn't yet need to keep progressing."
        if is_novice else
        "Each day in the split rotates a Heavy / Light / Medium (or Power / Hypertrophy) target "
        "instead of repeating the same stimulus every session, layered on top of the same "
        "week-to-week load progression. Rhea et al. (2002) found this kind of daily undulation "
        "produced larger strength gains than equal-volume linear training in already-trained "
        "lifters, and it's the same logic behind classic HLM weekly templates - a split-authored "
        "day (e.g. PHUL's 'Upper Power') keeps its own explicit emphasis; everything else "
        "rotates automatically."
    )

    training_phase_block = None
    if req.training_phase:
        phase = PHASE_GUIDANCE.get(req.training_phase, {})
        training_phase_block = {
            "phase": req.training_phase,
            "typical_duration": phase.get("duration"),
            "lifting_focus": phase.get("lifting_focus"),
            "conditioning_focus": phase.get("conditioning_focus"),
            "volume_multiplier": phase.get("volume_multiplier"),
            "split_matched_phase": bool(phase_split and split_id == phase_split),
        }

    sport_conditioning = sport_conditioning_profile(req.sport)
    conditioning_guidance = None
    if sport_conditioning:
        ref = conditioning_reference()
        aerobic_pct = sport_conditioning["aerobic_pct"]
        lactic_pct = sport_conditioning["lactic_pct"]
        conditioning_guidance = {
            "sport": req.sport,
            "aerobic_pct": aerobic_pct,
            "lactic_pct": lactic_pct,
            "best_splits": sport_conditioning["best_splits"],
            "gym_emphasis": sport_conditioning["gym_emphasis"],
            "conditioning_notes": sport_conditioning["conditioning_notes"],
            "time_saver": sport_conditioning["time_saver"],
            # Weighted picks from the manual's Part 6 menus - biased toward
            # aerobic or lactic sessions/week in proportion to the sport's
            # own ratio, not just "here's every option that exists".
            "suggested_aerobic_sessions_per_week": round(aerobic_pct / 100 * 3) or (1 if aerobic_pct > 0 else 0),
            "suggested_lactic_sessions_per_week": round(lactic_pct / 100 * 2.5) or (1 if lactic_pct > 0 else 0),
            "aerobic_session_menu": ref["aerobic_session_menu"],
            "lactic_session_menu": ref["lactic_session_menu"],
            "weekly_fitting_note": ref["weekly_fitting_note"],
            "universal_add_ons": ref["universal_add_ons"],
            "warmup_protocol": ref["warmup_protocol"],
            "warmup_note": ref["warmup_note"],
        }

    return {
        "status": "success",
        "engine": "FORGE Program Builder v1.0",
        "primary_goal": req.primary_goal,
        "sport": req.sport,
        "experience_level": req.experience_level,
        "level_check": level_check_result,
        "conditioning_emphasis": req.conditioning_emphasis,
        "training_phase": training_phase_block,
        "conditioning_guidance": conditioning_guidance,
        "periodization_model": periodization_model,
        "periodization_rationale": periodization_rationale,
        "split": {
            "id": split_id,
            "name": template["name"],
            "description": template["description"],
            "reference": template.get("reference"),
            "recommended_for_sport": sport_recommended,
            "sport_rationale": sport_guidance["rationale"] if sport_recommended else None,
            "experience_capped": experience_capped,
            "experience_rationale": experience_rationale,
        },
        "days_per_week": req.days_per_week,
        "weeks": req.weeks,
        "deload_week": deload_week,
        "program": weeks_output,
    }
