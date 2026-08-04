"""
generate_batch3_equipment.py — adds 5 new equipment types and 12 new,
fully-tagged exercises to exercises.json.

WHY THESE 5: Squat Rack, Belt Squat, Reverse Hyper, Seal Row Bench, and
Hyperextension Bench are staple powerlifting/strength-and-conditioning gym
equipment that were missing from the set — all lower-back and posterior-chain
friendly tools that fit FORGE's injury-aware programming niche particularly
well (belt squat and reverse hyper in particular are commonly prescribed as
*rehab-friendly* alternatives to axially-loaded barbell work, since they take
compressive spinal load out of the movement).

Follows the exact pattern of generate_batch2_equipment.py: hand-tagged
joint_stress / injuries_to_avoid per exercise (not machine-generated), small
and reviewable rather than exhaustive.

Run: python scripts/generate_batch3_equipment.py
Then: python scripts/enrich_exercises.py   (derives v4.0 fields for the new entries)
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.core.config import settings

SRC = settings.EXERCISES_JSON_PATH
BACKUP = settings.BACKUP_DIR / "exercises_pre_batch3_backup.json"

TEMPLATES = {
    # heavy barbell squat-pattern work done in a rack — general strength sports
    "rack_squat": {"Wrestling": 75, "Judo": 70, "Sambo": 75, "BJJ": 55, "Boxing": 45,
                   "Muay Thai": 50, "Kickboxing": 50, "Sanda": 50, "Rugby": 90,
                   "Rock Climbing": 25, "HYROX": 70, "Special Forces": 85},
    # belt squat — leg strength with spine decompressed, good for grapplers/combat
    "belt_squat": {"Wrestling": 80, "Judo": 75, "Sambo": 80, "BJJ": 65, "Boxing": 50,
                   "Muay Thai": 55, "Kickboxing": 55, "Sanda": 55, "Rugby": 80,
                   "Rock Climbing": 30, "HYROX": 65, "Special Forces": 80},
    # reverse hyper / posterior-chain rehab & resilience work
    "reverse_hyper": {"Wrestling": 65, "Judo": 60, "Sambo": 65, "BJJ": 55, "Boxing": 45,
                       "Muay Thai": 50, "Kickboxing": 50, "Sanda": 50, "Rugby": 75,
                       "Rock Climbing": 35, "HYROX": 55, "Special Forces": 65},
    # chest-supported row accessory work
    "row_accessory": {"Wrestling": 55, "Judo": 55, "Sambo": 55, "BJJ": 55, "Boxing": 45,
                       "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 60,
                       "Rock Climbing": 60, "HYROX": 45, "Special Forces": 55},
    # 45-degree back extension work
    "back_extension": {"Wrestling": 60, "Judo": 60, "Sambo": 60, "BJJ": 55, "Boxing": 45,
                        "Muay Thai": 50, "Kickboxing": 50, "Sanda": 50, "Rugby": 65,
                        "Rock Climbing": 40, "HYROX": 60, "Special Forces": 65},
}


def sp(template, **overrides):
    d = dict(TEMPLATES[template])
    d.update(overrides)
    return d


def ex(id_, name, category, pattern, difficulty, level, equipment, eq_level,
       primary, secondary, stabilizers, joint_stress, injuries, reqs,
       template, **sp_overrides):
    return {
        "id": id_, "name": name, "category": category, "movement_pattern": pattern,
        "difficulty": difficulty, "experience_level": level,
        "equipment": equipment, "equipment_level": eq_level,
        "primary_muscles": primary, "secondary_muscles": secondary, "stabilizers": stabilizers,
        "joint_stress": joint_stress, "injuries_to_avoid": injuries,
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0,
                                   "pullups": 0, "pushups": 0, **reqs},
        "progressions": [], "regressions": [], "alternatives": [],
        "sport_priority": sp(template, **sp_overrides),
    }


NEW = []

# ---- Squat Rack (33) ----
NEW += [
ex("rack_pinsquat_001", "Pin Squat", "Squat", "Squat", 3, "Intermediate", "Squat Rack", 33,
   ["Quadriceps"], ["Glutes", "Hamstrings"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain"],
   {"squat_ratio": 0.75}, "rack_squat"),
ex("rack_boxsquat_001", "Box Squat", "Squat", "Squat", 3, "Intermediate", "Squat Rack", 33,
   ["Quadriceps", "Glutes"], ["Hamstrings"], ["Core"],
   ["Knee", "Hip", "Lower Back"], ["Low Back Pain"],
   {"squat_ratio": 0.8}, "rack_squat"),
ex("rack_pull_001", "Rack Pull", "Hinge", "Pull", 3, "Intermediate", "Squat Rack", 33,
   ["Erector Spinae", "Glutes"], ["Traps", "Hamstrings"], ["Forearms"],
   ["Lower Back"], ["Low Back Pain", "SI Joint Ligaments Sprain - Grade II Sprain (Partial Tear)"],
   {"deadlift_ratio": 0.9}, "rack_squat"),
]

# ---- Belt Squat (34) ----
NEW += [
ex("beltsquat_001", "Belt Squat", "Squat", "Squat", 2, "Novice", "Belt Squat", 34,
   ["Quadriceps"], ["Glutes", "Hamstrings"], [],
   ["Knee", "Hip"], ["Meniscus Tear - Grade 3 (True Structural Tear)"],
   {"squat_ratio": 0.5}, "belt_squat"),
ex("beltsquat_splitsquat_001", "Belt Squat Split Squat", "Squat", "Lunge", 3, "Intermediate", "Belt Squat", 34,
   ["Quadriceps", "Glutes"], ["Hamstrings"], ["Core"],
   ["Knee", "Hip", "Ankle"], ["ACL/Ligament Tear - Grade 3 (Complete Rupture)"],
   {"squat_ratio": 0.3}, "belt_squat"),
ex("beltsquat_march_001", "Belt Squat March", "Carry", "Carry", 2, "Novice", "Belt Squat", 34,
   ["Hip Flexors", "Glutes"], ["Quadriceps", "Core"], ["Core"],
   ["Hip", "Knee"], [],
   {}, "belt_squat"),
]

# ---- Reverse Hyper (35) ----
NEW += [
ex("reversehyper_001", "Reverse Hyperextension", "Hinge", "Isometric", 2, "Novice", "Reverse Hyper", 35,
   ["Glutes", "Erector Spinae"], ["Hamstrings"], ["Core"],
   ["Lower Back", "Hip"], ["Low Back Pain"],
   {}, "reverse_hyper"),
ex("reversehyper_singleleg_001", "Single-Leg Reverse Hyper", "Hinge", "Isometric", 3, "Intermediate", "Reverse Hyper", 35,
   ["Glutes", "Erector Spinae"], ["Hamstrings"], ["Core"],
   ["Lower Back", "Hip"], ["Low Back Pain", "SI Joint Ligaments Sprain - Grade II Sprain (Partial Tear)"],
   {}, "reverse_hyper"),
]

# ---- Seal Row Bench (36) ----
NEW += [
ex("sealrow_001", "Seal Row", "Horizontal Pull", "Pull", 2, "Novice", "Seal Row Bench", 36,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii", "Rear Deltoid"], [],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 2}, "row_accessory"),
ex("sealrow_singlearm_001", "Single-Arm Seal Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Seal Row Bench", 36,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Obliques"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 2}, "row_accessory"),
]

# ---- Hyperextension Bench (37) ----
NEW += [
ex("hyperext_bw_001", "Bodyweight Hyperextension", "Hinge", "Isometric", 1, "Beginner", "Hyperextension Bench", 37,
   ["Erector Spinae"], ["Glutes", "Hamstrings"], [],
   ["Lower Back"], ["Low Back Pain"],
   {}, "back_extension"),
ex("hyperext_weighted_001", "Weighted Hyperextension", "Hinge", "Isometric", 2, "Novice", "Hyperextension Bench", 37,
   ["Erector Spinae"], ["Glutes", "Hamstrings"], ["Core"],
   ["Lower Back"], ["Low Back Pain", "Posterior Ligament Complex Sprain - Grade III Sprain (Complete Rupture)"],
   {}, "back_extension"),
]

print(f"Generated {len(NEW)} new exercises across "
      f"{len(set(e['equipment'] for e in NEW))} new equipment types.")


def main():
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, BACKUP)
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = {e["id"] for e in data["exercises"]}
    dupes = [e["id"] for e in NEW if e["id"] in existing_ids]
    if dupes:
        raise SystemExit(f"Duplicate IDs, aborting: {dupes}")

    data["exercises"].extend(NEW)
    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(data['exercises'])} total exercises to {SRC}. "
          f"Backup at {BACKUP}. Now run scripts/enrich_exercises.py.")


if __name__ == "__main__":
    main()
