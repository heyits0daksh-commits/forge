"""
exercise_metadata.py — v4.0 metadata enrichment (movement analysis + athletic
quality tags), derived rather than hand-typed.

WHY DERIVED, NOT HAND-AUTHORED:
The v4.0 spec asks for ~15 movement-analysis fields and ~33 athletic-quality
scores (0-100) on every exercise. For 175 exercises that's roughly 8,000
individual numbers. Hand-typing 8,000 numbers in one pass produces numbers
that look precise but aren't actually verified against anything — which is
worse than not having them, because a training engine that silently trusts
fabricated scores makes worse decisions than one that admits it doesn't know.

Instead, this module encodes the judgment ONCE per movement category (a
strength coach's mental model: "vertical pulls build X, cost Y in CNS fatigue,
require Z stability") and then derives each exercise's actual values from
that category baseline plus real signal already present on the exercise
(difficulty, equipment, which joints it stresses, its movement_pattern, its
name). This is the same principle the rest of FORGE already uses — the
metadata endpoint and injury taxonomy are both "derive from what the data
already says" rather than "maintain a second hand-typed copy" — applied to
the new fields.

This is intentionally reviewable: change one row in CATEGORY_PROFILES and
every exercise in that category updates consistently. A future pass can
override individual exercises where a coach disagrees with the category
default, without touching this derivation logic.

USAGE:
    from exercise_metadata import enrich_exercise
    enriched_fields = enrich_exercise(exercise_dict)
    exercise_dict.update(enriched_fields)   # purely additive — no existing
                                             # key is ever read from or
                                             # written to by this module
"""

from typing import Dict, List

# ==========================================================================
# 1. ATHLETIC QUALITY TAGS — full list from the v4.0 spec, section 2, plus
# three v5.1 additions (Wrist/Elbow/Lower Back Stability) so every joint in
# joint_stress's actual 8-tag vocabulary (see injury_taxonomy.py's module
# docstring: Wrist, Elbow, Shoulder, Neck, Lower Back, Hip, Knee, Ankle) has
# a matching stability tag - the original 5 (Shoulder/Hip/Knee/Ankle/Neck)
# silently left Wrist, Elbow, and Lower Back with no stability tag at all,
# which meant no exercise could ever be a rehab candidate for an injury on
# those three joints (JOINT_STABILITY_TAG.get(joint) returned None ->
# is_rehab_candidate short-circuited to False) and knowledge_graph.py's
# joint nodes silently omitted them (see that module's fix).
# ==========================================================================
ATHLETIC_QUALITY_TAGS: List[str] = [
    "Max Strength", "Relative Strength", "Hypertrophy", "Muscular Endurance",
    "Power", "Explosiveness", "Acceleration", "Deceleration", "Top Speed",
    "Agility", "Change of Direction", "Reactive Strength", "Elastic Strength",
    "Rate of Force Development", "Grip Strength", "Grip Endurance",
    "Core Stability", "Anti Rotation", "Anti Extension", "Anti Flexion",
    "Anti Lateral Flexion", "Rotational Power", "Shoulder Stability",
    "Hip Stability", "Knee Stability", "Ankle Stability", "Neck Strength",
    "Wrist Stability", "Elbow Stability", "Lower Back Stability",
    "Conditioning", "Work Capacity", "VO2", "Anaerobic Capacity",
    "Aerobic Capacity", "Recovery",
]

# ==========================================================================
# 2. CATEGORY BASELINES
# ==========================================================================
# One row per exercises.json `category` value. Every score is 0-100 unless
# noted. Categories not listed fall back to _DEFAULT_PROFILE.
#
# "Recovery" here means "how much this movement itself doubles as active
# recovery" (low-difficulty mobility work scores high; max-effort barbell
# work scores near zero) — not to be confused with recovery_time_hours below,
# which is how long the body needs *after* the exercise.
CATEGORY_PROFILES: Dict[str, Dict] = {
    "Horizontal Push": dict(
        plane="Sagittal", chain="Closed Chain", force="Concentric",
        stability=45, balance=25, coordination=35, mobility=30,
        tags=dict(**{
            "Max Strength": 55, "Relative Strength": 65, "Hypertrophy": 60,
            "Muscular Endurance": 45, "Power": 35, "Explosiveness": 25,
            "Core Stability": 40, "Anti Extension": 35,
            "Shoulder Stability": 40, "Grip Strength": 15,
        }),
    ),
    "Vertical Push": dict(
        plane="Sagittal", chain="Open Chain", force="Concentric",
        stability=65, balance=40, coordination=45, mobility=45,
        tags=dict(**{
            "Max Strength": 55, "Relative Strength": 60, "Hypertrophy": 55,
            "Power": 35, "Core Stability": 45, "Anti Extension": 30,
            "Shoulder Stability": 60, "Neck Strength": 25, "Grip Strength": 20,
        }),
    ),
    "Horizontal Pull": dict(
        plane="Sagittal", chain="Open Chain", force="Concentric",
        stability=40, balance=25, coordination=35, mobility=25,
        tags=dict(**{
            "Max Strength": 55, "Relative Strength": 55, "Hypertrophy": 55,
            "Muscular Endurance": 45, "Grip Strength": 40, "Grip Endurance": 35,
            "Core Stability": 30, "Shoulder Stability": 35,
        }),
    ),
    "Vertical Pull": dict(
        plane="Sagittal", chain="Open Chain", force="Concentric",
        stability=50, balance=25, coordination=40, mobility=35,
        tags=dict(**{
            "Max Strength": 55, "Relative Strength": 65, "Hypertrophy": 55,
            "Muscular Endurance": 45, "Grip Strength": 55, "Grip Endurance": 45,
            "Core Stability": 35, "Shoulder Stability": 45,
        }),
    ),
    "Squat": dict(
        plane="Sagittal", chain="Closed Chain", force="Concentric",
        stability=45, balance=35, coordination=30, mobility=45,
        tags=dict(**{
            "Max Strength": 65, "Relative Strength": 60, "Hypertrophy": 60,
            "Muscular Endurance": 40, "Power": 40, "Knee Stability": 45,
            "Hip Stability": 40, "Core Stability": 35,
        }),
    ),
    "Hinge": dict(
        plane="Sagittal", chain="Closed Chain", force="Concentric",
        stability=45, balance=30, coordination=35, mobility=40,
        tags=dict(**{
            "Max Strength": 70, "Relative Strength": 60, "Hypertrophy": 55,
            "Power": 45, "Rate of Force Development": 30, "Hip Stability": 50,
            "Grip Strength": 35, "Core Stability": 40, "Anti Flexion": 35,
        }),
    ),
    "Core": dict(
        plane="Multi-planar", chain="Hybrid", force="Isometric",
        stability=65, balance=40, coordination=35, mobility=25,
        tags=dict(**{
            "Core Stability": 75, "Anti Rotation": 30, "Anti Extension": 30,
            "Anti Flexion": 30, "Anti Lateral Flexion": 30,
            "Muscular Endurance": 45, "Hip Stability": 25,
        }),
    ),
    "Full Body": dict(
        plane="Multi-planar", chain="Hybrid", force="Stretch-Shortening Cycle",
        stability=55, balance=45, coordination=55, mobility=35,
        tags=dict(**{
            "Power": 55, "Explosiveness": 45, "Rate of Force Development": 40,
            "Work Capacity": 50, "Conditioning": 45, "Core Stability": 40,
            "Grip Strength": 35, "Anaerobic Capacity": 40,
        }),
    ),
    "Carry": dict(
        plane="Sagittal", chain="Closed Chain", force="Isometric",
        stability=55, balance=40, coordination=30, mobility=20,
        tags=dict(**{
            "Grip Strength": 65, "Grip Endurance": 70, "Core Stability": 55,
            "Anti Lateral Flexion": 40, "Work Capacity": 55,
            "Muscular Endurance": 50, "Conditioning": 40,
        }),
    ),
    "Grip": dict(
        plane="Sagittal", chain="Open Chain", force="Isometric",
        stability=35, balance=15, coordination=20, mobility=15,
        tags=dict(**{
            "Grip Strength": 75, "Grip Endurance": 60, "Muscular Endurance": 30,
        }),
    ),
    "Jump": dict(
        plane="Sagittal", chain="Closed Chain", force="Stretch-Shortening Cycle",
        stability=40, balance=45, coordination=55, mobility=30,
        tags=dict(**{
            "Power": 70, "Explosiveness": 65, "Reactive Strength": 60,
            "Elastic Strength": 55, "Rate of Force Development": 55,
            "Acceleration": 40, "Knee Stability": 30, "Ankle Stability": 35,
        }),
    ),
    "Power": dict(
        plane="Multi-planar", chain="Closed Chain", force="Stretch-Shortening Cycle",
        stability=45, balance=40, coordination=55, mobility=30,
        tags=dict(**{
            "Power": 75, "Explosiveness": 65, "Rate of Force Development": 60,
            "Acceleration": 40, "Hip Stability": 30,
        }),
    ),
    "Conditioning": dict(
        plane="Multi-planar", chain="Hybrid", force="Concentric",
        stability=25, balance=20, coordination=30, mobility=20,
        tags=dict(**{
            "Conditioning": 75, "Work Capacity": 70, "VO2": 60,
            "Anaerobic Capacity": 55, "Aerobic Capacity": 50,
            "Muscular Endurance": 45,
        }),
    ),
    "Sport Specific": dict(
        plane="Multi-planar", chain="Hybrid", force="Stretch-Shortening Cycle",
        stability=50, balance=45, coordination=60, mobility=35,
        tags=dict(**{
            "Agility": 45, "Change of Direction": 40, "Power": 40,
            "Reactive Strength": 35, "Core Stability": 35,
        }),
    ),
}

_DEFAULT_PROFILE = dict(
    plane="Sagittal", chain="Hybrid", force="Concentric",
    stability=35, balance=30, coordination=30, mobility=30,
    tags={},
)

# All tags default to this floor before category/exercise adjustments, so
# every exercise reports a full, consistent tag set rather than sparse zeros.
_TAG_FLOOR = 10


# ==========================================================================
# 3. PER-EXERCISE MODIFIERS
# ==========================================================================
# Small, explainable nudges on top of the category baseline, driven by real
# fields already on the exercise — not invented per exercise.

_UNILATERAL_MARKERS = ("single", "one-arm", "one arm", "pistol", "bulgarian", "archer", "uneven")
_ALTERNATING_MARKERS = ("alternating", "walking lunge", "farmer")


# ==========================================================================
# EQUIPMENT CATALOG — groups exercises.json's ~65 raw `equipment` strings
# into the buckets a person actually shops/thinks in (Free Weights, Machines,
# Strongman, etc.), so the equipment browser can show "Free Weights" as a
# section instead of one un-grouped alphabetical checkbox list. Any
# equipment string found in the data but not listed here falls into "Other"
# automatically (build_equipment_catalog below) rather than silently
# disappearing - so this list drifting behind new exercises.json entries
# degrades gracefully instead of hiding equipment from the browser.
# ==========================================================================
EQUIPMENT_CATEGORIES: Dict[str, List[str]] = {
    "Bodyweight": ["Bodyweight", "Suspension Trainer", "Rings", "Parallel Bars", "Pull-up Bar"],
    "Free Weights": [
        "Barbell", "Dumbbell", "Kettlebell", "EZ Curl Bar", "Trap Bar",
        "Safety Squat Bar", "Cambered Bar", "Swiss Bar", "Buffalo Bar",
        "Log Bar", "Axle Bar", "Landmine", "Medicine Ball",
    ],
    "Machines": [
        "Cable Machine", "Lat Pulldown Machine", "Leg Press Machine",
        "Leg Curl Machine", "Leg Extension Machine", "Chest Press Machine",
        "Shoulder Press Machine", "Seated Row Machine", "High Row Machine",
        "Pec Deck Machine", "Hack Squat Machine", "Smith Machine",
        "Pendulum Squat Machine", "V Squat Machine", "Belt Squat Machine",
        "Plate-Loaded Lever Machine",
    ],
    "Racks & Benches": [
        "Power Rack", "Squat Rack", "Hyperextension Bench", "Seal Row Bench",
        "GHD", "Captain's Chair", "Reverse Hyper", "Belt Squat",
    ],
    "Strongman": [
        "Atlas Stone", "Husafell Stone", "Conan's Wheel", "Yoke", "Sled",
        "Tire", "Keg", "Sandbag", "Farmer Handles", "Fingal's Fingers", "Log Bar",
    ],
    "Conditioning": [
        "Assault Bike", "Rowing Erg", "Jump Rope", "Battle Ropes",
        "Agility Ladder", "Plyo Box", "Weighted Vest",
    ],
    "Grip & Accessory": ["Ab Wheel", "Resistance Band", "Climbing Hangboard"],
    "Combat Sport": ["Boxing Heavy Bag", "Tackle Bag", "Wrestling Dummy"],
}

_EQUIPMENT_TO_CATEGORY: Dict[str, str] = {
    eq: cat for cat, items in EQUIPMENT_CATEGORIES.items() for eq in items
}


def build_equipment_catalog(exercises: List[Dict]) -> List[Dict]:
    """One row per equipment type actually present in the database: which
    shopping/gym-area category it belongs to, how many exercises it
    unlocks, and which movement categories those exercises cover - e.g. a
    Kettlebell row showing categories=['Horizontal Push','Hinge','Squat',
    'Carry','Core',...] is the concrete answer to "kettlebell should cover
    everything, not just swings" - a person can see, before picking it,
    that it actually does. Grouped by EQUIPMENT_CATEGORIES section so the
    browser can render sections instead of one flat alphabetical list."""
    by_equipment: Dict[str, Dict] = {}
    for ex in exercises:
        eq = ex.get("equipment", "Bodyweight")
        entry = by_equipment.setdefault(eq, {"count": 0, "categories": set(), "sports": set()})
        entry["count"] += 1
        if ex.get("category"):
            entry["categories"].add(ex["category"])
        entry["sports"].update(ex.get("sport_priority", {}).keys())

    rows = []
    for eq, info in by_equipment.items():
        rows.append({
            "equipment": eq,
            "group": _EQUIPMENT_TO_CATEGORY.get(eq, "Other"),
            "exercise_count": info["count"],
            "movement_categories": sorted(info["categories"]),
            # A rough "how much of the movement library does this equipment
            # alone cover" signal - 8 is the number of loaded-strength +
            # carry/core categories in the database (see main.py's
            # _LOADED_STRENGTH_CATEGORIES plus Carry/Core).
            "pattern_coverage": len(info["categories"]),
        })
    rows.sort(key=lambda r: (r["group"], -r["exercise_count"]))
    return rows


def _movement_type(ex: Dict) -> str:
    name = ex.get("name", "").lower()
    pattern = (ex.get("movement_pattern") or "").lower()
    if any(m in name for m in _ALTERNATING_MARKERS):
        return "Alternating"
    if any(m in name for m in _UNILATERAL_MARKERS):
        return "Unilateral"
    if "carry" in pattern or ex.get("category") == "Carry":
        return "Bilateral"
    return "Bilateral"


def _movement_plane(ex: Dict, base_plane: str) -> str:
    pattern = (ex.get("movement_pattern") or "").lower()
    name = (ex.get("name") or "").lower()
    if "rotat" in pattern or "rotat" in name or "chop" in name or "twist" in name:
        return "Transverse"
    if "lunge" in pattern or "lateral" in name:
        return "Frontal"
    if pattern in ("complex", "ballistic") or ex.get("category") in ("Full Body", "Sport Specific"):
        return "Multi-planar"
    return base_plane


def _force_type(ex: Dict, base_force: str) -> str:
    pattern = (ex.get("movement_pattern") or "")
    if pattern == "Isometric":
        return "Isometric"
    if pattern in ("Ballistic", "Explosive Pull", "Jump", "Throw"):
        return "Stretch-Shortening Cycle"
    return base_force


def _velocity_type(ex: Dict) -> str:
    pattern = (ex.get("movement_pattern") or "")
    difficulty = ex.get("difficulty", 1)
    if pattern in ("Jump", "Throw", "Ballistic"):
        return "Reactive"
    if pattern == "Explosive Pull":
        return "Explosive"
    if ex.get("category") in ("Conditioning",):
        return "Speed Strength"
    if difficulty >= 4 and ex.get("equipment") in ("Barbell", "Trap Bar", "Power Rack"):
        return "Max Strength"
    return "Slow Strength"


def _chain_type(ex: Dict, base_chain: str) -> str:
    pattern = (ex.get("movement_pattern") or "")
    if pattern in ("Throw", "Ballistic") or ex.get("equipment") in ("Medicine Ball", "Battle Ropes"):
        return "Open Chain"
    return base_chain


# Public (not underscore-prefixed): knowledge_graph.py imports this directly
# instead of keeping its own copy, so the two modules can't drift out of sync
# the way they previously did (that drift was the root cause of the joint-
# node/rehab-candidacy gap on Wrist/Elbow/Lower Back - see the
# ATHLETIC_QUALITY_TAGS comment above). All 8 joints exercises.json actually
# carries in joint_stress are covered now, not just the original 5.
JOINT_STABILITY_TAG = {
    "Shoulder": "Shoulder Stability",
    "Hip": "Hip Stability",
    "Knee": "Knee Stability",
    "Ankle": "Ankle Stability",
    "Neck": "Neck Strength",
    "Wrist": "Wrist Stability",
    "Elbow": "Elbow Stability",
    "Lower Back": "Lower Back Stability",
}

_GRIP_EQUIPMENT = {"Barbell", "Kettlebell", "Pull-up Bar", "Rings", "Farmer Handles",
                    "Trap Bar", "Climbing Hangboard", "Battle Ropes"}


def enrich_exercise(ex: Dict) -> Dict:
    """Return the v4.0 additive fields for one exercise. Never reads intent
    to overwrite an existing key — caller decides how to merge, and every
    field returned here is new in v4.0 (see the ABSOLUTE RULES the upgrade
    prompt itself sets: don't remove or rename existing fields)."""
    category = ex.get("category")
    profile = CATEGORY_PROFILES.get(category, _DEFAULT_PROFILE)
    difficulty = ex.get("difficulty", 1)
    equipment = ex.get("equipment", "Bodyweight")
    joint_stress = ex.get("joint_stress", [])

    # ---- movement analysis ----
    movement_plane = _movement_plane(ex, profile["plane"])
    movement_type = _movement_type(ex)
    chain_type = _chain_type(ex, profile["chain"])
    force_type = _force_type(ex, profile["force"])
    velocity_type = _velocity_type(ex)

    # Instability equipment (rings, kettlebells, single-limb work) bumps the
    # stabilizer-demand fields; nothing here is invented from scratch, it's a
    # fixed +/- nudge off the category baseline.
    instability_bonus = 15 if equipment in ("Rings", "Kettlebell") else 0
    instability_bonus += 10 if movement_type in ("Unilateral", "Alternating") else 0

    stability_requirement = min(100, profile["stability"] + instability_bonus + difficulty * 3)
    balance_requirement = min(100, profile["balance"] + instability_bonus + difficulty * 2)
    coordination_requirement = min(100, profile["coordination"] + (10 if force_type == "Stretch-Shortening Cycle" else 0) + difficulty * 3)
    mobility_requirement = min(100, profile["mobility"] + difficulty * 2)

    technical_complexity = max(1, min(5, round(difficulty * 0.8 + (1 if force_type == "Stretch-Shortening Cycle" else 0))))
    learning_curve = max(1, min(5, round(technical_complexity * 0.9 + (1 if equipment in ("Rings", "Barbell") else 0))))
    skill_requirement = max(1, min(5, round((technical_complexity + learning_curve) / 2)))

    cns_load_equipment = equipment in ("Barbell", "Trap Bar", "Power Rack", "Rings")
    CNS_fatigue = min(100, difficulty * 15 + (15 if force_type == "Stretch-Shortening Cycle" else 0) + (10 if cns_load_equipment else 0))
    fatigue_cost = min(100, difficulty * 14 + (10 if category in ("Conditioning", "Full Body", "Carry") else 0))
    recovery_time_hours = round(12 + CNS_fatigue * 0.6)

    # ---- athletic quality tags ----
    tags = {t: _TAG_FLOOR for t in ATHLETIC_QUALITY_TAGS}
    tags.update(profile.get("tags", {}))

    # Difficulty scales strength/power-adjacent qualities but not conditioning
    # qualities (a hard set of 5 heavy squats isn't "more conditioning").
    strength_adjacent = (
        "Max Strength", "Relative Strength", "Hypertrophy", "Power",
        "Explosiveness", "Rate of Force Development",
    )
    for t in strength_adjacent:
        if t in tags and tags[t] > _TAG_FLOOR:
            tags[t] = min(100, round(tags[t] + (difficulty - 3) * 5))

    # Joint-stressed = joint-trained: an exercise that stresses the shoulder
    # is, by definition, building shoulder stability under load.
    for joint in joint_stress:
        tag = JOINT_STABILITY_TAG.get(joint)
        if tag:
            tags[tag] = min(100, max(tags.get(tag, _TAG_FLOOR), 30 + difficulty * 8))

    if equipment in _GRIP_EQUIPMENT:
        tags["Grip Strength"] = min(100, max(tags["Grip Strength"], 35 + difficulty * 5))
        tags["Grip Endurance"] = min(100, max(tags["Grip Endurance"], 25 + difficulty * 4))

    if movement_type == "Unilateral":
        tags["Agility"] = min(100, tags.get("Agility", _TAG_FLOOR) + 10)
        tags["Change of Direction"] = min(100, tags.get("Change of Direction", _TAG_FLOOR) + 5)

    if movement_plane == "Transverse":
        tags["Rotational Power"] = min(100, max(tags.get("Rotational Power", _TAG_FLOOR), 35 + difficulty * 8))
        tags["Anti Rotation"] = min(100, max(tags.get("Anti Rotation", _TAG_FLOOR), 30 + difficulty * 6))

    if force_type == "Isometric":
        tags["Muscular Endurance"] = min(100, tags.get("Muscular Endurance", _TAG_FLOOR) + 10)

    if force_type == "Stretch-Shortening Cycle":
        tags["Reactive Strength"] = min(100, max(tags.get("Reactive Strength", _TAG_FLOOR), 35 + difficulty * 8))
        tags["Elastic Strength"] = min(100, max(tags.get("Elastic Strength", _TAG_FLOOR), 30 + difficulty * 7))

    # "Recovery" tag = how much this movement doubles as active recovery for
    # the athlete, which is the inverse of how taxing it is.
    tags["Recovery"] = max(0, 100 - CNS_fatigue - fatigue_cost // 2)

    return {
        "movement_plane": movement_plane,
        "movement_type": movement_type,
        "chain_type": chain_type,
        "force_type": force_type,
        "velocity_type": velocity_type,
        "stability_requirement": stability_requirement,
        "balance_requirement": balance_requirement,
        "coordination_requirement": coordination_requirement,
        "mobility_requirement": mobility_requirement,
        "technical_complexity": technical_complexity,
        "learning_curve": learning_curve,
        "skill_requirement": skill_requirement,
        "fatigue_cost": fatigue_cost,
        "CNS_fatigue": CNS_fatigue,
        "recovery_time_hours": recovery_time_hours,
        "athletic_qualities": tags,
    }
