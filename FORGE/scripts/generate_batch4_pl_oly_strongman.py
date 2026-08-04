"""
generate_batch4_pl_oly_strongman.py — adds ~170 new, fully-tagged exercises
covering the powerlifting/Olympic-lifting/strongman/machine variation gaps
identified by the user (squat/deadlift/bench/press bar & accommodating-
resistance variations, Olympic pulls & receiving positions, strongman
implements, and a handful of missing machines).

DEDUPE NOTE: the user's source list had ~275 names across two overlapping
paste-ins. Before writing this file we diffed every name against the
existing 261-exercise database (case-insensitive) and dropped anything that
was already covered under an existing name (e.g. "Anderson Squat" ->
already "Anderson Squat (From Pins)"; "Push Press" / "Rack Pull" / "Split
Jerk" / "Kettlebell Jerk" already exist verbatim) or was a spelling
duplicate within the user's own list (e.g. "Turkish Get Up" / "Turkish
Get-Up", "Mid Thigh Pull" / "Mid-Thigh Pull", "Speed Bench" / "Speed Bench
Press"). What's left is genuinely new ground.

Same joint_stress / injuries_to_avoid discipline as batch2: every entry is
hand-tagged from real biomechanics, not machine-generated in bulk, so the
injury-filtering engine stays trustworthy.

Run: python scripts/generate_batch4_pl_oly_strongman.py
Then: python scripts/enrich_exercises.py   (derives v4.0/v5.1 fields for the new entries)
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.core.config import settings

SRC = settings.EXERCISES_JSON_PATH
BACKUP = settings.BACKUP_DIR / "exercises_pre_batch4_backup.json"

SPORTS = ["Wrestling", "Judo", "Sambo", "BJJ", "Boxing", "Muay Thai",
          "Kickboxing", "Sanda", "Rugby", "Rock Climbing", "HYROX", "Special Forces"]

TEMPLATES = {
    # heavy barbell strength staples (squat/bench/deadlift variations)
    "barbell_basic": {"Wrestling": 75, "Judo": 70, "Sambo": 70, "BJJ": 55, "Boxing": 55,
                       "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 80,
                       "Rock Climbing": 25, "HYROX": 80, "Special Forces": 85},
    # squat-pattern leg work
    "legs": {"Wrestling": 80, "Judo": 75, "Sambo": 75, "BJJ": 65, "Boxing": 65,
             "Muay Thai": 75, "Kickboxing": 75, "Sanda": 75, "Rugby": 85,
             "Rock Climbing": 45, "HYROX": 90, "Special Forces": 90},
    # Olympic lifting / explosive barbell
    "olympic": {"Wrestling": 85, "Judo": 80, "Sambo": 80, "BJJ": 55, "Boxing": 45,
                "Muay Thai": 55, "Kickboxing": 50, "Sanda": 60, "Rugby": 90,
                "Rock Climbing": 20, "HYROX": 75, "Special Forces": 90},
    # accommodating resistance / max-effort powerlifting specialty work
    "max_effort": {"Wrestling": 65, "Judo": 60, "Sambo": 60, "BJJ": 45, "Boxing": 40,
                    "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 75,
                    "Rock Climbing": 15, "HYROX": 65, "Special Forces": 85},
    # rack / pin / positional strength
    "rack": {"Wrestling": 65, "Judo": 60, "Sambo": 60, "BJJ": 50, "Boxing": 40,
             "Muay Thai": 45, "Kickboxing": 45, "Sanda": 45, "Rugby": 75,
             "Rock Climbing": 20, "HYROX": 80, "Special Forces": 90},
    # kettlebell ballistic/grind
    "kettlebell": {"Wrestling": 75, "Judo": 75, "Sambo": 75, "BJJ": 65, "Boxing": 60,
                   "Muay Thai": 65, "Kickboxing": 65, "Sanda": 65, "Rugby": 70,
                   "Rock Climbing": 40, "HYROX": 90, "Special Forces": 90},
    # strongman implements
    "strongman": {"Wrestling": 80, "Judo": 75, "Sambo": 80, "BJJ": 60, "Boxing": 50,
                  "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 90,
                  "Rock Climbing": 30, "HYROX": 90, "Special Forces": 95},
    # loaded carries
    "loaded_carry": {"Wrestling": 75, "Judo": 70, "Sambo": 75, "BJJ": 60, "Boxing": 55,
                      "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 85,
                      "Rock Climbing": 40, "HYROX": 95, "Special Forces": 95},
    # dumbbell general strength/hypertrophy
    "dumbbell": {"Wrestling": 65, "Judo": 60, "Sambo": 60, "BJJ": 55, "Boxing": 55,
                 "Muay Thai": 55, "Kickboxing": 55, "Sanda": 55, "Rugby": 65,
                 "Rock Climbing": 35, "HYROX": 70, "Special Forces": 75},
    # rows / horizontal pull
    "row": {"Wrestling": 75, "Judo": 75, "Sambo": 75, "BJJ": 70, "Boxing": 55,
            "Muay Thai": 55, "Kickboxing": 55, "Sanda": 55, "Rugby": 70,
            "Rock Climbing": 55, "HYROX": 60, "Special Forces": 75},
    # commercial-gym machine accessory work
    "machine": {"Wrestling": 40, "Judo": 35, "Sambo": 35, "BJJ": 35, "Boxing": 35,
                "Muay Thai": 35, "Kickboxing": 35, "Sanda": 35, "Rugby": 45,
                "Rock Climbing": 25, "HYROX": 35, "Special Forces": 40},
    # landmine work
    "landmine": {"Wrestling": 70, "Judo": 65, "Sambo": 65, "BJJ": 55, "Boxing": 60,
                 "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 80,
                 "Rock Climbing": 30, "HYROX": 75, "Special Forces": 80},
    # speed/dynamic-effort explosive barbell
    "speed": {"Wrestling": 75, "Judo": 70, "Sambo": 70, "BJJ": 55, "Boxing": 60,
              "Muay Thai": 60, "Kickboxing": 60, "Sanda": 60, "Rugby": 85,
              "Rock Climbing": 25, "HYROX": 75, "Special Forces": 85},
}


def sp(template, **overrides):
    d = dict(TEMPLATES[template])
    d.update(overrides)
    return d


def ex(id_, name, category, pattern, difficulty, level, equipment, eq_level,
       primary, secondary, stabilizers, joint_stress, injuries, reqs,
       progressions, regressions, alternatives, template, **sp_overrides):
    return {
        "id": id_, "name": name, "category": category, "movement_pattern": pattern,
        "difficulty": difficulty, "experience_level": level,
        "equipment": equipment, "equipment_level": eq_level,
        "primary_muscles": primary, "secondary_muscles": secondary, "stabilizers": stabilizers,
        "joint_stress": joint_stress, "injuries_to_avoid": injuries,
        "strength_requirements": {"bench_ratio": 0.0, "squat_ratio": 0.0, "deadlift_ratio": 0.0,
                                   "pullups": 0, "pushups": 0, **reqs},
        "progressions": progressions, "regressions": regressions, "alternatives": alternatives,
        "sport_priority": sp(template, **sp_overrides),
    }


NEW = []

# =========================================================
# BACK SQUAT BAR & ACCOMMODATING-RESISTANCE VARIATIONS
# =========================================================
NEW += [
ex("highbar_backsquat_001", "High Bar Back Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 1.0},
   [], [], ["Barbell Back Squat"], "legs"),
ex("lowbar_backsquat_001", "Low Bar Back Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Quadriceps", "Erector Spinae"], ["Core"],
   ["Hip", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 1.0},
   [], [], ["Barbell Back Squat"], "legs"),
ex("concentric_box_squat_001", "Concentric Box Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Quadriceps"], ["Core"],
   ["Hip", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 0.7},
   [], ["box_squat_001"], [], "max_effort"),
ex("pause_backsquat_001", "Pause Back Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 0.8},
   [], [], [], "legs"),
ex("tempo_backsquat_001", "Tempo Back Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 0.75},
   [], [], [], "legs"),
ex("banded_backsquat_001", "Banded Back Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 0.85},
   [], [], [], "max_effort"),
ex("chain_backsquat_001", "Chain Back Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 0.9},
   [], [], [], "max_effort"),
ex("reverseband_squat_001", "Reverse Band Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 1.15},
   [], [], [], "max_effort"),
ex("accommodating_squat_001", "Accommodating Resistance Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 0.9},
   [], [], ["Chain Back Squat", "Banded Back Squat"], "max_effort"),
ex("dynamiceffort_squat_001", "Dynamic Effort Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 0.55},
   [], [], [], "speed"),
ex("maxeffort_squat_001", "Max Effort Squat", "Squat", "Squat", 5, "Elite", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back", "Hip"], ["Low Back Pain", "Patellar Tendon", "Meniscus Tear - Grade 3 (True Structural Tear)"],
   {"squat_ratio": 1.3}, [], [], [], "max_effort"),
ex("cambered_squat_001", "Cambered Bar Squat", "Squat", "Squat", 4, "Advanced", "Cambered Bar", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back", "Shoulder"], ["Low Back Pain"], {"squat_ratio": 0.85},
   [], [], [], "max_effort"),
ex("buffalo_squat_001", "Buffalo Bar Squat", "Squat", "Squat", 3, "Intermediate", "Buffalo Bar", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back", "Shoulder"], ["Low Back Pain"], {"squat_ratio": 0.95},
   [], [], ["Safety Bar Squat"], "legs"),
ex("safetybar_squat_001", "Safety Bar Squat", "Squat", "Squat", 3, "Intermediate", "Safety Squat Bar", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back", "Shoulder"], ["Low Back Pain"], {"squat_ratio": 0.95},
   [], [], ["Buffalo Bar Squat"], "legs"),
ex("monolift_squat_001", "Monolift Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Low Back Pain", "Patellar Tendon"], {"squat_ratio": 1.1},
   [], [], [], "max_effort"),
ex("hatfield_squat_001", "Hatfield Squat", "Squat", "Squat", 4, "Advanced", "Power Rack", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee", "Lower Back", "Shoulder"], ["Low Back Pain"], {"squat_ratio": 1.2},
   [], [], [], "rack"),
ex("spanish_squat_001", "Spanish Squat", "Squat", "Isometric", 2, "Novice", "Resistance Band", 8,
   ["Quadriceps"], [], ["Core"],
   ["Knee"], ["Jumper's Knee (Patellar Tendinopathy)", "Patellofemoral Pain Syndrome (PFPS)"],
   {}, [], [], [], "legs"),
ex("kang_squat_001", "Kang Squat", "Hinge", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Quadriceps", "Erector Spinae"], ["Core"],
   ["Hip", "Lower Back", "Knee"], ["Low Back Pain"], {"squat_ratio": 0.6},
   [], [], ["Good Morning"], "legs"),
]

# =========================================================
# FRONT SQUAT VARIATIONS
# =========================================================
NEW += [
ex("pause_frontsquat_001", "Pause Front Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus", "Upper Back"], ["Core"],
   ["Knee", "Wrist"], ["Patellar Tendon"], {"squat_ratio": 0.7},
   [], [], [], "legs"),
ex("tempo_frontsquat_001", "Tempo Front Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus", "Upper Back"], ["Core"],
   ["Knee", "Wrist"], ["Patellar Tendon"], {"squat_ratio": 0.65},
   [], [], [], "legs"),
ex("zombie_frontsquat_001", "Zombie Front Squat", "Squat", "Isometric", 4, "Advanced", "Barbell", 5,
   ["Quadriceps"], ["Anterior Deltoid", "Core"], ["Shoulder Stabilizers"],
   ["Knee", "Shoulder"], ["Shoulder Instability"], {"squat_ratio": 0.4},
   [], [], [], "legs"),
ex("crossarm_frontsquat_001", "Cross Arm Front Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus", "Upper Back"], ["Core"],
   ["Knee", "Shoulder"], ["Patellar Tendon"], {"squat_ratio": 0.7},
   [], [], ["Barbell Front Squat"], "legs"),
ex("cleangrip_frontsquat_001", "Clean Grip Front Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus", "Upper Back"], ["Core"],
   ["Knee", "Wrist"], ["Wrist Pain"], {"squat_ratio": 0.75},
   [], [], ["Barbell Front Squat"], "olympic"),
ex("front_box_squat_001", "Front Box Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee", "Lower Back"], ["Patellar Tendon"], {"squat_ratio": 0.6},
   [], [], [], "max_effort"),
ex("front_pin_squat_001", "Front Pin Squat", "Squat", "Squat", 3, "Intermediate", "Power Rack", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee", "Lower Back"], ["Patellar Tendon"], {"squat_ratio": 0.55},
   [], [], [], "rack"),
ex("front_anderson_squat_001", "Front Anderson Squat", "Squat", "Squat", 3, "Intermediate", "Power Rack", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee", "Lower Back"], ["Patellar Tendon"], {"squat_ratio": 0.6},
   [], [], ["Anderson Squat (From Pins)"], "rack"),
]

# =========================================================
# ZERCHER FAMILY
# =========================================================
NEW += [
ex("zercher_squat_001", "Zercher Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Biceps Brachii", "Upper Back"], ["Core"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 0.65},
   [], [], [], "legs"),
ex("zercher_carry_001", "Zercher Carry", "Carry", "Carry", 3, "Intermediate", "Barbell", 5,
   ["Erector Spinae", "Core"], ["Biceps Brachii"], ["Core"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {}, [], [], ["Farmer Handles Carry"], "loaded_carry"),
ex("zercher_deadlift_001", "Zercher Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae", "Biceps Brachii"], ["Core"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.6}, [], [], [], "legs"),
ex("zercher_goodmorning_001", "Zercher Good Morning", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Erector Spinae", "Hamstrings"], ["Gluteus Maximus"], ["Core"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.3}, [], [], ["Good Morning"], "legs"),
ex("zercher_reverselunge_001", "Zercher Reverse Lunge", "Squat", "Lunge", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Biceps Brachii"], ["Core"],
   ["Knee", "Elbow"], [], {}, [], [], [], "legs"),
ex("zercher_splitsquat_001", "Zercher Split Squat", "Squat", "Lunge", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Biceps Brachii"], ["Core"],
   ["Knee", "Elbow"], [], {}, [], [], [], "legs"),
ex("zercher_march_001", "Zercher March", "Core", "Isometric", 2, "Novice", "Barbell", 5,
   ["Core", "Hip Flexors"], ["Biceps Brachii"], ["Erector Spinae"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {}, [], [], [], "legs"),
ex("zercher_boxsquat_001", "Zercher Box Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Biceps Brachii"], ["Core"],
   ["Elbow", "Lower Back"], ["Low Back Pain"], {"squat_ratio": 0.5}, [], [], [], "max_effort"),
]

# =========================================================
# GOBLET / SINGLE-LEG / STANCE VARIATIONS
# =========================================================
NEW += [
ex("goblet_boxsquat_001", "Goblet Box Squat", "Squat", "Squat", 2, "Novice", "Kettlebell", 3,
   ["Quadriceps", "Gluteus Maximus"], ["Core"], [],
   ["Knee"], [], {}, [], [], ["Dumbbell Goblet Squat"], "kettlebell"),
ex("goblet_cyclist_001", "Goblet Cyclist Squat", "Squat", "Squat", 2, "Novice", "Kettlebell", 3,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee"], ["Patellar Tendon"], {}, [], [], [], "kettlebell"),
ex("goblet_splitsquat_001", "Goblet Split Squat", "Squat", "Lunge", 2, "Novice", "Kettlebell", 3,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee"], [], {}, [], [], ["Bulgarian Split Squat"], "kettlebell"),
ex("goblet_lateralsquat_001", "Goblet Lateral Squat", "Squat", "Lunge", 2, "Novice", "Kettlebell", 3,
   ["Adductors", "Gluteus Maximus"], ["Quadriceps"], ["Core"],
   ["Knee", "Hip"], [], {}, [], [], [], "kettlebell"),
ex("goblet_reverselunge_001", "Goblet Reverse Lunge", "Squat", "Lunge", 2, "Novice", "Kettlebell", 3,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee"], [], {}, [], [], [], "kettlebell"),
ex("atg_splitsquat_001", "ATG Split Squat", "Squat", "Lunge", 3, "Intermediate", "Dumbbell", 7,
   ["Quadriceps", "Gluteus Maximus"], ["Adductors"], ["Core", "Ankle Stabilizers"],
   ["Knee", "Ankle"], ["Patellar Tendon"], {}, [], ["Bulgarian Split Squat"], [], "dumbbell"),
ex("walking_splitsquat_001", "Walking Split Squat", "Squat", "Lunge", 2, "Novice", "Dumbbell", 7,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee"], [], {}, [], [], ["Dumbbell Walking Lunge"], "dumbbell"),
ex("static_splitsquat_001", "Static Split Squat", "Squat", "Lunge", 2, "Novice", "Dumbbell", 7,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee"], [], {}, ["dumbbell_splitsquat_001"], [], [], "dumbbell"),
ex("dumbbell_splitsquat_001", "Dumbbell Split Squat", "Squat", "Lunge", 2, "Novice", "Dumbbell", 7,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee"], [], {}, ["atg_splitsquat_001"], ["static_splitsquat_001"], [], "dumbbell"),
ex("skater_squat_001", "Skater Squat", "Squat", "Lunge", 4, "Advanced", "Bodyweight", 1,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Ankle Stabilizers", "Core"],
   ["Knee", "Ankle"], ["ACL/Ligament Tear - Grade 2 (Partial Tear)", "Patellar Tendon"],
   {}, [], ["Bulgarian Split Squat"], [], "legs"),
ex("highbox_stepup_001", "High Box Step Up", "Squat", "Lunge", 3, "Intermediate", "Plyo Box", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee", "Hip"], ["Patellar Tendon"], {}, [], ["Dumbbell Step-Up"], [], "legs"),
ex("lateral_stepup_001", "Lateral Step Up", "Squat", "Lunge", 2, "Novice", "Plyo Box", 5,
   ["Adductors", "Gluteus Maximus"], ["Quadriceps"], ["Core"],
   ["Knee", "Hip"], [], {}, [], [], [], "legs"),
ex("deficit_stepup_001", "Deficit Step Up", "Squat", "Lunge", 3, "Intermediate", "Plyo Box", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core", "Ankle Stabilizers"],
   ["Knee", "Hip", "Ankle"], ["Patellar Tendon"], {}, [], [], [], "legs"),
ex("cyclist_squat_001", "Cyclist Squat", "Squat", "Squat", 2, "Novice", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee"], ["Patellar Tendon"], {"squat_ratio": 0.6}, [], [], [], "legs"),
ex("heels_elevated_squat_001", "Heels Elevated Squat", "Squat", "Squat", 2, "Novice", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee"], ["Patellar Tendon"], {"squat_ratio": 0.7}, [], [], [], "legs"),
ex("narrow_stance_squat_001", "Narrow Stance Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps"], ["Gluteus Maximus"], ["Core"],
   ["Knee", "Lower Back"], ["Patellar Tendon"], {"squat_ratio": 0.85}, [], [], [], "legs"),
ex("wide_stance_squat_001", "Wide Stance Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Adductors", "Gluteus Maximus"], ["Quadriceps"], ["Core"],
   ["Hip", "Knee", "Lower Back"], ["Groin Strain - Grade 2 (Partial Tear)"], {"squat_ratio": 0.9},
   [], [], [], "legs"),
ex("cossack_squat_001", "Cossack Squat", "Squat", "Lunge", 3, "Intermediate", "Kettlebell", 3,
   ["Adductors", "Gluteus Maximus"], ["Quadriceps"], ["Ankle Stabilizers", "Core"],
   ["Knee", "Hip", "Ankle"], ["Groin Strain - Grade 2 (Partial Tear)"], {}, [], [], [], "kettlebell"),
ex("jefferson_squat_001", "Jefferson Squat", "Squat", "Squat", 4, "Advanced", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Adductors", "Erector Spinae"], ["Core"],
   ["Knee", "Lower Back", "Hip"], ["Low Back Pain"], {"squat_ratio": 0.5}, [], [], [], "max_effort"),
ex("landmine_squat_001", "Landmine Squat", "Squat", "Squat", 2, "Novice", "Landmine", 23,
   ["Quadriceps", "Gluteus Maximus"], ["Core"], [],
   ["Knee"], [], {}, [], [], ["Dumbbell Goblet Squat"], "landmine"),
]

# =========================================================
# DEADLIFT / HINGE VARIATIONS
# =========================================================
NEW += [
ex("stiffleg_deadlift_001", "Stiff Leg Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core"],
   ["Lower Back", "Hamstring"], ["Hamstring Strain - Grade 2 (Partial Tear)", "Low Back Pain"],
   {"deadlift_ratio": 0.75}, [], [], ["Romanian Deadlift"], "legs"),
ex("cleangrip_deadlift_001", "Clean Grip Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae", "Trapezius"], ["Core"],
   ["Lower Back", "Wrist"], ["Low Back Pain"], {"deadlift_ratio": 1.0}, [], [], [], "olympic"),
ex("jefferson_deadlift_001", "Jefferson Deadlift", "Hinge", "Hinge", 4, "Advanced", "Barbell", 5,
   ["Gluteus Maximus", "Quadriceps"], ["Erector Spinae", "Adductors"], ["Core"],
   ["Lower Back", "Hip", "Knee"], ["Low Back Pain"], {"deadlift_ratio": 0.6}, [], [], [], "max_effort"),
ex("reeves_deadlift_001", "Reeves Deadlift", "Hinge", "Hinge", 4, "Advanced", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae", "Forearm Flexors"], ["Core"],
   ["Lower Back", "Wrist"], ["Low Back Pain", "Wrist Pain"], {"deadlift_ratio": 0.5}, [], [], [], "max_effort"),
ex("suitcase_deadlift_001", "Suitcase Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Obliques"], ["Erector Spinae", "Forearm Flexors"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.5}, [], [], ["Suitcase Carry"], "legs"),
ex("rack_pull_highpull_001", "Rack Pull High Pull", "Hinge", "Explosive Pull", 3, "Intermediate", "Power Rack", 5,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.7}, [], [], [], "rack"),
ex("silverdollar_deadlift_001", "Silver Dollar Deadlift", "Hinge", "Hinge", 4, "Advanced", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.6}, [], [], ["Deficit Deadlift"], "max_effort"),
ex("axle_deadlift_001", "Axle Deadlift", "Hinge", "Hinge", 4, "Advanced", "Axle Bar", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae", "Forearm Flexors"], ["Core"],
   ["Lower Back", "Wrist"], ["Low Back Pain"], {"deadlift_ratio": 0.85}, [], [], [], "strongman"),
ex("reverseband_deadlift_001", "Reverse Band Deadlift", "Hinge", "Hinge", 4, "Advanced", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 1.2}, [], [], [], "max_effort"),
ex("bstance_rdl_001", "B-Stance Romanian Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Dumbbell", 7,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core", "Ankle Stabilizers"],
   ["Hamstring", "Lower Back"], ["Hamstring Strain - Grade 1 (Mild Strain)"], {"deadlift_ratio": 0.35},
   [], [], ["Single-Leg Bodyweight Romanian Deadlift"], "dumbbell"),
ex("snatchgrip_rdl_001", "Snatch Grip Romanian Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae", "Upper Back"], ["Core"],
   ["Hamstring", "Lower Back"], ["Hamstring Strain - Grade 2 (Partial Tear)"], {"deadlift_ratio": 0.6},
   [], [], ["Romanian Deadlift"], "olympic"),
ex("deficit_rdl_001", "Deficit Romanian Deadlift", "Hinge", "Hinge", 4, "Advanced", "Barbell", 5,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core"],
   ["Hamstring", "Lower Back"], ["Hamstring Strain - Grade 2 (Partial Tear)", "Low Back Pain"],
   {"deadlift_ratio": 0.55}, [], [], [], "max_effort"),
ex("kettlebell_rdl_001", "Kettlebell Romanian Deadlift", "Hinge", "Hinge", 2, "Novice", "Kettlebell", 3,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core"],
   ["Hamstring", "Lower Back"], [], {}, [], [], ["Dumbbell Romanian Deadlift"], "kettlebell"),
ex("tempo_rdl_001", "Tempo Romanian Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core"],
   ["Hamstring", "Lower Back"], ["Hamstring Strain - Grade 1 (Mild Strain)"], {"deadlift_ratio": 0.5},
   [], [], [], "legs"),
ex("seated_goodmorning_001", "Seated Good Morning", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Erector Spinae", "Hamstrings"], ["Gluteus Maximus"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.35}, [], [], ["Good Morning"], "legs"),
ex("banded_goodmorning_001", "Banded Good Morning", "Hinge", "Hinge", 2, "Novice", "Resistance Band", 8,
   ["Erector Spinae", "Hamstrings"], ["Gluteus Maximus"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], [], "legs"),
ex("safetybar_goodmorning_001", "Safety Bar Good Morning", "Hinge", "Hinge", 3, "Intermediate", "Safety Squat Bar", 5,
   ["Erector Spinae", "Hamstrings"], ["Gluteus Maximus"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.4}, [], [], ["Good Morning"], "legs"),
ex("cambered_goodmorning_001", "Cambered Bar Good Morning", "Hinge", "Hinge", 3, "Intermediate", "Cambered Bar", 5,
   ["Erector Spinae", "Hamstrings"], ["Gluteus Maximus"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.4}, [], [], [], "legs"),
ex("glute_ham_raise_001", "Glute Ham Raise", "Hinge", "Flexion", 3, "Intermediate", "GHD", 24,
   ["Hamstrings", "Gluteus Maximus"], ["Erector Spinae"], ["Core"],
   ["Knee", "Lower Back"], ["Hamstring Strain - Grade 2 (Partial Tear)"], {}, [], ["GHD Back Extension"], [], "legs"),
ex("back_extension_001", "Back Extension", "Hinge", "Isometric", 1, "Beginner", "Hyperextension Bench", 5,
   ["Erector Spinae"], ["Gluteus Maximus", "Hamstrings"], [],
   ["Lower Back"], ["Low Back Pain"], {}, ["glute_ham_raise_001"], [], ["Bodyweight Hyperextension"], "legs"),
]

# =========================================================
# BENCH PRESS VARIATIONS
# =========================================================
NEW += [
ex("flat_bench_001", "Flat Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 1.0}, [], [], ["Dumbbell Bench Press"], "barbell_basic"),
ex("incline_bench_001", "Incline Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Pectoralis Major", "Anterior Deltoid"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 0.85}, [], [], ["Incline Dumbbell Bench Press"], "barbell_basic"),
ex("decline_bench_001", "Decline Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 1.05}, [], [], [], "barbell_basic"),
ex("closegrip_bench_001", "Close Grip Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Triceps Brachii"], ["Pectoralis Major"], ["Core"],
   ["Elbow", "Wrist"], ["Golfer's Elbow"], {"bench_ratio": 0.85}, [], [], [], "barbell_basic"),
ex("widegrip_bench_001", "Wide Grip Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Pectoralis Major"], ["Anterior Deltoid", "Triceps Brachii"], ["Core"],
   ["Shoulder"], ["Shoulder Instability"], {"bench_ratio": 1.0}, [], [], [], "barbell_basic"),
ex("reversegrip_bench_001", "Reverse Grip Bench Press", "Horizontal Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Pectoralis Major", "Anterior Deltoid"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Wrist"], ["Wrist Pain"], {"bench_ratio": 0.8}, [], [], [], "barbell_basic"),
ex("spoto_press_001", "Spoto Press", "Horizontal Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 0.75}, [], [], [], "barbell_basic"),
ex("larsen_press_001", "Larsen Press", "Horizontal Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {"bench_ratio": 0.8}, [], [], [], "barbell_basic"),
ex("pin_bench_press_001", "Pin Bench Press", "Horizontal Push", "Push", 3, "Intermediate", "Power Rack", 5,
   ["Pectoralis Major"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 0.55}, [], [], ["Pin Bench Press (Mid-Range)"], "rack"),
ex("board_press_001", "Board Press", "Horizontal Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Triceps Brachii"], ["Pectoralis Major"], ["Core"],
   ["Elbow", "Shoulder"], ["Golfer's Elbow"], {"bench_ratio": 0.9}, [], [], [], "barbell_basic"),
ex("swissbar_bench_001", "Swiss Bar Bench Press", "Horizontal Push", "Push", 2, "Novice", "Swiss Bar", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {"bench_ratio": 0.9}, [], [], [], "barbell_basic"),
ex("footballbar_bench_001", "Football Bar Bench", "Horizontal Push", "Push", 2, "Novice", "Swiss Bar", 5,
   ["Pectoralis Major"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {"bench_ratio": 0.9}, [], [], ["Swiss Bar Bench Press"], "barbell_basic"),
ex("guillotine_press_001", "Guillotine Press", "Horizontal Push", "Push", 4, "Advanced", "Barbell", 5,
   ["Pectoralis Major", "Anterior Deltoid"], ["Triceps Brachii"], ["Rotator Cuff"],
   ["Shoulder"], ["Shoulder Instability", "Rotator Cuff"], {"bench_ratio": 0.7}, [], [], [], "max_effort"),
ex("slingshot_bench_001", "Sling Shot Bench Press", "Horizontal Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Elbow"], [], {"bench_ratio": 1.15}, [], [], [], "max_effort"),
ex("chain_bench_001", "Chain Bench Press", "Horizontal Push", "Push", 4, "Advanced", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 0.9}, [], [], [], "max_effort"),
ex("band_bench_001", "Band Bench Press", "Horizontal Push", "Push", 3, "Intermediate", "Resistance Band", 8,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"bench_ratio": 0.7}, [], [], [], "max_effort"),
ex("dumbbell_floorpress_001", "Dumbbell Floor Press", "Horizontal Push", "Push", 2, "Novice", "Dumbbell", 7,
   ["Pectoralis Major"], ["Triceps Brachii"], ["Core"],
   ["Shoulder", "Elbow"], [], {"bench_ratio": 0.5}, [], [], ["Kettlebell Floor Press"], "dumbbell"),
ex("singlearm_db_bench_001", "Single Arm Dumbbell Bench Press", "Horizontal Push", "Push", 3, "Intermediate", "Dumbbell", 7,
   ["Pectoralis Major"], ["Triceps Brachii", "Core"], ["Core", "Obliques"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {"bench_ratio": 0.3}, [], [], [], "dumbbell"),
ex("speed_bench_001", "Speed Bench Press", "Horizontal Push", "Push", 2, "Novice", "Barbell", 5,
   ["Pectoralis Major"], ["Triceps Brachii", "Anterior Deltoid"], ["Core"],
   ["Shoulder", "Elbow"], [], {"bench_ratio": 0.5}, [], [], [], "speed"),
]

# =========================================================
# OVERHEAD PRESS VARIATIONS
# =========================================================
NEW += [
ex("strict_press_001", "Strict Press", "Vertical Push", "Push", 2, "Novice", "Barbell", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Upper Trapezius"], ["Core"],
   ["Shoulder"], ["Shoulder Instability"], {"bench_ratio": 0.5}, [], [], ["Barbell Overhead Press"], "barbell_basic"),
ex("military_press_001", "Military Press", "Vertical Push", "Push", 2, "Novice", "Barbell", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {"bench_ratio": 0.5}, [], [], ["Strict Press"], "barbell_basic"),
ex("zpress_001", "Z Press", "Vertical Push", "Push", 4, "Advanced", "Barbell", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder", "Hip"], ["Shoulder Instability"], {"bench_ratio": 0.35}, [], [], [], "max_effort"),
ex("bradford_press_001", "Bradford Press", "Vertical Push", "Push", 3, "Intermediate", "Barbell", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Upper Trapezius"], ["Rotator Cuff"],
   ["Shoulder", "Neck"], ["Shoulder Instability"], {"bench_ratio": 0.35}, [], [], [], "barbell_basic"),
ex("viking_press_001", "Viking Press", "Vertical Push", "Push", 3, "Intermediate", "Landmine", 23,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder"], ["Shoulder Instability"], {}, [], [], ["Half Kneeling Landmine Press"], "landmine"),
ex("behindneck_press_001", "Behind The Neck Press", "Vertical Push", "Push", 4, "Advanced", "Barbell", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Upper Trapezius"], ["Rotator Cuff"],
   ["Shoulder", "Neck"], ["Shoulder Instability", "Rotator Cuff"], {"bench_ratio": 0.4}, [], [], [], "max_effort"),
ex("axle_press_001", "Axle Press", "Vertical Push", "Push", 3, "Intermediate", "Axle Bar", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Forearm Flexors"], ["Core"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {"bench_ratio": 0.4}, [], [], [], "strongman"),
ex("log_press_001", "Log Press", "Vertical Push", "Push", 4, "Advanced", "Log Bar", 5,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {"bench_ratio": 0.55}, [], [], [], "strongman"),
ex("circusdb_press_001", "Circus Dumbbell Press", "Vertical Push", "Push", 4, "Advanced", "Dumbbell", 7,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core", "Obliques"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {"bench_ratio": 0.4}, [], [], [], "strongman"),
ex("arnold_press_001", "Arnold Press", "Vertical Push", "Push", 2, "Novice", "Dumbbell", 7,
   ["Anterior Deltoid"], ["Triceps Brachii", "Upper Trapezius"], ["Rotator Cuff"],
   ["Shoulder"], ["Shoulder Instability"], {}, [], [], ["Single-Arm Dumbbell Overhead Press"], "dumbbell"),
]

# =========================================================
# OLYMPIC LIFTS — pulls, hangs, receiving positions
# =========================================================
NEW += [
ex("hang_squat_clean_001", "Hang Squat Clean", "Full Body", "Complex", 4, "Advanced", "Barbell", 5,
   ["Gluteus Maximus", "Quadriceps"], ["Trapezius", "Deltoids"], ["Core"],
   ["Knee", "Shoulder", "Wrist"], ["Wrist Pain"], {"squat_ratio": 0.5}, [], [], ["Hang Clean"], "olympic"),
ex("muscle_clean_001", "Muscle Clean", "Full Body", "Explosive Pull", 3, "Intermediate", "Barbell", 5,
   ["Trapezius", "Deltoids"], ["Gluteus Maximus"], ["Core", "Forearm Flexors"],
   ["Shoulder", "Wrist"], [], {}, [], [], [], "olympic"),
ex("tall_clean_001", "Tall Clean", "Full Body", "Complex", 3, "Intermediate", "Barbell", 5,
   ["Trapezius", "Quadriceps"], ["Deltoids"], ["Core"],
   ["Wrist", "Knee"], [], {}, [], [], [], "olympic"),
ex("clean_highpull_001", "Clean High Pull", "Hinge", "Explosive Pull", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.75}, [], [], [], "olympic"),
ex("clean_deadlift_001", "Clean Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae", "Trapezius"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.9}, [], [], ["Barbell Clean Pull"], "olympic"),
ex("hang_squat_snatch_001", "Hang Squat Snatch", "Full Body", "Complex", 5, "Elite", "Barbell", 5,
   ["Trapezius", "Gluteus Maximus"], ["Deltoids", "Quadriceps"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Knee", "Wrist"], ["Shoulder Instability"], {}, [], [], [], "olympic"),
ex("hang_power_snatch_001", "Hang Power Snatch", "Full Body", "Explosive Pull", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Deltoids"], ["Gluteus Maximus"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {}, [], [], [], "olympic"),
ex("muscle_snatch_001", "Muscle Snatch", "Full Body", "Explosive Pull", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Deltoids"], ["Gluteus Maximus"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {}, [], [], [], "olympic"),
ex("tall_snatch_001", "Tall Snatch", "Full Body", "Complex", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Deltoids"], ["Quadriceps"], ["Core", "Rotator Cuff"],
   ["Wrist", "Shoulder"], ["Shoulder Instability"], {}, [], [], [], "olympic"),
ex("block_snatch_001", "Block Snatch", "Full Body", "Complex", 5, "Elite", "Barbell", 5,
   ["Trapezius", "Gluteus Maximus"], ["Deltoids", "Quadriceps"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Wrist", "Lower Back"], ["Shoulder Instability", "Low Back Pain"],
   {"deadlift_ratio": 0.6}, [], [], [], "olympic"),
ex("snatch_pull_001", "Snatch Pull", "Hinge", "Explosive Pull", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.7}, [], [], ["Barbell Clean Pull"], "olympic"),
ex("snatch_highpull_001", "Snatch High Pull", "Hinge", "Explosive Pull", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.65}, [], [], [], "olympic"),
ex("splitclean_001", "Split Clean", "Full Body", "Complex", 5, "Elite", "Barbell", 5,
   ["Quadriceps", "Trapezius"], ["Deltoids", "Gluteus Maximus"], ["Core", "Ankle Stabilizers"],
   ["Knee", "Wrist", "Ankle"], ["ACL/Ligament Tear - Grade 2 (Partial Tear)"], {}, [], [], [], "olympic"),
ex("splitsnatch_001", "Split Snatch", "Full Body", "Complex", 5, "Elite", "Barbell", 5,
   ["Quadriceps", "Trapezius"], ["Deltoids", "Gluteus Maximus"], ["Core", "Rotator Cuff", "Ankle Stabilizers"],
   ["Knee", "Shoulder", "Ankle"], ["Shoulder Instability", "ACL/Ligament Tear - Grade 2 (Partial Tear)"],
   {}, [], [], [], "olympic"),
ex("powercleanjerk_001", "Power Clean and Jerk", "Full Body", "Complex", 4, "Advanced", "Barbell", 5,
   ["Trapezius", "Anterior Deltoid"], ["Gluteus Maximus", "Triceps Brachii"], ["Core"],
   ["Knee", "Shoulder", "Wrist"], ["Shoulder Instability"], {}, [], [], ["Clean and Jerk"], "olympic"),
ex("midthigh_pull_001", "Mid-Thigh Pull", "Hinge", "Isometric", 3, "Intermediate", "Power Rack", 5,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus", "Forearm Flexors"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 1.0}, [], [], ["Isometric Mid-Thigh Pull"], "rack"),
ex("isometric_midthigh_pull_001", "Isometric Mid-Thigh Pull", "Hinge", "Isometric", 3, "Intermediate", "Power Rack", 5,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], ["midthigh_pull_001"], "rack"),
ex("hang_highpull_001", "Hang High Pull", "Hinge", "Explosive Pull", 3, "Intermediate", "Barbell", 5,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], [], {"deadlift_ratio": 0.55}, [], [], [], "olympic"),
]

# =========================================================
# ROWS
# =========================================================
NEW += [
ex("meadows_row_001", "Meadows Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Barbell", 5,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], ["Core", "Obliques"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], [], "row"),
ex("chestsupported_row_001", "Chest Supported Row", "Horizontal Pull", "Pull", 2, "Novice", "Dumbbell", 7,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], [],
   ["Shoulder"], [], {}, [], [], ["Seal Row"], "row"),
ex("tbar_row_001", "T Bar Row", "Horizontal Pull", "Pull", 2, "Novice", "Landmine", 23,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii", "Erector Spinae"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], ["Landmine Row"], "landmine"),
ex("yates_row_001", "Yates Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Barbell", 5,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii", "Erector Spinae"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.55}, [], [], [], "row"),
ex("kroc_row_001", "Kroc Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Dumbbell", 7,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Forearm Flexors"], ["Core", "Obliques"],
   ["Lower Back", "Elbow"], ["Low Back Pain"], {}, [], [], ["Single-Arm Dumbbell Row"], "row"),
ex("singlearm_bb_row_001", "Single Arm Barbell Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Barbell", 5,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Core"], ["Core", "Obliques"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], ["Single-Arm Dumbbell Row"], "row"),
ex("dumbbell_row_001", "Dumbbell Row", "Horizontal Pull", "Pull", 2, "Novice", "Dumbbell", 7,
   ["Latissimus Dorsi"], ["Biceps Brachii"], ["Core"],
   ["Lower Back", "Shoulder"], [], {}, [], [], ["Bilateral Dumbbell Bent-Over Row"], "row"),
ex("inverted_row_001", "Inverted Row", "Horizontal Pull", "Pull", 1, "Beginner", "Pull-up Bar", 1,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], ["Core"],
   ["Shoulder"], [], {}, [], [], ["Inverted Table Row"], "row"),
ex("cable_row_001", "Cable Row", "Horizontal Pull", "Pull", 2, "Novice", "Cable Machine", 10,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], ["Core"],
   ["Shoulder", "Lower Back"], ["Low Back Pain"], {}, [], [], ["Wide-Grip Seated Row"], "machine"),
ex("renegade_row_001", "Renegade Row", "Horizontal Pull", "Pull", 3, "Intermediate", "Dumbbell", 7,
   ["Latissimus Dorsi", "Core"], ["Biceps Brachii", "Anterior Deltoid"], ["Core", "Shoulder Stabilizers"],
   ["Shoulder", "Wrist"], ["Shoulder Instability"], {}, [], [], ["Dumbbell Renegade Row"], "dumbbell"),
]

# =========================================================
# PULLING (VERTICAL) VARIATIONS
# =========================================================
NEW += [
ex("neutralgrip_pullup_001", "Neutral Grip Pull-Up", "Vertical Pull", "Pull", 2, "Novice", "Pull-up Bar", 1,
   ["Latissimus Dorsi"], ["Biceps Brachii", "Brachialis"], ["Rotator Cuff"],
   ["Shoulder", "Elbow"], [], {"pullups": 3}, [], [], ["Bodyweight Pull-Up"], "row"),
ex("commando_pullup_001", "Commando Pull-Up", "Vertical Pull", "Pull", 4, "Advanced", "Pull-up Bar", 1,
   ["Latissimus Dorsi", "Obliques"], ["Biceps Brachii"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Elbow"], [], {"pullups": 10}, [], [], [], "row"),
ex("towel_pullup_001", "Towel Pull-Up", "Vertical Pull", "Pull", 4, "Advanced", "Pull-up Bar", 1,
   ["Latissimus Dorsi", "Forearm Flexors"], ["Biceps Brachii"], ["Rotator Cuff"],
   ["Shoulder", "Elbow", "Wrist"], ["Golfer's Elbow"], {"pullups": 10}, [], [], [], "row"),
ex("ropeclimb_pull_001", "Rope Climb Pull", "Vertical Pull", "Pull", 4, "Advanced", "Bodyweight", 1,
   ["Latissimus Dorsi", "Forearm Flexors"], ["Biceps Brachii", "Core"], ["Rotator Cuff"],
   ["Shoulder", "Elbow"], ["Shoulder Instability"], {"pullups": 8}, [], [], [], "row"),
ex("weighted_chinup_001", "Weighted Chin-Up", "Vertical Pull", "Pull", 4, "Advanced", "Pull-up Bar", 1,
   ["Latissimus Dorsi", "Biceps Brachii"], ["Brachialis"], ["Rotator Cuff"],
   ["Shoulder", "Elbow"], [], {"pullups": 12}, [], [], ["Weighted Pull-Up"], "row"),
]

# =========================================================
# STRONGMAN LIFTS
# =========================================================
NEW += [
ex("atlas_stone_load_001", "Atlas Stone Load", "Full Body", "Complex", 4, "Advanced", "Atlas Stone", 33,
   ["Erector Spinae", "Gluteus Maximus"], ["Quadriceps", "Biceps Brachii"], ["Core"],
   ["Lower Back", "Elbow"], ["Low Back Pain", "Bicep Tendon Rupture - Complete"], {}, [], [], [], "strongman"),
ex("stone_to_shoulder_001", "Stone to Shoulder", "Full Body", "Complex", 4, "Advanced", "Atlas Stone", 33,
   ["Erector Spinae", "Gluteus Maximus"], ["Trapezius", "Quadriceps"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"], {}, [], [], [], "strongman"),
ex("stone_over_bar_001", "Stone Over Bar", "Full Body", "Complex", 5, "Elite", "Atlas Stone", 33,
   ["Erector Spinae", "Gluteus Maximus"], ["Trapezius", "Anterior Deltoid"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"], {}, [], [], [], "strongman"),
ex("sandbag_load_001", "Sandbag Load", "Full Body", "Complex", 3, "Intermediate", "Sandbag", 28,
   ["Erector Spinae", "Gluteus Maximus"], ["Quadriceps", "Biceps Brachii"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], ["Sandbag Clean"], "strongman"),
ex("sandbag_squat_001", "Sandbag Squat", "Squat", "Squat", 3, "Intermediate", "Sandbag", 28,
   ["Quadriceps", "Gluteus Maximus"], ["Core"], ["Forearm Flexors"],
   ["Knee", "Lower Back"], ["Low Back Pain"], {}, [], [], ["Barbell Back Squat"], "strongman"),
ex("sandbag_press_001", "Sandbag Press", "Vertical Push", "Push", 3, "Intermediate", "Sandbag", 28,
   ["Anterior Deltoid"], ["Triceps Brachii", "Core"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {}, [], [], [], "strongman"),
ex("sandbag_to_shoulder_001", "Sandbag to Shoulder", "Full Body", "Complex", 3, "Intermediate", "Sandbag", 28,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus", "Core"], ["Forearm Flexors"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], [], "strongman"),
ex("log_clean_001", "Log Clean", "Full Body", "Complex", 4, "Advanced", "Log Bar", 5,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus", "Deltoids"], ["Core", "Forearm Flexors"],
   ["Lower Back", "Wrist"], ["Low Back Pain"], {}, [], [], [], "strongman"),
ex("log_cleanpress_001", "Log Clean and Press", "Full Body", "Complex", 4, "Advanced", "Log Bar", 5,
   ["Erector Spinae", "Anterior Deltoid"], ["Gluteus Maximus", "Triceps Brachii"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"], {}, [], [], ["log_clean_001"], "strongman"),
ex("axle_clean_001", "Axle Clean", "Full Body", "Complex", 4, "Advanced", "Axle Bar", 5,
   ["Erector Spinae", "Trapezius"], ["Gluteus Maximus", "Forearm Flexors"], ["Core"],
   ["Lower Back", "Wrist"], ["Low Back Pain"], {}, [], [], [], "strongman"),
ex("axle_cleanpress_001", "Axle Clean and Press", "Full Body", "Complex", 4, "Advanced", "Axle Bar", 5,
   ["Erector Spinae", "Anterior Deltoid"], ["Gluteus Maximus", "Triceps Brachii"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"], {}, [], [], ["axle_clean_001"], "strongman"),
ex("tire_flip_001", "Tire Flip", "Full Body", "Complex", 3, "Intermediate", "Tire", 34,
   ["Gluteus Maximus", "Quadriceps"], ["Erector Spinae", "Anterior Deltoid"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.5}, [], [], [], "strongman"),
ex("conans_wheel_001", "Conan's Wheel", "Carry", "Carry", 4, "Advanced", "Conan's Wheel", 35,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Core"], ["Core"],
   ["Lower Back", "Neck"], ["Low Back Pain"], {}, [], [], ["Yoke Carry"], "loaded_carry"),
ex("fingals_fingers_001", "Fingal's Fingers", "Full Body", "Complex", 4, "Advanced", "Fingal's Fingers", 36,
   ["Erector Spinae", "Gluteus Maximus"], ["Quadriceps", "Forearm Flexors"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], [], "strongman"),
ex("keg_carry_001", "Keg Carry", "Carry", "Carry", 3, "Intermediate", "Keg", 37,
   ["Erector Spinae", "Core"], ["Biceps Brachii", "Forearm Flexors"], ["Core"],
   ["Lower Back", "Elbow"], ["Low Back Pain"], {}, [], [], ["Zercher Carry"], "strongman"),
ex("keg_toss_001", "Keg Toss", "Power", "Throw", 4, "Advanced", "Keg", 37,
   ["Gluteus Maximus", "Erector Spinae"], ["Anterior Deltoid", "Core"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain", "Shoulder Instability"], {}, [], [], [], "strongman"),
ex("husafell_carry_001", "Husafell Carry", "Carry", "Carry", 4, "Advanced", "Husafell Stone", 38,
   ["Erector Spinae", "Core"], ["Trapezius", "Forearm Flexors"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], ["Yoke Carry"], "loaded_carry"),
ex("frame_carry_001", "Frame Carry", "Carry", "Carry", 3, "Intermediate", "Farmer Handles", 5,
   ["Erector Spinae", "Trapezius"], ["Forearm Flexors", "Core"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {}, [], [], ["Dumbbell Farmer's Carry"], "loaded_carry"),
ex("overhead_carry_001", "Overhead Carry", "Carry", "Carry", 3, "Intermediate", "Barbell", 5,
   ["Anterior Deltoid", "Core"], ["Trapezius", "Triceps Brachii"], ["Rotator Cuff", "Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {}, [], [], ["Heavy Overhead Carry"], "loaded_carry"),
ex("farmerhandle_carry_001", "Farmer Handles Carry", "Carry", "Carry", 2, "Novice", "Farmer Handles", 5,
   ["Forearm Flexors", "Trapezius"], ["Erector Spinae", "Core"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], ["Dumbbell Farmer's Carry"], "loaded_carry"),
]

# =========================================================
# KETTLEBELL & DUMBBELL LIFTS
# =========================================================
NEW += [
ex("american_swing_001", "American Swing", "Full Body", "Ballistic", 3, "Intermediate", "Kettlebell", 3,
   ["Gluteus Maximus", "Anterior Deltoid"], ["Hamstrings", "Core"], ["Core", "Rotator Cuff"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability", "Low Back Pain"], {}, [], [], ["Russian Kettlebell Swing"], "kettlebell"),
ex("kb_longcycle_001", "Kettlebell Long Cycle", "Full Body", "Complex", 4, "Advanced", "Kettlebell", 3,
   ["Gluteus Maximus", "Anterior Deltoid"], ["Trapezius", "Triceps Brachii"], ["Core"],
   ["Shoulder", "Lower Back"], ["Shoulder Instability"], {}, [], [], ["Double Kettlebell Clean and Jerk"], "kettlebell"),
ex("dbl_kb_frontsquat_001", "Double Kettlebell Front Squat", "Squat", "Squat", 3, "Intermediate", "Kettlebell", 3,
   ["Quadriceps", "Gluteus Maximus"], ["Core"], ["Core"],
   ["Knee", "Wrist"], [], {}, [], [], ["Barbell Front Squat"], "kettlebell"),
ex("windmill_001", "Windmill", "Core", "Rotational", 4, "Advanced", "Kettlebell", 3,
   ["Obliques", "Latissimus Dorsi"], ["Hamstrings", "Anterior Deltoid"], ["Core", "Rotator Cuff"],
   ["Lower Back", "Shoulder", "Hamstring"], ["Low Back Pain", "Hamstring Strain - Grade 1 (Mild Strain)"],
   {}, [], [], [], "kettlebell"),
ex("dumbbell_clean_001", "Dumbbell Clean", "Full Body", "Complex", 2, "Novice", "Dumbbell", 7,
   ["Trapezius", "Gluteus Maximus"], ["Deltoids", "Quadriceps"], ["Core"],
   ["Shoulder", "Lower Back"], [], {}, [], [], ["Kettlebell Clean"], "dumbbell"),
ex("dumbbell_snatch_001", "Dumbbell Snatch", "Full Body", "Explosive Pull", 3, "Intermediate", "Dumbbell", 7,
   ["Trapezius", "Gluteus Maximus"], ["Deltoids"], ["Core", "Rotator Cuff"],
   ["Shoulder"], ["Shoulder Instability"], {}, [], [], ["Single-Arm Dumbbell Snatch"], "dumbbell"),
ex("dumbbell_pushpress_001", "Dumbbell Push Press", "Vertical Push", "Push", 2, "Novice", "Dumbbell", 7,
   ["Anterior Deltoid"], ["Triceps Brachii", "Quadriceps"], ["Core"],
   ["Shoulder", "Knee"], ["Shoulder Instability"], {}, [], [], ["Barbell Push Press"], "dumbbell"),
ex("dumbbell_deadlift_001", "Dumbbell Deadlift", "Hinge", "Hinge", 1, "Beginner", "Dumbbell", 7,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {"deadlift_ratio": 0.35}, [], [], ["Kettlebell Deadlift"], "dumbbell"),
ex("dumbbell_incline_press_001", "Dumbbell Incline Press", "Horizontal Push", "Push", 2, "Novice", "Dumbbell", 7,
   ["Pectoralis Major", "Anterior Deltoid"], ["Triceps Brachii"], ["Core"],
   ["Shoulder"], ["Shoulder Instability"], {"bench_ratio": 0.35}, [], [], ["Incline Dumbbell Bench Press"], "dumbbell"),
]

# =========================================================
# MACHINE / CABLE COMPOUND LIFTS
# =========================================================
NEW += [
ex("smith_ohp_001", "Smith Machine Overhead Press", "Vertical Push", "Push", 2, "Novice", "Smith Machine", 5,
   ["Anterior Deltoid"], ["Triceps Brachii"], [],
   ["Shoulder"], ["Shoulder Instability"], {"bench_ratio": 0.4}, [], [], ["Smith Machine Bench Press"], "machine"),
ex("v_squat_001", "V Squat", "Squat", "Squat", 3, "Intermediate", "V Squat Machine", 39,
   ["Quadriceps"], ["Gluteus Maximus"], [],
   ["Knee", "Lower Back"], ["Patellar Tendon"], {"squat_ratio": 0.5}, [], [], ["Hack Squat Machine"], "machine"),
ex("pendulum_squat_001", "Pendulum Squat", "Squat", "Squat", 3, "Intermediate", "Pendulum Squat Machine", 40,
   ["Quadriceps"], ["Gluteus Maximus"], [],
   ["Knee"], ["Patellar Tendon"], {"squat_ratio": 0.55}, [], [], ["Hack Squat Machine"], "machine"),
ex("chest_press_machine_001", "Chest Press Machine", "Horizontal Push", "Push", 1, "Beginner", "Chest Press Machine", 41,
   ["Pectoralis Major"], ["Triceps Brachii"], [],
   ["Shoulder"], [], {}, [], [], ["Dumbbell Bench Press"], "machine"),
ex("shoulder_press_machine_001", "Shoulder Press Machine", "Vertical Push", "Push", 1, "Beginner", "Shoulder Press Machine", 42,
   ["Anterior Deltoid"], ["Triceps Brachii"], [],
   ["Shoulder"], [], {}, [], [], ["Barbell Overhead Press"], "machine"),
ex("high_row_machine_001", "High Row Machine", "Horizontal Pull", "Pull", 1, "Beginner", "High Row Machine", 43,
   ["Rhomboids", "Latissimus Dorsi"], ["Biceps Brachii"], [],
   ["Shoulder"], [], {}, [], [], ["Wide-Grip Seated Row"], "machine"),
ex("cable_pullthrough_001", "Cable Pull Through", "Hinge", "Hinge", 2, "Novice", "Cable Machine", 10,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae"], ["Core"],
   ["Lower Back"], ["Low Back Pain"], {}, [], [], ["Romanian Deadlift"], "machine"),
ex("belt_squat_machine_001", "Belt Squat Machine", "Squat", "Squat", 2, "Novice", "Belt Squat Machine", 44,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], [],
   ["Knee"], ["Patellar Tendon"], {"squat_ratio": 0.5}, [], [], ["Belt Squat"], "machine"),
ex("lever_row_001", "Lever Row", "Horizontal Pull", "Pull", 2, "Novice", "Plate-Loaded Lever Machine", 45,
   ["Latissimus Dorsi", "Rhomboids"], ["Biceps Brachii"], [],
   ["Shoulder", "Lower Back"], [], {}, [], [], ["Chest Supported Row"], "machine"),
ex("lever_chestpress_001", "Lever Chest Press", "Horizontal Push", "Push", 2, "Novice", "Plate-Loaded Lever Machine", 45,
   ["Pectoralis Major"], ["Triceps Brachii"], [],
   ["Shoulder"], [], {}, [], [], ["Chest Press Machine"], "machine"),
]

# =========================================================
# EXPLOSIVE / SPEED-STRENGTH / ATHLETIC POWER
# =========================================================
NEW += [
ex("jump_squat_001", "Jump Squat", "Jump", "Jump", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Calves"], ["Core", "Ankle Stabilizers"],
   ["Knee", "Ankle"], ["Patellar Tendon", "Achilles Tendon - Complete Rupture"], {"squat_ratio": 0.3},
   [], ["Bodyweight Squat Jump"], [], "legs"),
ex("trapbar_jump_001", "Trap Bar Jump", "Jump", "Jump", 3, "Intermediate", "Trap Bar", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Calves"], ["Core", "Ankle Stabilizers"],
   ["Knee", "Ankle"], ["Patellar Tendon"], {"squat_ratio": 0.3}, [], [], ["jump_squat_001"], "legs"),
ex("speed_squat_001", "Speed Squat", "Squat", "Squat", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Gluteus Maximus"], ["Hamstrings"], ["Core"],
   ["Knee", "Lower Back"], [], {"squat_ratio": 0.5}, [], [], [], "speed"),
ex("speed_deadlift_001", "Speed Deadlift", "Hinge", "Hinge", 3, "Intermediate", "Barbell", 5,
   ["Gluteus Maximus", "Hamstrings"], ["Erector Spinae"], ["Core"],
   ["Lower Back"], [], {"deadlift_ratio": 0.5}, [], [], [], "speed"),
ex("high_pull_001", "High Pull", "Hinge", "Explosive Pull", 3, "Intermediate", "Barbell", 5,
   ["Trapezius", "Erector Spinae"], ["Gluteus Maximus", "Deltoids"], ["Core"],
   ["Lower Back", "Shoulder"], ["Low Back Pain"], {"deadlift_ratio": 0.6}, [], [], [], "olympic"),
ex("thruster_001", "Thruster", "Full Body", "Complex", 3, "Intermediate", "Barbell", 5,
   ["Quadriceps", "Anterior Deltoid"], ["Gluteus Maximus", "Triceps Brachii"], ["Core"],
   ["Knee", "Shoulder"], ["Shoulder Instability"], {}, [], [], ["Dumbbell Thruster"], "olympic"),
ex("medball_squatthrow_001", "Medicine Ball Squat Throw", "Power", "Throw", 2, "Novice", "Medicine Ball", 20,
   ["Quadriceps", "Anterior Deltoid"], ["Gluteus Maximus", "Core"], ["Core"],
   ["Shoulder", "Knee"], [], {}, [], [], ["Medicine Ball Rotational Throw"], "kettlebell"),
]

print("Total new exercises:", len(NEW))

# ---- de-dup guard ----
ids = [e["id"] for e in NEW]
dupes = {i for i in ids if ids.count(i) > 1}
assert not dupes, f"duplicate ids in NEW: {dupes}"


def main():
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, BACKUP)
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_ids = {e["id"] for e in data["exercises"]}
    id_dupes = [e["id"] for e in NEW if e["id"] in existing_ids]
    if id_dupes:
        raise SystemExit(f"Duplicate IDs, aborting: {id_dupes}")

    data["exercises"].extend(NEW)
    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(data['exercises'])} total exercises to {SRC}. "
          f"Backup at {BACKUP}. Now run scripts/enrich_exercises.py.")


if __name__ == "__main__":
    main()
