"""
sport_profiles.py — what "transfers" to each sport, encoded once per sport
rather than once per exercise.

WHY THIS EXISTS
Before this module, `sport_priority` in exercises.json was a single hand-typed
0-100 number per (exercise, sport) pair, authored directly in
generate_new_exercises.py with no stated reasoning attached — a Bulgarian Split
Squat scores 70 for Judo and nobody downstream can say *why*. That's the same
problem exercise_metadata.py solved for the movement-analysis and
athletic-quality fields: numbers that look precise but aren't checkable against
anything are worse than an engine that can explain itself.

This module encodes a strength coach's mental model of each sport ONCE — "what
physical qualities actually win in this sport" — as a weighted subset of the
same ATHLETIC_QUALITY_TAGS every exercise is already scored against
(exercise_metadata.ATHLETIC_QUALITY_TAGS). The engine then computes transfer
as a weighted overlap between an exercise's real, derived qualities and the
sport's profile, and can point at exactly which qualities drove the number.

The original hand-authored `sport_priority` isn't discarded — a coach's flat
judgment call ("this exercise just matters for this sport") still carries
real information the quality-tag overlap can't fully capture (e.g. a highly
sport-specific drill). `blended_transfer_score` below averages the two, so
the number is grounded in something checkable but doesn't lose whatever
judgment was already baked into the original data.

Reviewable and editable exactly like CATEGORY_PROFILES: change one sport's
row here and every exercise's transfer score for that sport updates
consistently, instead of hand-editing 175 individual numbers.
"""

from typing import Dict, List, Tuple

# One row per sport in exercises.json's sport_priority keys. Each maps a
# subset of ATHLETIC_QUALITY_TAGS to an importance weight (0-100). Qualities
# left out of a sport's profile simply don't contribute to that sport's
# transfer score - they're not "zero", they're "not part of the model" (a
# sport's profile is deliberately the ~6-10 qualities that actually
# distinguish it, not a full re-ranking of all 33 tags).
SPORT_QUALITY_PROFILES: Dict[str, Dict[str, int]] = {
    "Wrestling": {
        "Relative Strength": 70, "Power": 65, "Explosiveness": 60,
        "Grip Strength": 70, "Grip Endurance": 65, "Hip Stability": 60,
        "Core Stability": 55, "Anaerobic Capacity": 60,
        "Reactive Strength": 50, "Change of Direction": 45,
    },
    "Judo": {
        "Grip Strength": 75, "Grip Endurance": 60, "Rotational Power": 65,
        "Power": 60, "Hip Stability": 55, "Explosiveness": 55,
        "Core Stability": 50, "Anti Rotation": 45, "Reactive Strength": 45,
    },
    "Sambo": {
        "Grip Strength": 65, "Grip Endurance": 55, "Power": 60,
        "Hip Stability": 55, "Rotational Power": 50, "Explosiveness": 50,
        "Core Stability": 50, "Anaerobic Capacity": 50,
    },
    "BJJ": {
        "Grip Endurance": 70, "Grip Strength": 55, "Core Stability": 60,
        "Anti Rotation": 45, "Muscular Endurance": 55, "Hip Stability": 55,
        "Work Capacity": 50, "Anaerobic Capacity": 45,
    },
    "Boxing": {
        "Rotational Power": 70, "Power": 60, "Explosiveness": 65,
        "Rate of Force Development": 55, "Core Stability": 50,
        "Anti Rotation": 45, "Anaerobic Capacity": 55,
        "Aerobic Capacity": 45, "Change of Direction": 40, "Neck Strength": 30,
    },
    "Muay Thai": {
        "Rotational Power": 65, "Power": 65, "Hip Stability": 55,
        "Explosiveness": 55, "Grip Strength": 40, "Anaerobic Capacity": 55,
        "Core Stability": 50, "Muscular Endurance": 45,
    },
    "Kickboxing": {
        "Rotational Power": 60, "Explosiveness": 60, "Power": 55,
        "Change of Direction": 50, "Agility": 50, "Anaerobic Capacity": 55,
        "Core Stability": 45,
    },
    "Sanda": {
        "Power": 65, "Explosiveness": 60, "Rotational Power": 55,
        "Hip Stability": 50, "Reactive Strength": 45,
        "Anaerobic Capacity": 50, "Core Stability": 45,
    },
    "Rugby": {
        "Max Strength": 60, "Power": 65, "Deceleration": 55,
        "Acceleration": 55, "Work Capacity": 55, "Core Stability": 50,
        "Grip Strength": 45, "Anaerobic Capacity": 55, "Change of Direction": 45,
    },
    "Rock Climbing": {
        "Grip Strength": 80, "Grip Endurance": 75, "Core Stability": 60,
        "Anti Rotation": 40, "Relative Strength": 55,
        "Anti Lateral Flexion": 35, "Muscular Endurance": 45,
    },
    "HYROX": {
        "Work Capacity": 75, "Aerobic Capacity": 65, "Anaerobic Capacity": 55,
        "Muscular Endurance": 60, "Grip Endurance": 50, "Conditioning": 65,
        "Core Stability": 40,
    },
    "Special Forces": {
        "Work Capacity": 60, "Max Strength": 50, "Relative Strength": 50,
        "Grip Strength": 50, "Grip Endurance": 50, "Core Stability": 50,
        "Aerobic Capacity": 50, "Anaerobic Capacity": 50, "Muscular Endurance": 55,
    },
    # MMA blends the striking (Boxing/Muay Thai) and grappling (Wrestling/BJJ/Judo)
    # profiles rather than being its own thing - a fighter needs rotational power
    # for striking AND grip/pulling strength for the clinch and ground game, plus
    # the gas tank to do both across rounds. Weights below sit roughly at the
    # average of its component sports' rows, nudged so nothing gets zeroed out
    # the way a naive "pick one archetype" profile would.
    "MMA": {
        "Grip Strength": 60, "Grip Endurance": 55, "Rotational Power": 60,
        "Power": 60, "Explosiveness": 55, "Hip Stability": 55,
        "Core Stability": 55, "Anaerobic Capacity": 60, "Work Capacity": 50,
        "Change of Direction": 40, "Reactive Strength": 40, "Muscular Endurance": 45,
    },
}

# Below this per-quality contribution, a quality isn't worth naming in a
# "why this exercise, for this sport" explanation - it's noise, not signal.
_EXPLAIN_FLOOR = 30


def quality_overlap_score(athletic_qualities: Dict[str, int], sport: str) -> float:
    """Weighted average of an exercise's athletic-quality scores against a
    sport's profile weights. 0-100, same scale as the input scores, because
    it's a weighted *average* (not sum) of numbers already on that scale."""
    profile = SPORT_QUALITY_PROFILES.get(sport)
    if not profile or not athletic_qualities:
        return 0.0
    total_weight = sum(profile.values())
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(
        weight * athletic_qualities.get(quality, 0) for quality, weight in profile.items()
    )
    return weighted_sum / total_weight


def top_contributing_qualities(
    athletic_qualities: Dict[str, int], sport: str, limit: int = 3
) -> List[Tuple[str, int]]:
    """The qualities actually driving this exercise's transfer score for this
    sport, ranked by (sport's weight on that quality) x (exercise's score on
    it) - i.e. what a coach would point at if asked to justify the number."""
    profile = SPORT_QUALITY_PROFILES.get(sport)
    if not profile or not athletic_qualities:
        return []
    scored = [
        (quality, athletic_qualities.get(quality, 0))
        for quality in profile
        if athletic_qualities.get(quality, 0) >= _EXPLAIN_FLOOR
    ]
    scored.sort(key=lambda pair: profile[pair[0]] * pair[1], reverse=True)
    return scored[:limit]


def blended_transfer_score(data: Dict, sport: str) -> int:
    """The number the engine actually ranks/sorts on: half the original
    hand-authored sport_priority (real coach judgment, kept), half the
    quality-overlap score (checkable against the exercise's own derived
    profile). If a sport has no quality profile or the exercise has no
    quality tags yet, falls back to whichever of the two is available."""
    authored = data.get("sport_priority", {}).get(sport)
    qualities = data.get("athletic_qualities", {})
    overlap = quality_overlap_score(qualities, sport) if qualities else None

    if authored is not None and overlap is not None:
        return round(0.5 * authored + 0.5 * overlap)
    if authored is not None:
        return round(authored)
    if overlap is not None:
        return round(overlap)
    return 0


SPORT_MOVEMENT_EMPHASIS: Dict[str, Dict[str, float]] = {
    # NOTE on "Rotational"/"Rotation": these are movement_pattern values, and
    # only 5 of 442 exercises in exercises.json carry either one (the rest of
    # the database's genuinely rotational work - shadow boxing, heavy bag
    # combinations, clinch knees, throws - is tagged with the movement_pattern
    # values "Strike" and "Throw" instead, under category "Sport Specific").
    # Keying only on "Rotational"/"Rotation" meant this boost almost never
    # fired for the sports it exists for. "Strike" and "Throw" are added below
    # for every sport where striking or throwing actually transfers, so the
    # boost reaches the exercises real coaches would call rotational-power
    # work for these sports.
    "Boxing": {
        "Horizontal Push": 1.25, "Vertical Push": 1.15, "Rotational": 1.3,
        "Rotation": 1.3, "Strike": 1.3, "Power": 1.15,
        "Horizontal Pull": 0.85, "Squat": 0.9,
    },
    "Muay Thai": {
        "Horizontal Push": 1.15, "Vertical Push": 1.1, "Rotational": 1.25,
        "Rotation": 1.25, "Strike": 1.25, "Hinge": 1.15,
        "Horizontal Pull": 0.9,
    },
    "Kickboxing": {
        "Rotational": 1.25, "Rotation": 1.25, "Strike": 1.25,
        "Horizontal Push": 1.1, "Hinge": 1.1, "Horizontal Pull": 0.9,
    },
    "Sanda": {
        "Rotational": 1.2, "Rotation": 1.2, "Strike": 1.2, "Throw": 1.15,
        "Horizontal Push": 1.15, "Hinge": 1.1, "Horizontal Pull": 0.9,
    },
    "Judo": {
        "Horizontal Pull": 1.35, "Vertical Pull": 1.3, "Grip": 1.3,
        "Throw": 1.35, "Hinge": 1.15, "Horizontal Push": 0.85,
        "Vertical Push": 0.85,
    },
    "Wrestling": {
        "Horizontal Pull": 1.25, "Vertical Pull": 1.2, "Hinge": 1.2,
        "Squat": 1.15, "Grip": 1.2, "Throw": 1.25, "Vertical Push": 0.9,
    },
    "Sambo": {
        "Horizontal Pull": 1.25, "Vertical Pull": 1.2, "Hinge": 1.15,
        "Grip": 1.2, "Throw": 1.25, "Vertical Push": 0.9,
    },
    "BJJ": {
        "Horizontal Pull": 1.3, "Vertical Pull": 1.25, "Grip": 1.25,
        "Core": 1.15, "Throw": 1.1, "Vertical Push": 0.9, "Squat": 0.9,
    },
    "Rock Climbing": {
        "Vertical Pull": 1.4, "Horizontal Pull": 1.2, "Grip": 1.35,
        "Core": 1.15, "Horizontal Push": 0.8, "Squat": 0.85,
    },
    "Rugby": {
        "Hinge": 1.25, "Squat": 1.2, "Horizontal Push": 1.1,
        "Horizontal Pull": 1.1, "Carry": 1.15, "Throw": 1.1,
    },
    "HYROX": {
        "Carry": 1.3, "Hinge": 1.15, "Squat": 1.1, "Conditioning": 1.2,
    },
    "Special Forces": {
        "Carry": 1.2, "Hinge": 1.15, "Squat": 1.1, "Vertical Pull": 1.1,
    },
    # Unlike a pure striking or pure grappling sport, MMA doesn't want any
    # movement pattern de-emphasized below 1.0 - a fighter who neglects pulling
    # for pressing (or vice versa) has an exploitable hole in the clinch or on
    # the feet. Everything gets a modest, roughly even bump instead of the
    # sharp push-vs-pull skew a single-discipline sport's table has.
    "MMA": {
        "Horizontal Push": 1.15, "Vertical Push": 1.1, "Rotational": 1.2,
        "Rotation": 1.2, "Strike": 1.2, "Throw": 1.15,
        "Horizontal Pull": 1.15, "Vertical Pull": 1.15,
        "Grip": 1.15, "Hinge": 1.1, "Squat": 1.05,
    },
}


def movement_emphasis_multiplier(data: Dict, sport: str) -> float:
    """Sport-specific bias for this exercise's pattern (category takes
    precedence over movement_pattern when both are present in the sport's
    table, since category is the coarser/more reliable field). Returns 1.0
    (no change) when the sport has no table or the pattern isn't in it."""
    table = SPORT_MOVEMENT_EMPHASIS.get(sport)
    if not table:
        return 1.0
    category = data.get("category")
    if category in table:
        return table[category]
    pattern = data.get("movement_pattern")
    if pattern in table:
        return table[pattern]
    return 1.0


# Combat Sports & Rugby S&C Manual, Part 5 — "Quick-Reference Summary" table
# plus each sport's own subsection. One row per sport the manual actually
# covers (MMA, BJJ, Wrestling, Judo, Boxing, Kickboxing, Muay Thai, Sanda,
# Sambo, Special Forces, Rugby — 11 sports; Rock Climbing and HYROX aren't
# in the manual and keep whatever guidance they already had elsewhere in
# this module). `aerobic_pct`/`lactic_pct` always sum to 100 and drive how
# many of AEROBIC_SESSION_MENU vs. LACTIC_SESSION_MENU sessions a program
# should surface per week (conditioning_protocols.py has the menus
# themselves — this table only carries the per-sport ratio + narrative).
SPORT_CONDITIONING_PROFILES: Dict[str, Dict] = {
    "MMA": {
        "best_splits": ["3-Day Full Body (in-season)", "4-Day Upper/Lower (off-season)"],
        "aerobic_pct": 50, "lactic_pct": 50,
        "gym_emphasis": "Balanced full-body strength; the biggest aerobic base of all combat sports here (longest, most varied rounds).",
        "conditioning_notes": "2x/week aerobic (30-40 min Zone 2) to build the base + 1-2x/week lactic interval work matching your fight's round length (e.g. 5-min rounds/1-min rest x3-5).",
        "time_saver": "Pair your lactic conditioning with skill work — hard sparring/rolling rounds count toward your lactic volume, you don't need to double up.",
    },
    "BJJ": {
        "best_splits": ["3-Day Full Body", "3-Day Push/Pull/Legs"],
        "aerobic_pct": 55, "lactic_pct": 45,
        "gym_emphasis": "Pulling strength (rows, pull-ups), isometric holds, hip strength for guard/sweeps, heavy grip and forearm work.",
        "conditioning_notes": "Aerobic base is priority (rolls can be long) — 2-3x/week Zone 2, plus 1x/week lactic work in 5-8 min 'round' efforts to mimic hard rolling.",
        "time_saver": "Rolling itself is excellent lactic conditioning — 4-5 hard 5-minute rolls covers your weekly lactic quota.",
    },
    "Wrestling": {
        "best_splits": ["4-Day Upper/Lower (off-season)", "3-Day Full Body (in-season)"],
        "aerobic_pct": 35, "lactic_pct": 65,
        "gym_emphasis": "Hip and posterior chain power (deadlifts, hip thrust), explosive pulling, heavy neck training (bridging), grip.",
        "conditioning_notes": "Lactic-dominant — 2x/week interval work (e.g. 20-30s max effort bike/sled x8-10, short rest) plus 1x/week aerobic base session.",
        "time_saver": "Live wrestling/scramble drilling doubles as lactic conditioning — don't stack extra hard intervals on heavy practice days.",
    },
    "Judo": {
        "best_splits": ["3-Day Full Body"],
        "aerobic_pct": 30, "lactic_pct": 70,
        "gym_emphasis": "Maximal grip strength, explosive hip extension (cleans/high pulls or trap bar jumps), single-leg strength for off-balancing.",
        "conditioning_notes": "Mostly lactic — short, very hard intervals (15-30s max effort) mirroring throw exchanges, 2x/week; 1x/week light aerobic for recovery capacity.",
        "time_saver": "Uchikomi (repeated throw entries) at high speed is a built-in lactic/power session.",
    },
    "Boxing": {
        "best_splits": ["2-Day Upper/Lower", "3-Day Full Body (off-season)"],
        "aerobic_pct": 40, "lactic_pct": 60,
        "gym_emphasis": "Rotational core power (landmine press, medicine ball throws), upper-back and shoulder endurance, single-leg stability for footwork.",
        "conditioning_notes": "Classic round-based lactic intervals (3 min on/1 min off x3-6, bike or shadowboxing) 2x/week, plus 2x/week aerobic running for the historic 'roadwork' base.",
        "time_saver": "Structure your interval conditioning in literal round/rest ratios so it transfers directly.",
    },
    "Kickboxing": {
        "best_splits": ["3-Day Full Body", "2-Day Upper/Lower"],
        "aerobic_pct": 45, "lactic_pct": 55,
        "gym_emphasis": "Single-leg strength and hip power for kicks (split squats, hip thrust, trap bar jumps), core rotation, shoulder endurance.",
        "conditioning_notes": "Round-based lactic intervals 2x/week (matching competition round length) + 2x/week aerobic base.",
        "time_saver": "Heavy-bag combination rounds at competition pace double as lactic work — track them as a session.",
    },
    "Muay Thai": {
        "best_splits": ["3-Day Full Body", "2-Day Upper/Lower"],
        "aerobic_pct": 45, "lactic_pct": 55,
        "gym_emphasis": "Hip and knee-drive power, clinch/grip strength (heavy carries, isometric holds), single-leg balance, calf/shin conditioning work.",
        "conditioning_notes": "Round-based lactic intervals 2x/week + 2x/week aerobic running/cycling (traditional Muay Thai roadwork).",
        "time_saver": "Clinch sparring rounds are simultaneously strength-endurance and lactic conditioning.",
    },
    "Sanda": {
        "best_splits": ["3-Day Full Body"],
        "aerobic_pct": 40, "lactic_pct": 60,
        "gym_emphasis": "Full-body explosive power (trap bar jumps, medicine ball throws), grip for clinch throws, single-leg strength for sprawl/takedown defense.",
        "conditioning_notes": "Lactic-dominant intervals 2x/week (mix striking-pace and grappling-pace efforts) + 1x/week aerobic base.",
        "time_saver": "Combine throw-entry drilling with striking combinations in the same hard round to cover both qualities at once.",
    },
    "Sambo": {
        "best_splits": ["4-Day Upper/Lower (off-season)", "3-Day Full Body (in-season)"],
        "aerobic_pct": 35, "lactic_pct": 65,
        "gym_emphasis": "Grip strength, explosive hip extension, posterior chain strength, joint-friendly single-leg work to protect knees/hips from leg-lock stress.",
        "conditioning_notes": "Lactic-dominant, similar to wrestling/judo — 2x/week short hard intervals + 1x/week aerobic base.",
        "time_saver": "Live grappling rounds at full intensity substitute directly for a lactic conditioning session.",
    },
    "Special Forces": {
        "best_splits": ["4-Day Upper/Lower"],
        "aerobic_pct": 70, "lactic_pct": 30,
        "gym_emphasis": "Max strength in squat/deadlift/press, heavy loaded carries, pulling strength for climbing/casualty drags.",
        "conditioning_notes": "Aerobic-dominant — 3-4x/week (rucking, running, swimming, rowing) building toward longer durations, plus 1-2x/week lactic work (sandbag/sled intervals, hill sprints) for the short maximal-effort demand.",
        "time_saver": "Ruck marches and loaded carries double as both conditioning and posterior-chain/grip strength work.",
    },
    "Rugby": {
        "best_splits": ["4-Day Upper/Lower (in-season)", "3-Day Push/Pull/Legs (off-season)"],
        "aerobic_pct": 45, "lactic_pct": 55,
        "gym_emphasis": "Maximal squat/deadlift/press strength for scrums and tackling, explosive power (jumps, sled pushes), neck strength for contact.",
        "conditioning_notes": "Repeated-sprint lactic training 2x/week (e.g. 10x40m sprint with short rest) + 2-3x/week aerobic running to build match-duration capacity.",
        "time_saver": "Team conditioning/repeated-sprint drills at training count as your lactic sessions — add gym work on separate or lighter days.",
    },
}


def sport_conditioning_profile(sport: str) -> Dict:
    """Aerobic:lactic ratio + gym emphasis + weekly conditioning guidance for
    a sport, straight out of the manual's Part 5. Returns an empty dict for
    sports the manual doesn't cover (e.g. Rock Climbing, HYROX) rather than
    guessing a ratio for them."""
    return SPORT_CONDITIONING_PROFILES.get(sport, {})


def transfer_rationale(data: Dict, sport: str) -> str:
    """One sentence a coach could actually say out loud."""
    qualities = data.get("athletic_qualities", {})
    top = top_contributing_qualities(qualities, sport)
    name = data.get("name", data.get("id", "This exercise"))
    multiplier = movement_emphasis_multiplier(data, sport)
    pattern_note = ""
    if multiplier >= 1.1:
        pattern_note = f" Boosted for {sport}: {data.get('category', 'this pattern')} is a priority pattern for the sport."
    elif multiplier <= 0.9:
        pattern_note = f" De-emphasized for {sport}: {data.get('category', 'this pattern')} matters less than other patterns here."
    if not top:
        return f"{name} contributes general conditioning value for {sport}.{pattern_note}"
    quality_list = ", ".join(f"{q} ({v})" for q, v in top)
    return f"Transfers to {sport} primarily through {quality_list}.{pattern_note}"
