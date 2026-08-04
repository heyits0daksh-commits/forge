"""
generate_batch5_manual_part7_gaps.py — adds the handful of exercises the
Combat Sports & Rugby S&C Manual names in Part 7 (variation library) and
Part 7.7 (injury-friendly substitution table) that weren't already in the
database under any name. Nearly everything in Part 7 already existed
(Hang Power Clean -> "Barbell Hang Power Clean", Landmine Press/Row/Squat,
GHD Back/Hip Extension, Nordic Hamstring Curl, Belt Squat family, Kettlebell
Swing/Clean & Press/Turkish Get-Up, box/broad/lateral/depth jumps, Seal Row,
Pendlay Row, Weighted Pull-Up/Dip, etc. all pre-date this pass) - this file
is deliberately small, covering only the genuine gaps:

  - Band-Assisted Pull-Up / Band-Assisted Dip (Part 7.3's named regression
    step "while building toward strict bodyweight reps" - the database had
    Negative Pull-Up as a regression but no band-assisted option).
  - Landmine Anti-Rotation Press / "half-kneeling" (Part 7.5's core/prehab
    option - the database had Landmine Press, Landmine Rotation, and
    Landmine Row, but not this anti-rotation variant).
  - Neutral-Grip Dumbbell Press (Part 7.7's named shoulder-pain substitute
    for bench/overhead press - the database had "Neutral Grip Pull-Up" but
    no neutral-grip *press*).
  - Fat-Grip Row (Part 7.7's named elbow-pain ["grappler's elbow"]
    substitute for curls/strict pull-ups - reduces direct forearm/elbow
    loading vs. a standard-grip row).

Same authoring discipline as batch2-4: base fields (id, name, category,
movement_pattern, difficulty, experience_level, equipment, equipment_level,
muscles, joint_stress, injuries_to_avoid, strength_requirements,
progressions/regressions/alternatives, sport_priority) are hand-tagged from
real biomechanics; run enrich_exercises.py afterward to derive the v4.0+
movement-analysis/athletic-quality fields the same way every other exercise
in the file gets them, so nothing is hand-faked.

Run: python scripts/generate_batch5_manual_part7_gaps.py
Then: python scripts/enrich_exercises.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from backend.core.config import settings
    SRC = settings.EXERCISES_JSON_PATH
    BACKUP = settings.BACKUP_DIR / "exercises_pre_batch5_backup.json"
except ModuleNotFoundError:
    # pydantic isn't installed in this environment - fall back to the same
    # paths config.py would have resolved (data/exercises.json,
    # data/backups/), so this script still runs standalone.
    _ROOT = Path(__file__).resolve().parent.parent
    SRC = _ROOT / "data" / "exercises.json"
    BACKUP = _ROOT / "data" / "backups" / "exercises_pre_batch5_backup.json"

# Same 13-sport set every other exercise in the file carries (12 from
# batch2-4 plus MMA, backfilled onto every exercise by add_mma_sport.py) -
# ratings follow the same logic as batch4's per-archetype tables, adjusted
# per movement.
SPORTS_PULL_REGRESSION = {  # Band-Assisted Pull-Up: same audience as Weighted Pull-Up/Neutral Grip Pull-Up, slightly lower (it's a regression, not the target strength stimulus)
    "Wrestling": 55, "Judo": 55, "Sambo": 50, "BJJ": 60, "Boxing": 45,
    "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 50,
    "Rock Climbing": 55, "HYROX": 40, "Special Forces": 55, "MMA": 55,
}
SPORTS_PUSH_REGRESSION = {  # Band-Assisted Dip
    "Wrestling": 45, "Judo": 40, "Sambo": 40, "BJJ": 40, "Boxing": 50,
    "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 45,
    "Rock Climbing": 30, "HYROX": 35, "Special Forces": 45, "MMA": 45,
}
SPORTS_ROTATIONAL_CORE = {  # Landmine Anti-Rotation Press
    "Wrestling": 50, "Judo": 45, "Sambo": 45, "BJJ": 50, "Boxing": 65,
    "Muay Thai": 60, "Kickboxing": 60, "Sanda": 55, "Rugby": 55,
    "Rock Climbing": 35, "HYROX": 40, "Special Forces": 45, "MMA": 55,
}
SPORTS_SHOULDER_FRIENDLY_PRESS = {  # Neutral-Grip Dumbbell Press
    "Wrestling": 55, "Judo": 50, "Sambo": 50, "BJJ": 45, "Boxing": 60,
    "Muay Thai": 55, "Kickboxing": 55, "Sanda": 55, "Rugby": 60,
    "Rock Climbing": 30, "HYROX": 55, "Special Forces": 60, "MMA": 55,
}
SPORTS_ELBOW_FRIENDLY_ROW = {  # Fat-Grip Row
    "Wrestling": 60, "Judo": 55, "Sambo": 55, "BJJ": 60, "Boxing": 45,
    "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 55,
    "Rock Climbing": 55, "HYROX": 45, "Special Forces": 55, "MMA": 55,
}

NEW_EXERCISES = [
    {
        "id": "band_assisted_pullup_001",
        "name": "Band-Assisted Pull-Up",
        "category": "Vertical Pull",
        "movement_pattern": "Pull",
        "difficulty": 1,
        "experience_level": "Beginner",
        "equipment": "Resistance Band",
        "equipment_level": 2,
        "primary_muscles": ["Latissimus Dorsi"],
        "secondary_muscles": ["Biceps Brachii", "Rhomboids"],
        "stabilizers": ["Core"],
        "joint_stress": ["Shoulder", "Elbow"],
        "injuries_to_avoid": [],
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0, "pullups": 0, "pushups": 0},
        "progressions": ["pullup_001"],
        "regressions": ["negative_pullup_001"],
        "alternatives": ["pullup_001"],
        "sport_priority": SPORTS_PULL_REGRESSION,
    },
    {
        "id": "band_assisted_dip_001",
        "name": "Band-Assisted Dip",
        "category": "Vertical Push",
        "movement_pattern": "Push",
        "difficulty": 1,
        "experience_level": "Beginner",
        "equipment": "Resistance Band",
        "equipment_level": 2,
        "primary_muscles": ["Triceps Brachii", "Pectoralis Major"],
        "secondary_muscles": ["Anterior Deltoid"],
        "stabilizers": ["Core"],
        "joint_stress": ["Shoulder", "Elbow"],
        "injuries_to_avoid": ["Shoulder Instability"],
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0, "pullups": 0, "pushups": 0},
        "progressions": ["parallel_bar_dip_001"],
        "regressions": [],
        "alternatives": ["parallel_bar_dip_001"],
        "sport_priority": SPORTS_PUSH_REGRESSION,
    },
    {
        "id": "landmine_antirotation_press_001",
        "name": "Landmine Anti-Rotation Press (Half-Kneeling)",
        "category": "Vertical Push",
        "movement_pattern": "Push",
        "difficulty": 2,
        "experience_level": "Novice",
        "equipment": "Landmine",
        "equipment_level": 23,
        "primary_muscles": ["Anterior Deltoid", "Rectus Abdominis"],
        "secondary_muscles": ["Triceps Brachii", "Obliques"],
        "stabilizers": ["Rotator Cuff", "Gluteus Medius"],
        "joint_stress": ["Shoulder", "Lower Back"],
        "injuries_to_avoid": ["Shoulder Instability", "Lower Back Strain"],
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0, "pullups": 0, "pushups": 0},
        "progressions": [],
        "regressions": [],
        "alternatives": ["landmine_press_001"],
        "sport_priority": SPORTS_ROTATIONAL_CORE,
    },
    {
        "id": "db_neutralgrip_press_001",
        "name": "Neutral-Grip Dumbbell Press",
        "category": "Horizontal Push",
        "movement_pattern": "Push",
        "difficulty": 2,
        "experience_level": "Novice",
        "equipment": "Dumbbell",
        "equipment_level": 3,
        "primary_muscles": ["Pectoralis Major", "Anterior Deltoid"],
        "secondary_muscles": ["Triceps Brachii"],
        "stabilizers": ["Rotator Cuff"],
        "joint_stress": ["Shoulder", "Elbow"],
        "injuries_to_avoid": ["Shoulder Instability", "Rotator Cuff"],
        "strength_requirements": {"bench_ratio": 0.35, "squat_ratio": 0.0, "deadlift_ratio": 0.0, "pullups": 0, "pushups": 0},
        "progressions": [],
        "regressions": [],
        "alternatives": ["db_bench_press_001", "landmine_press_001"],
        "sport_priority": SPORTS_SHOULDER_FRIENDLY_PRESS,
    },
    {
        "id": "fatgrip_row_001",
        "name": "Fat-Grip Row",
        "category": "Horizontal Pull",
        "movement_pattern": "Pull",
        "difficulty": 2,
        "experience_level": "Novice",
        "equipment": "Barbell",
        "equipment_level": 5,
        "primary_muscles": ["Latissimus Dorsi", "Rhomboids"],
        "secondary_muscles": ["Rear Deltoid"],
        "stabilizers": ["Forearm Flexors", "Core"],
        "joint_stress": ["Shoulder"],
        "injuries_to_avoid": [],
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0, "pullups": 0, "pushups": 0},
        "progressions": [],
        "regressions": [],
        "alternatives": ["bb_bent_over_row_001"],
        "sport_priority": SPORTS_ELBOW_FRIENDLY_ROW,
    },
]


def main():
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, BACKUP)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = {e["id"] for e in data["exercises"]}
    existing_names_lower = {e["name"].lower() for e in data["exercises"]}

    added = 0
    for ex in NEW_EXERCISES:
        if ex["id"] in existing_ids or ex["name"].lower() in existing_names_lower:
            print(f"SKIP (already present): {ex['name']}")
            continue
        # Drop dangling progression/regression/alternative references (an
        # id that doesn't exist in this database yet) rather than writing a
        # broken pointer - keeps the DAG-acyclicity/no-dangling-refs
        # invariant the README says was verified after every prior batch.
        for key in ("progressions", "regressions", "alternatives"):
            ex[key] = [rid for rid in ex[key] if rid in existing_ids]
        data["exercises"].append(ex)
        existing_ids.add(ex["id"])
        existing_names_lower.add(ex["name"].lower())
        added += 1

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Added {added} exercises. Backup written to {BACKUP}.")


if __name__ == "__main__":
    main()
