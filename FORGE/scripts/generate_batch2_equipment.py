"""
generate_batch2_equipment.py — adds 20 new equipment types and 40 new,
fully-tagged exercises to exercises.json.

WHY THESE 20: they fill real gaps in the existing 22-equipment set —
standard commercial-gym machines that were completely absent (leg press,
lat pulldown, leg extension/curl, smith machine, etc.) plus functional/
tactical tools that fit FORGE's actual niche (landmine, GHD, sandbag,
weighted vest, TRX, heavy bag, jump rope, agility ladder, yoke).

WHY 40, NOT 1000+: every entry here is hand-tagged for joint_stress and
injuries_to_avoid based on real biomechanics, because that tagging is what
the injury-filtering engine actually depends on (see the Knee Push-Up bug
found in review — it was tagged joint_stress: [Wrist, Elbow, Shoulder]
with NO Knee tag despite being a kneeling, knee-loaded movement). Machine
generating thousands of entries without verifying each one's joint tags
would reproduce that exact bug at scale. This batch is small on purpose —
it's meant to be reviewed, not trusted blindly.

Run: python scripts/generate_batch2_equipment.py
Then: python scripts/enrich_exercises.py   (derives v4.0 fields for the new entries)
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.core.config import settings

SRC = settings.EXERCISES_JSON_PATH
BACKUP = settings.BACKUP_DIR / "exercises_pre_batch2_backup.json"

SPORTS = ["Wrestling", "Judo", "Sambo", "BJJ", "Boxing", "Muay Thai",
          "Kickboxing", "Sanda", "Rugby", "Rock Climbing", "HYROX", "Special Forces"]

TEMPLATES = {
    "machine_accessory": {"Wrestling": 40, "Judo": 35, "Sambo": 35, "BJJ": 35, "Boxing": 35,
                           "Muay Thai": 35, "Kickboxing": 35, "Sanda": 35, "Rugby": 45,
                           "Rock Climbing": 25, "HYROX": 35, "Special Forces": 40},
    "machine_leg": {"Wrestling": 55, "Judo": 55, "Sambo": 55, "BJJ": 45, "Boxing": 40,
                     "Muay Thai": 50, "Kickboxing": 50, "Sanda": 50, "Rugby": 65,
                     "Rock Climbing": 30, "HYROX": 55, "Special Forces": 60},
    "ghd_core": {"Wrestling": 70, "Judo": 70, "Sambo": 70, "BJJ": 70, "Boxing": 60,
                 "Muay Thai": 65, "Kickboxing": 65, "Sanda": 65, "Rugby": 70,
                 "Rock Climbing": 60, "HYROX": 75, "Special Forces": 80},
    "loaded_carry": {"Wrestling": 75, "Judo": 70, "Sambo": 75, "BJJ": 60, "Boxing": 55,
                      "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 85,
                      "Rock Climbing": 40, "HYROX": 95, "Special Forces": 95},
    "striking_bag": {"Wrestling": 50, "Judo": 45, "Sambo": 45, "BJJ": 45, "Boxing": 95,
                      "Muay Thai": 95, "Kickboxing": 95, "Sanda": 90, "Rugby": 55,
                      "Rock Climbing": 20, "HYROX": 40, "Special Forces": 70},
    "jump_rope": {"Wrestling": 65, "Judo": 60, "Sambo": 60, "BJJ": 55, "Boxing": 85,
                   "Muay Thai": 80, "Kickboxing": 80, "Sanda": 75, "Rugby": 60,
                   "Rock Climbing": 45, "HYROX": 80, "Special Forces": 80},
    "agility": {"Wrestling": 70, "Judo": 65, "Sambo": 65, "BJJ": 55, "Boxing": 65,
                "Muay Thai": 70, "Kickboxing": 70, "Sanda": 65, "Rugby": 90,
                "Rock Climbing": 35, "HYROX": 70, "Special Forces": 85},
    "landmine": {"Wrestling": 70, "Judo": 65, "Sambo": 65, "BJJ": 55, "Boxing": 60,
                 "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 80,
                 "Rock Climbing": 30, "HYROX": 75, "Special Forces": 80},
    "vest_loaded": {"Wrestling": 70, "Judo": 65, "Sambo": 65, "BJJ": 55, "Boxing": 55,
                     "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 80,
                     "Rock Climbing": 45, "HYROX": 90, "Special Forces": 95},
    "sandbag": {"Wrestling": 80, "Judo": 75, "Sambo": 80, "BJJ": 65, "Boxing": 55,
                "Muay Thai": 65, "Kickboxing": 65, "Sanda": 65, "Rugby": 85,
                "Rock Climbing": 35, "HYROX": 90, "Special Forces": 95},
    "trx": {"Wrestling": 65, "Judo": 65, "Sambo": 65, "BJJ": 60, "Boxing": 50,
            "Muay Thai": 55, "Kickboxing": 55, "Sanda": 55, "Rugby": 60,
            "Rock Climbing": 70, "HYROX": 55, "Special Forces": 70},
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

# ---- Leg Press Machine (13) ----
NEW += [
ex("legpress_bilateral_001", "Leg Press", "Squat", "Squat", 2, "Novice", "Leg Press Machine", 13,
   ["Quadriceps"], ["Glutes", "Hamstrings"], [],
   ["Knee", "Hip"], ["Meniscus Tear - Grade 3 (True Structural Tear)"],
   {"squat_ratio": 0.4}, "machine_leg"),
ex("legpress_singleleg_001", "Single-Leg Leg Press", "Squat", "Squat", 3, "Intermediate", "Leg Press Machine", 13,
   ["Quadriceps"], ["Glutes", "Hamstrings"], ["Core"],
   ["Knee", "Hip"], ["Meniscus Tear - Grade 3 (True Structural Tear)", "ACL/Ligament Tear - Grade 3 (Complete Rupture)"],
   {"squat_ratio": 0.25}, "machine_leg"),
]

# ---- Hack Squat Machine (14) ----
NEW += [
ex("hacksquat_001", "Hack Squat Machine", "Squat", "Squat", 3, "Intermediate", "Hack Squat Machine", 14,
   ["Quadriceps"], ["Glutes"], [],
   ["Knee", "Lower Back"], ["Meniscus Tear - Grade 3 (True Structural Tear)", "Patellofemoral Pain Syndrome (PFPS)"],
   {"squat_ratio": 0.5}, "machine_leg"),
]

# ---- Lat Pulldown Machine (15) ----
NEW += [
ex("latpulldown_wide_001", "Wide-Grip Lat Pulldown", "Vertical Pull", "Pull", 2, "Novice", "Lat Pulldown Machine", 15,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Rear Deltoid"], [],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 3}, "machine_accessory"),
ex("latpulldown_close_001", "Close-Grip Lat Pulldown", "Vertical Pull", "Pull", 2, "Novice", "Lat Pulldown Machine", 15,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Rhomboids"], [],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 3}, "machine_accessory"),
ex("latpulldown_singlearm_001", "Single-Arm Lat Pulldown", "Vertical Pull", "Pull", 3, "Intermediate", "Lat Pulldown Machine", 15,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Obliques"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 4}, "machine_accessory"),
]

# ---- Seated Row Machine (16) ----
NEW += [
ex("seatedrow_wide_001", "Wide-Grip Seated Row", "Horizontal Pull", "Pull", 2, "Novice", "Seated Row Machine", 16,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii", "Rear Deltoid"], [],
   ["Shoulder", "Lower Back"], ["Low Back Pain"],
   {"pullups": 2}, "machine_accessory"),
ex("seatedrow_singlearm_001", "Single-Arm Seated Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Seated Row Machine", 16,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Obliques"],
   ["Shoulder", "Lower Back"], ["Low Back Pain"],
   {"pullups": 2}, "machine_accessory"),
]

# ---- Leg Extension Machine (17) ----
NEW += [
ex("legext_001", "Leg Extension", "Squat", "Isometric", 2, "Novice", "Leg Extension Machine", 17,
   ["Quadriceps"], [], [],
   ["Knee"], ["ACL/Ligament Tear - Grade 3 (Complete Rupture)", "Jumper's Knee (Patellar Tendinopathy)",
              "Chondromalacia Patella", "Patellofemoral Pain Syndrome (PFPS)"],
   {}, "machine_accessory"),
]

# ---- Leg Curl Machine (18) ----
NEW += [
ex("legcurl_lying_001", "Lying Leg Curl", "Hinge", "Flexion", 2, "Novice", "Leg Curl Machine", 18,
   ["Hamstrings"], ["Calves"], [],
   ["Knee"], ["Meniscus Tear - Grade 3 (True Structural Tear)"],
   {}, "machine_accessory"),
ex("legcurl_seated_001", "Seated Leg Curl", "Hinge", "Flexion", 2, "Novice", "Leg Curl Machine", 18,
   ["Hamstrings"], ["Calves"], [],
   ["Knee"], ["Meniscus Tear - Grade 3 (True Structural Tear)"],
   {}, "machine_accessory"),
]

# ---- Pec Deck Machine (19) ----
NEW += [
ex("pecdeck_001", "Pec Deck Fly", "Horizontal Push", "Push", 2, "Novice", "Pec Deck Machine", 19,
   ["Pectoralis Major"], ["Anterior Deltoid"], [],
   ["Shoulder"], ["Shoulder Instability", "AC Ligament Sprain - Grade III Sprain (Complete Rupture)"],
   {}, "machine_accessory"),
]

# ---- Smith Machine (20) ----
NEW += [
ex("smith_squat_001", "Smith Machine Squat", "Squat", "Squat", 2, "Novice", "Smith Machine", 20,
   ["Quadriceps"], ["Glutes", "Hamstrings"], [],
   ["Knee", "Lower Back"], ["Low Back Pain", "Meniscus Tear - Grade 3 (True Structural Tear)"],
   {"squat_ratio": 0.55}, "machine_leg"),
ex("smith_bench_001", "Smith Machine Bench Press", "Horizontal Push", "Push", 2, "Novice", "Smith Machine", 20,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], [],
   ["Shoulder", "Elbow", "Wrist"], ["Shoulder Instability"],
   {"bench_ratio": 0.6}, "machine_accessory"),
]

# ---- EZ Curl Bar (21) ----
NEW += [
ex("ezbar_curl_001", "EZ Bar Curl", "Horizontal Pull", "Pull", 1, "Beginner", "EZ Curl Bar", 21,
   ["Biceps Brachii"], ["Forearms"], [],
   ["Elbow", "Wrist"], [],
   {}, "machine_accessory"),
ex("ezbar_skullcrusher_001", "EZ Bar Skullcrusher", "Horizontal Push", "Push", 2, "Novice", "EZ Curl Bar", 21,
   ["Triceps Brachii"], [], [],
   ["Elbow"], ["UCL Sprain - Grade III Sprain (Complete Rupture)"],
   {}, "machine_accessory"),
]

# ---- Safety Squat Bar (22) ----
NEW += [
ex("ssb_squat_001", "Safety Squat Bar Squat", "Squat", "Squat", 3, "Intermediate", "Safety Squat Bar", 22,
   ["Quadriceps"], ["Glutes", "Lower Back"], ["Core"],
   ["Knee", "Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"],
   {"squat_ratio": 0.85}, "machine_leg"),
]

# ---- Landmine (23) ----
NEW += [
ex("landmine_press_001", "Landmine Press", "Vertical Push", "Push", 2, "Novice", "Landmine", 23,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Rotator Cuff"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {}, "landmine"),
ex("landmine_row_001", "Landmine Row", "Horizontal Pull", "Pull", 2, "Novice", "Landmine", 23,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], ["Core"],
   ["Shoulder", "Lower Back"], ["Low Back Pain"],
   {}, "landmine"),
ex("landmine_rotation_001", "Landmine Rotation", "Core", "Rotational", 3, "Intermediate", "Landmine", 23,
   ["Obliques"], ["Anterior Deltoid", "Core"], ["Rotator Cuff"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "SI Joint Ligaments Sprain - Grade II Sprain (Partial Tear)"],
   {}, "landmine"),
]

# ---- GHD (24) ----
NEW += [
ex("ghd_situp_001", "GHD Sit-Up", "Core", "Flexion", 3, "Intermediate", "GHD", 24,
   ["Rectus Abdominis"], ["Hip Flexors"], [],
   ["Lower Back", "Hip"], ["Low Back Pain"],
   {}, "ghd_core"),
ex("ghd_backext_001", "GHD Back Extension", "Hinge", "Isometric", 2, "Novice", "GHD", 24,
   ["Erector Spinae"], ["Glutes", "Hamstrings"], [],
   ["Lower Back"], ["Low Back Pain", "Posterior Ligament Complex Sprain - Grade III Sprain (Complete Rupture)"],
   {}, "ghd_core"),
ex("ghd_hipext_001", "GHD Hip Extension", "Hinge", "Isometric", 2, "Novice", "GHD", 24,
   ["Glutes"], ["Hamstrings", "Erector Spinae"], [],
   ["Lower Back", "Hip"], ["Low Back Pain"],
   {}, "ghd_core"),
]

# ---- Ab Wheel (25) ----
NEW += [
ex("abwheel_rollout_001", "Ab Wheel Rollout", "Core", "Anti-Extension", 3, "Intermediate", "Ab Wheel", 25,
   ["Rectus Abdominis"], ["Lats", "Hip Flexors"], ["Core"],
   ["Lower Back", "Shoulder", "Wrist"], ["Low Back Pain", "Shoulder Instability"],
   {}, "ghd_core"),
]

# ---- Suspension Trainer / TRX (26) ----
NEW += [
ex("trx_row_001", "TRX Row", "Horizontal Pull", "Pull", 2, "Novice", "Suspension Trainer", 26,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Rotator Cuff"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"],
   {}, "trx"),
ex("trx_pushup_001", "TRX Push-Up", "Horizontal Push", "Push", 2, "Novice", "Suspension Trainer", 26,
   ["Pectoralis Major"], ["Triceps Brachii", "Core"], ["Rotator Cuff", "Core"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"],
   {"pushups": 15}, "trx"),
ex("trx_pistol_assist_001", "TRX Pistol Squat Assist", "Squat", "Squat", 3, "Intermediate", "Suspension Trainer", 26,
   ["Quadriceps"], ["Glutes"], ["Core"],
   ["Knee", "Ankle", "Shoulder"], ["ACL/Ligament Tear - Grade 3 (Complete Rupture)", "Meniscus Tear - Grade 3 (True Structural Tear)"],
   {"squat_ratio": 0.1}, "trx"),
]

# ---- Weighted Vest (27) ----
NEW += [
ex("vest_stepup_001", "Weighted Vest Step-Up", "Squat", "Lunge", 3, "Intermediate", "Weighted Vest", 27,
   ["Quadriceps", "Glutes"], ["Hamstrings"], ["Core"],
   ["Knee", "Hip"], ["Meniscus Tear - Grade 3 (True Structural Tear)", "ACL/Ligament Tear - Grade 3 (Complete Rupture)"],
   {}, "vest_loaded"),
ex("vest_ruck_001", "Weighted Vest Ruck March", "Carry", "Carry", 2, "Novice", "Weighted Vest", 27,
   ["Glutes", "Calves"], ["Quadriceps", "Erector Spinae"], ["Core"],
   ["Lower Back", "Knee", "Ankle"], ["Low Back Pain", "Stress Fracture - Tibia"],
   {}, "vest_loaded"),
ex("vest_pullup_001", "Weighted Vest Pull-Up", "Vertical Pull", "Pull", 4, "Advanced", "Weighted Vest", 27,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Rotator Cuff"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"],
   {"pullups": 10}, "vest_loaded"),
]

# ---- Sandbag (28) ----
NEW += [
ex("sandbag_clean_001", "Sandbag Clean", "Full Body", "Explosive Pull", 3, "Intermediate", "Sandbag", 28,
   ["Glutes", "Erector Spinae"], ["Quadriceps", "Traps"], ["Core", "Forearms"],
   ["Lower Back", "Knee"], ["Low Back Pain"],
   {}, "sandbag"),
ex("sandbag_carry_001", "Sandbag Carry", "Carry", "Carry", 2, "Novice", "Sandbag", 28,
   ["Erector Spinae", "Forearms"], ["Glutes", "Core"], ["Core"],
   ["Lower Back"], ["Low Back Pain"],
   {}, "sandbag"),
ex("sandbag_shoulder_001", "Sandbag Shouldering", "Full Body", "Explosive Pull", 3, "Intermediate", "Sandbag", 28,
   ["Glutes", "Erector Spinae"], ["Traps", "Core"], ["Forearms"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"],
   {}, "sandbag"),
]

# ---- Yoke (29) ----
NEW += [
ex("yoke_carry_001", "Yoke Carry", "Carry", "Carry", 4, "Advanced", "Yoke", 29,
   ["Erector Spinae", "Traps"], ["Glutes", "Quadriceps"], ["Core"],
   ["Lower Back", "Knee", "Ankle"], ["Low Back Pain"],
   {"squat_ratio": 0.4}, "loaded_carry"),
]

# ---- Agility Ladder (30) ----
NEW += [
ex("agility_ladder_001", "Agility Ladder In-In-Out", "Full Body", "Sprint", 2, "Novice", "Agility Ladder", 30,
   ["Calves", "Quadriceps"], ["Hip Flexors"], ["Core", "Ankle Stabilizers"],
   ["Ankle", "Knee"], ["ATFL Sprain - Grade III Sprain (Complete Rupture)"],
   {}, "agility"),
]

# ---- Boxing Heavy Bag (31) ----
NEW += [
ex("heavybag_combo_001", "Heavy Bag Combinations", "Sport Specific", "Strike", 2, "Novice", "Boxing Heavy Bag", 31,
   ["Anterior Deltoid", "Obliques"], ["Triceps Brachii", "Core"], ["Rotator Cuff"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"],
   {}, "striking_bag"),
ex("heavybag_power_001", "Heavy Bag Power Rounds", "Conditioning", "Strike", 3, "Intermediate", "Boxing Heavy Bag", 31,
   ["Obliques", "Anterior Deltoid"], ["Glutes", "Core"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability", "Low Back Pain"],
   {}, "striking_bag"),
ex("heavybag_knees_001", "Heavy Bag Knee Strikes", "Sport Specific", "Strike", 2, "Novice", "Boxing Heavy Bag", 31,
   ["Hip Flexors"], ["Glutes", "Core"], ["Ankle Stabilizers"],
   ["Hip", "Knee"], [],
   {}, "striking_bag"),
]

# ---- Jump Rope (32) ----
NEW += [
ex("jumprope_basic_001", "Jump Rope Basic Bounce", "Conditioning", "Jump", 1, "Beginner", "Jump Rope", 32,
   ["Calves"], ["Quadriceps"], ["Ankle Stabilizers"],
   ["Ankle", "Knee"], ["Achilles Tendon - Complete Rupture", "Stress Fracture - Tibia"],
   {}, "jump_rope"),
ex("jumprope_doubleunder_001", "Double Under Intervals", "Conditioning", "Jump", 3, "Intermediate", "Jump Rope", 32,
   ["Calves"], ["Quadriceps", "Forearms"], ["Ankle Stabilizers"],
   ["Ankle", "Knee"], ["Achilles Tendon - Complete Rupture", "Stress Fracture - Tibia"],
   {}, "jump_rope"),
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
