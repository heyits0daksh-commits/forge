import json

SPORTS = ["Wrestling","Judo","Sambo","BJJ","Boxing","Muay Thai","Kickboxing",
          "Sanda","Rugby","Rock Climbing","HYROX","Special Forces"]

# ---- sport-priority templates per movement family (0-100 scale, matches existing data style) ----
TEMPLATES = {
    # bodyweight push/pull/core calisthenics skill work
    "calisthenics": {"Wrestling":70,"Judo":75,"Sambo":75,"BJJ":75,"Boxing":65,"Muay Thai":65,
                      "Kickboxing":65,"Sanda":65,"Rugby":55,"Rock Climbing":80,"HYROX":55,"Special Forces":85},
    # ring / gymnastics strength (front lever, planche, muscle-up family)
    "gymnastics": {"Wrestling":75,"Judo":80,"Sambo":80,"BJJ":80,"Boxing":55,"Muay Thai":55,
                   "Kickboxing":55,"Sanda":55,"Rugby":45,"Rock Climbing":95,"HYROX":45,"Special Forces":85},
    # leg / squat progressions
    "legs": {"Wrestling":80,"Judo":75,"Sambo":75,"BJJ":65,"Boxing":65,"Muay Thai":75,
             "Kickboxing":75,"Sanda":75,"Rugby":85,"Rock Climbing":45,"HYROX":90,"Special Forces":90},
    # olympic / barbell weightlifting (explosive strength)
    "olympic": {"Wrestling":85,"Judo":80,"Sambo":80,"BJJ":55,"Boxing":45,"Muay Thai":55,
                "Kickboxing":50,"Sanda":60,"Rugby":90,"Rock Climbing":20,"HYROX":75,"Special Forces":90},
    # basic barbell strength (beginner lifts)
    "barbell_basic": {"Wrestling":75,"Judo":70,"Sambo":70,"BJJ":55,"Boxing":55,"Muay Thai":60,
                       "Kickboxing":60,"Sanda":60,"Rugby":80,"Rock Climbing":25,"HYROX":80,"Special Forces":85},
    # kettlebell ballistic/conditioning
    "kettlebell": {"Wrestling":75,"Judo":75,"Sambo":75,"BJJ":65,"Boxing":60,"Muay Thai":65,
                   "Kickboxing":65,"Sanda":65,"Rugby":70,"Rock Climbing":40,"HYROX":90,"Special Forces":90},
    # power-rack / positional strength
    "rack": {"Wrestling":65,"Judo":60,"Sambo":60,"BJJ":50,"Boxing":40,"Muay Thai":45,
             "Kickboxing":45,"Sanda":45,"Rugby":75,"Rock Climbing":20,"HYROX":80,"Special Forces":90},
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
# PUSH PROGRESSION (bodyweight -> handstand -> planche)
# =========================================================
NEW += [
ex("wall_pushup_001","Wall Push-Up","Horizontal Push","Push",1,"Beginner","Bodyweight",1,
   ["Pectoralis Major","Anterior Deltoid"],["Triceps Brachii"],["Rectus Abdominis"],
   ["Wrist","Shoulder"],[], {}, ["incline_pushup_001"], [], [], "calisthenics"),
ex("incline_pushup_001","Incline Push-Up","Horizontal Push","Push",1,"Beginner","Bodyweight",1,
   ["Pectoralis Major","Anterior Deltoid"],["Triceps Brachii"],["Rectus Abdominis"],
   ["Wrist","Elbow","Shoulder"],[], {}, ["knee_pushup_001"], ["wall_pushup_001"], [], "calisthenics"),
ex("knee_pushup_001","Knee Push-Up","Horizontal Push","Push",1,"Beginner","Bodyweight",1,
   ["Pectoralis Major","Anterior Deltoid","Triceps Brachii"],["Serratus Anterior"],["Rectus Abdominis"],
   ["Wrist","Elbow","Shoulder"],[], {}, ["pushup_001"], ["incline_pushup_001"], [], "calisthenics"),
ex("pike_pushup_001","Pike Push-Up","Vertical Push","Push",2,"Novice","Bodyweight",1,
   ["Anterior Deltoid","Triceps Brachii"],["Upper Trapezius"],["Core"],
   ["Wrist","Shoulder"],["Shoulder Instability"], {"pushups":10}, ["decline_pike_pushup_001"], ["pushup_001"], [], "calisthenics"),
ex("parallel_bar_dip_001","Parallel Bar Dip","Vertical Push","Push",2,"Novice","Parallel Bars",2,
   ["Triceps Brachii","Pectoralis Major"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"pushups":10}, ["ring_dip_001"], [], [], "calisthenics"),
ex("decline_pike_pushup_001","Decline Pike Push-Up","Vertical Push","Push",3,"Intermediate","Bodyweight",1,
   ["Anterior Deltoid","Triceps Brachii"],["Upper Trapezius"],["Core"],
   ["Wrist","Shoulder"],["Shoulder Instability"], {"pushups":20}, ["wall_hspu_001"], ["pike_pushup_001"], [], "calisthenics"),
ex("wall_hspu_001","Wall-Supported Handstand Push-Up","Vertical Push","Push",4,"Advanced","Bodyweight",1,
   ["Anterior Deltoid","Triceps Brachii"],["Upper Trapezius","Pectoralis Major"],["Core","Rotator Cuff"],
   ["Wrist","Shoulder","Neck"],["Shoulder Instability","Rotator Cuff"], {"pushups":30}, ["freestanding_hspu_001"], ["decline_pike_pushup_001"], [], "gymnastics"),
ex("freestanding_hspu_001","Freestanding Handstand Push-Up","Vertical Push","Push",5,"Elite","Bodyweight",1,
   ["Anterior Deltoid","Triceps Brachii"],["Upper Trapezius","Pectoralis Major"],["Core","Rotator Cuff"],
   ["Wrist","Shoulder","Neck"],["Shoulder Instability","Rotator Cuff"], {"pushups":40}, [], ["wall_hspu_001"], [], "gymnastics"),
ex("planche_lean_001","Planche Lean","Horizontal Push","Isometric",3,"Intermediate","Bodyweight",1,
   ["Anterior Deltoid","Pectoralis Major"],["Serratus Anterior","Triceps Brachii"],["Core","Wrist Flexors"],
   ["Wrist","Shoulder"],["Wrist Pain"], {"pushups":20}, ["tucked_planche_001"], [], [], "gymnastics"),
ex("tucked_planche_001","Tucked Planche","Full Body","Isometric",4,"Advanced","Bodyweight",1,
   ["Anterior Deltoid","Pectoralis Major","Rectus Abdominis"],["Serratus Anterior"],["Wrist Flexors","Core"],
   ["Wrist","Shoulder"],["Wrist Pain","Shoulder Instability"], {"pushups":30}, ["full_planche_001"], ["planche_lean_001"], [], "gymnastics"),
ex("full_planche_001","Full Planche","Full Body","Isometric",5,"Elite","Bodyweight",1,
   ["Anterior Deltoid","Pectoralis Major","Rectus Abdominis"],["Serratus Anterior"],["Wrist Flexors","Core"],
   ["Wrist","Shoulder"],["Wrist Pain","Shoulder Instability"], {"pushups":40}, [], ["tucked_planche_001"], [], "gymnastics"),
]

# =========================================================
# PULL PROGRESSION (dead hang -> front lever / one-arm pull-up)
# =========================================================
NEW += [
ex("passive_deadhang_001","Passive Dead Hang","Vertical Pull","Isometric",1,"Beginner","Pull-up Bar",1,
   ["Latissimus Dorsi","Forearm Flexors"],["Trapezius"],["Rotator Cuff"],
   ["Shoulder","Elbow"],[], {}, ["scap_shrug_001"], [], [], "calisthenics"),
ex("scap_shrug_001","Active Scapular Shrug","Vertical Pull","Pull",1,"Beginner","Pull-up Bar",1,
   ["Trapezius","Rhomboids"],["Latissimus Dorsi"],["Rotator Cuff"],
   ["Shoulder"],[], {}, ["inverted_table_row_001"], ["passive_deadhang_001"], [], "calisthenics"),
ex("inverted_table_row_001","Inverted Table Row","Horizontal Pull","Pull",1,"Beginner","Bodyweight",1,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii"],["Core"],
   ["Shoulder"],[], {}, ["inverted_row_bent_001"], [], [], "calisthenics"),
ex("inverted_row_bent_001","Inverted Bar Row (Knees Bent)","Horizontal Pull","Pull",1,"Beginner","Barbell",5,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii","Trapezius"],["Core"],
   ["Shoulder"],[], {}, ["inverted_row_straight_001"], ["inverted_table_row_001"], [], "calisthenics"),
ex("inverted_row_straight_001","Inverted Bar Row (Legs Straight)","Horizontal Pull","Pull",2,"Novice","Barbell",5,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii","Trapezius"],["Core"],
   ["Shoulder","Lower Back"],[], {}, ["negative_pullup_001"], ["inverted_row_bent_001"], [], "calisthenics"),
ex("negative_pullup_001","Negative Pull-Up","Vertical Pull","Pull",2,"Novice","Pull-up Bar",1,
   ["Latissimus Dorsi","Brachialis"],["Biceps Brachii"],["Core"],
   ["Shoulder","Elbow"],["Golfer's Elbow"], {}, ["chinup_001"], ["inverted_row_straight_001"], [], "calisthenics"),
ex("chinup_001","Chin-Up","Vertical Pull","Pull",2,"Novice","Pull-up Bar",1,
   ["Latissimus Dorsi","Biceps Brachii"],["Brachialis","Rhomboids"],["Core"],
   ["Shoulder","Elbow"],["Golfer's Elbow"], {"pullups":1}, ["pullup_001"], ["negative_pullup_001"], [], "calisthenics"),
ex("wide_grip_pullup_001","Wide-Grip Pull-Up","Vertical Pull","Pull",3,"Intermediate","Pull-up Bar",1,
   ["Latissimus Dorsi"],["Biceps Brachii","Rhomboids"],["Core"],
   ["Shoulder","Elbow"],["Rotator Cuff"], {"pullups":5}, ["archer_pullup_001"], ["pullup_001"], [], "calisthenics"),
ex("lsit_pullup_001","L-Sit Pull-Up","Vertical Pull","Pull",4,"Advanced","Pull-up Bar",1,
   ["Latissimus Dorsi","Rectus Abdominis"],["Hip Flexors","Biceps Brachii"],["Core"],
   ["Shoulder","Hip"],[], {"pullups":8}, [], ["wide_grip_pullup_001"], [], "gymnastics"),
ex("archer_pullup_001","Archer Pull-Up","Vertical Pull","Pull",4,"Advanced","Pull-up Bar",1,
   ["Latissimus Dorsi","Biceps Brachii"],["Brachialis"],["Core"],
   ["Shoulder","Elbow"],["Golfer's Elbow"], {"pullups":8}, ["explosive_c2b_001"], ["wide_grip_pullup_001"], [], "calisthenics"),
ex("explosive_c2b_001","Explosive Chest-to-Bar Pull-Up","Vertical Pull","Pull",4,"Advanced","Pull-up Bar",1,
   ["Latissimus Dorsi","Biceps Brachii"],["Rhomboids","Trapezius"],["Core"],
   ["Shoulder","Elbow"],["Rotator Cuff"], {"pullups":10}, ["bar_muscleup_001"], ["archer_pullup_001"], [], "calisthenics"),
ex("bar_muscleup_001","Bar Muscle-Up","Vertical Pull","Pull",5,"Elite","Pull-up Bar",1,
   ["Latissimus Dorsi","Triceps Brachii"],["Pectoralis Major","Biceps Brachii"],["Core","Rotator Cuff"],
   ["Shoulder","Elbow","Wrist"],["Rotator Cuff","Shoulder Instability"], {"pullups":12}, ["ring_muscleup_001"], ["explosive_c2b_001"], [], "gymnastics"),
ex("ring_muscleup_001","Ring Muscle-Up","Vertical Pull","Pull",5,"Elite","Rings",3,
   ["Latissimus Dorsi","Triceps Brachii"],["Pectoralis Major","Biceps Brachii"],["Core","Rotator Cuff"],
   ["Shoulder","Elbow","Wrist"],["Rotator Cuff","Shoulder Instability"], {"pullups":12}, [], ["bar_muscleup_001"], [], "gymnastics"),
ex("tucked_front_lever_001","Tucked Front Lever","Vertical Pull","Isometric",4,"Advanced","Pull-up Bar",1,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids","Trapezius"],["Core"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {"pullups":8}, ["adv_tucked_front_lever_001"], ["lsit_pullup_001"], [], "gymnastics"),
ex("adv_tucked_front_lever_001","Advanced Tucked Front Lever","Vertical Pull","Isometric",5,"Elite","Pull-up Bar",1,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids","Trapezius"],["Core"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {"pullups":10}, ["full_front_lever_001"], ["tucked_front_lever_001"], [], "gymnastics"),
ex("full_front_lever_001","Full Front Lever","Vertical Pull","Isometric",5,"Elite","Pull-up Bar",1,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids","Trapezius"],["Core"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {"pullups":12}, [], ["adv_tucked_front_lever_001"], [], "gymnastics"),
ex("one_arm_pullup_001","One-Arm Pull-Up","Vertical Pull","Pull",5,"Elite","Pull-up Bar",1,
   ["Latissimus Dorsi","Biceps Brachii"],["Brachialis","Core"],["Rotator Cuff"],
   ["Shoulder","Elbow"],["Golfer's Elbow","Rotator Cuff"], {"pullups":15}, [], ["archer_pullup_001"], [], "gymnastics"),
]

# =========================================================
# CORE & ABS PROGRESSION
# =========================================================
NEW += [
ex("dead_bug_001","Dead Bug","Core","Anti-Extension",1,"Beginner","Bodyweight",1,
   ["Rectus Abdominis","Transverse Abdominis"],["Hip Flexors"],["Erector Spinae"],
   ["Lower Back"],["Low Back Pain"], {}, ["side_plank_001"], [], [], "calisthenics"),
ex("side_plank_001","Side Plank","Core","Isometric",1,"Beginner","Bodyweight",1,
   ["Obliques"],["Gluteus Medius"],["Rectus Abdominis"],
   ["Shoulder","Lower Back"],[], {}, ["hanging_knee_raise_001"], ["dead_bug_001"], [], "calisthenics"),
ex("hanging_knee_raise_001","Hanging Knee Raise","Core","Flexion",2,"Novice","Pull-up Bar",1,
   ["Rectus Abdominis","Hip Flexors"],["Obliques"],["Forearm Flexors"],
   ["Shoulder","Hip"],[], {}, ["captains_chair_raise_001"], ["side_plank_001"], [], "calisthenics"),
ex("captains_chair_raise_001","Captain's Chair Leg Raise","Core","Flexion",2,"Novice","Captain's Chair",2,
   ["Rectus Abdominis","Hip Flexors"],["Obliques"],["Erector Spinae"],
   ["Lower Back","Hip"],[], {}, ["hanging_leg_raise_001"], ["hanging_knee_raise_001"], [], "calisthenics"),
ex("floor_lsit_tuck_001","Floor L-Sit Tuck","Core","Isometric",2,"Novice","Bodyweight",1,
   ["Rectus Abdominis","Hip Flexors"],["Triceps Brachii"],["Wrist Flexors"],
   ["Wrist","Hip"],[], {}, ["parallel_bar_lsit_001"], [], [], "calisthenics"),
ex("parallel_bar_lsit_001","Parallel Bar L-Sit","Core","Isometric",4,"Advanced","Parallel Bars",2,
   ["Rectus Abdominis","Hip Flexors"],["Triceps Brachii","Quadriceps"],["Wrist Flexors"],
   ["Wrist","Shoulder","Hip"],[], {"pushups":15}, ["dragon_flag_001"], ["floor_lsit_tuck_001"], [], "gymnastics"),
ex("dragon_flag_001","Dragon Flag","Core","Anti-Extension",5,"Elite","Bodyweight",1,
   ["Rectus Abdominis","Obliques"],["Hip Flexors","Erector Spinae"],["Latissimus Dorsi"],
   ["Lower Back","Shoulder"],["Low Back Pain"], {"pullups":8}, ["v_sit_hold_001"], ["parallel_bar_lsit_001"], [], "gymnastics"),
ex("v_sit_hold_001","V-Sit Hold","Core","Isometric",4,"Advanced","Bodyweight",1,
   ["Rectus Abdominis","Hip Flexors"],["Obliques"],["Erector Spinae"],
   ["Lower Back","Hip"],["Low Back Pain"], {}, ["human_flag_001"], ["parallel_bar_lsit_001"], [], "gymnastics"),
ex("human_flag_001","Human Flag","Full Body","Isometric",5,"Elite","Pull-up Bar",1,
   ["Obliques","Latissimus Dorsi"],["Anterior Deltoid","Rectus Abdominis"],["Wrist Flexors","Core"],
   ["Shoulder","Wrist","Lower Back"],["Shoulder Instability","Low Back Pain"], {"pullups":10,"pushups":20}, [], ["dragon_flag_001"], [], "gymnastics"),
]

# =========================================================
# LEG PROGRESSION
# =========================================================
NEW += [
ex("wall_sit_001","Wall Sit","Squat","Isometric",1,"Beginner","Bodyweight",1,
   ["Quadriceps"],["Gluteus Maximus"],["Erector Spinae"],
   ["Knee"],[], {}, ["box_squat_001"], [], [], "legs"),
ex("box_squat_001","Box Squat","Squat","Squat",1,"Beginner","Plyo Box",8,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, ["sumo_squat_001"], ["wall_sit_001"], [], "legs"),
ex("sumo_squat_001","Sumo Squat","Squat","Squat",1,"Beginner","Bodyweight",1,
   ["Adductors","Gluteus Maximus"],["Quadriceps"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, ["walking_lunge_001"], [], [], "legs"),
ex("walking_lunge_001","Walking Lunge","Squat","Lunge",1,"Beginner","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, ["reverse_lunge_001"], [], [], "legs"),
ex("reverse_lunge_001","Reverse Lunge","Squat","Lunge",1,"Beginner","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee"],[], {}, ["bulgarian_split_squat_001"], ["walking_lunge_001"], [], "legs"),
ex("bulgarian_split_squat_001","Bulgarian Split Squat","Squat","Lunge",2,"Novice","Dumbbell",3,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings","Adductors"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, ["assisted_pistol_squat_001"], ["reverse_lunge_001"], [], "legs"),
ex("single_leg_hip_thrust_001","Single-Leg Hip Thrust","Hinge","Hinge",2,"Novice","Bodyweight",1,
   ["Gluteus Maximus","Hamstrings"],["Erector Spinae"],["Gluteus Medius"],
   ["Hip","Lower Back"],["Low Back Pain"], {}, [], [], [], "legs"),
ex("step_up_001","Step-Up","Squat","Squat",1,"Beginner","Plyo Box",8,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee"],[], {}, [], [], [], "legs"),
ex("assisted_pistol_squat_001","Assisted Pistol Squat","Squat","Squat",3,"Intermediate","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae","Gluteus Medius"],
   ["Knee","Hip"],["Patellar Tendon"], {}, ["airborne_squat_001"], ["bulgarian_split_squat_001"], [], "legs"),
ex("airborne_squat_001","Airborne Squat","Squat","Squat",3,"Intermediate","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae","Gluteus Medius"],
   ["Knee","Hip"],["Patellar Tendon"], {}, ["shrimp_squat_001"], ["assisted_pistol_squat_001"], [], "legs"),
ex("shrimp_squat_001","Shrimp Squat","Squat","Squat",4,"Advanced","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae","Gluteus Medius"],
   ["Knee","Hip"],["Patellar Tendon"], {}, ["pistol_squat_001"], ["airborne_squat_001"], [], "legs"),
ex("pistol_squat_001","Pistol Squat","Squat","Squat",4,"Advanced","Bodyweight",1,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae","Gluteus Medius"],
   ["Knee","Hip"],["Patellar Tendon"], {}, [], ["shrimp_squat_001"], [], "legs"),
ex("nordic_hamstring_curl_001","Nordic Hamstring Curl","Hinge","Hinge",4,"Advanced","Bodyweight",1,
   ["Hamstrings"],["Gluteus Maximus"],["Erector Spinae"],
   ["Knee"],["Hamstring Strain"], {}, [], [], [], "legs"),
]

# =========================================================
# WEIGHTLIFTING - Beginner
# =========================================================
NEW += [
ex("goblet_squat_001","Goblet Squat","Squat","Squat",2,"Novice","Kettlebell",4,
   ["Quadriceps","Gluteus Maximus"],["Adductors"],["Erector Spinae","Core"],
   ["Knee","Hip"],[], {}, ["bb_back_squat_001"], ["squat_001"], [], "barbell_basic"),
ex("push_press_001","Push Press","Vertical Push","Push",3,"Intermediate","Barbell",5,
   ["Anterior Deltoid","Triceps Brachii"],["Quadriceps","Trapezius"],["Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability"], {"bench_ratio":0.6}, ["push_jerk_001"], ["bb_overhead_press_001"], [], "barbell_basic"),
ex("floor_press_001","Floor Press","Horizontal Push","Push",2,"Novice","Barbell",5,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"bench_ratio":0.4}, ["db_bench_press_001"], [], [], "barbell_basic"),
ex("rdl_barbell_001","Romanian Deadlift","Hinge","Hinge",2,"Novice","Barbell",5,
   ["Hamstrings","Gluteus Maximus"],["Erector Spinae"],["Core"],
   ["Hip","Lower Back"],["Low Back Pain"], {"deadlift_ratio":0.5}, ["sumo_deadlift_001"], ["bb_deadlift_001"], [], "barbell_basic"),
ex("bb_bent_over_row_001","Barbell Bent-Over Row","Horizontal Pull","Pull",2,"Novice","Barbell",5,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii","Trapezius"],["Erector Spinae"],
   ["Lower Back","Shoulder"],["Low Back Pain"], {"deadlift_ratio":0.4}, ["pendlay_row_001"], ["db_row_001"], [], "barbell_basic"),
ex("lat_pulldown_001","Lat Pulldown","Vertical Pull","Pull",1,"Beginner","Cable Machine",5,
   ["Latissimus Dorsi"],["Biceps Brachii","Rhomboids"],["Core"],
   ["Shoulder","Elbow"],[], {}, ["chinup_001"], [], [], "barbell_basic"),
]

# =========================================================
# WEIGHTLIFTING - Intermediate
# =========================================================
NEW += [
ex("power_clean_001","Barbell Power Clean","Full Body","Explosive Pull",4,"Advanced","Barbell",5,
   ["Trapezius","Gluteus Maximus","Hamstrings"],["Quadriceps","Anterior Deltoid"],["Core","Erector Spinae"],
   ["Lower Back","Knee","Wrist"],["Low Back Pain"], {"deadlift_ratio":0.9,"squat_ratio":0.7}, ["full_squat_clean_001"], ["hang_clean_001"], [], "olympic"),
ex("power_snatch_001","Power Snatch","Full Body","Explosive Pull",5,"Advanced","Barbell",5,
   ["Trapezius","Gluteus Maximus","Hamstrings"],["Anterior Deltoid","Quadriceps"],["Core","Rotator Cuff"],
   ["Shoulder","Lower Back","Wrist"],["Shoulder Instability","Low Back Pain"], {"deadlift_ratio":0.8,"squat_ratio":0.7}, ["full_squat_snatch_001"], [], [], "olympic"),
ex("hang_clean_001","Hang Clean","Full Body","Explosive Pull",3,"Intermediate","Barbell",5,
   ["Trapezius","Gluteus Maximus","Hamstrings"],["Quadriceps","Anterior Deltoid"],["Core"],
   ["Lower Back","Knee"],["Low Back Pain"], {"deadlift_ratio":0.7,"squat_ratio":0.5}, ["power_clean_001"], ["rdl_barbell_001"], [], "olympic"),
ex("overhead_squat_001","Overhead Squat","Squat","Squat",5,"Advanced","Barbell",5,
   ["Quadriceps","Anterior Deltoid"],["Gluteus Maximus","Erector Spinae"],["Rotator Cuff","Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability","Low Back Pain"], {"squat_ratio":0.8,"bench_ratio":0.4}, [], ["goblet_squat_001"], [], "olympic"),
ex("push_jerk_001","Push Jerk","Vertical Push","Push",4,"Advanced","Barbell",5,
   ["Anterior Deltoid","Quadriceps"],["Triceps Brachii","Trapezius"],["Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability"], {"bench_ratio":0.7,"squat_ratio":0.5}, ["split_jerk_001"], ["push_press_001"], [], "olympic"),
ex("snatch_grip_deadlift_001","Snatch-Grip Deadlift","Hinge","Hinge",3,"Intermediate","Barbell",5,
   ["Hamstrings","Erector Spinae"],["Trapezius","Gluteus Maximus"],["Core"],
   ["Lower Back"],["Low Back Pain"], {"deadlift_ratio":0.8}, ["deficit_deadlift_001"], ["rdl_barbell_001"], [], "olympic"),
ex("sumo_deadlift_001","Sumo Deadlift","Hinge","Hinge",3,"Intermediate","Barbell",5,
   ["Gluteus Maximus","Adductors"],["Hamstrings","Erector Spinae"],["Core"],
   ["Hip","Lower Back","Knee"],["Low Back Pain"], {"deadlift_ratio":0.9}, [], ["rdl_barbell_001"], ["bb_deadlift_001"], "barbell_basic"),
ex("pendlay_row_001","Pendlay Row","Horizontal Pull","Pull",3,"Intermediate","Barbell",5,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii","Trapezius"],["Erector Spinae"],
   ["Lower Back","Shoulder"],["Low Back Pain"], {"deadlift_ratio":0.6}, [], ["bb_bent_over_row_001"], [], "barbell_basic"),
ex("weighted_c2b_pullup_001","Weighted Chest-to-Bar Pull-Up","Vertical Pull","Pull",4,"Advanced","Pull-up Bar",1,
   ["Latissimus Dorsi","Biceps Brachii"],["Rhomboids","Trapezius"],["Core"],
   ["Shoulder","Elbow"],["Rotator Cuff"], {"pullups":10}, [], ["explosive_c2b_001","weighted_pullup_001"], [], "calisthenics"),
]

# =========================================================
# WEIGHTLIFTING - Advanced
# =========================================================
NEW += [
ex("full_squat_clean_001","Full Squat Clean","Full Body","Explosive Pull",5,"Elite","Barbell",5,
   ["Trapezius","Quadriceps","Gluteus Maximus"],["Hamstrings","Anterior Deltoid"],["Core","Erector Spinae"],
   ["Lower Back","Knee","Wrist"],["Low Back Pain","Patellar Tendon"], {"deadlift_ratio":1.1,"squat_ratio":1.0}, ["clean_and_jerk_001"], ["power_clean_001"], [], "olympic"),
ex("full_squat_snatch_001","Full Squat Snatch","Full Body","Explosive Pull",5,"Elite","Barbell",5,
   ["Trapezius","Quadriceps","Gluteus Maximus"],["Anterior Deltoid","Hamstrings"],["Rotator Cuff","Core"],
   ["Shoulder","Lower Back","Knee"],["Shoulder Instability","Low Back Pain"], {"deadlift_ratio":1.0,"squat_ratio":1.0}, ["snatch_balance_001"], ["power_snatch_001"], [], "olympic"),
ex("split_jerk_001","Split Jerk","Vertical Push","Push",5,"Elite","Barbell",5,
   ["Anterior Deltoid","Quadriceps"],["Triceps Brachii","Gluteus Maximus"],["Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability"], {"bench_ratio":0.9,"squat_ratio":0.7}, ["clean_and_jerk_001"], ["push_jerk_001"], [], "olympic"),
ex("clean_and_jerk_001","Clean and Jerk","Full Body","Complex",5,"Elite","Barbell",5,
   ["Trapezius","Quadriceps","Anterior Deltoid"],["Hamstrings","Triceps Brachii"],["Core","Erector Spinae"],
   ["Lower Back","Knee","Shoulder","Wrist"],["Low Back Pain","Shoulder Instability"], {"deadlift_ratio":1.2,"squat_ratio":1.1,"bench_ratio":0.9}, [], ["full_squat_clean_001","split_jerk_001"], [], "olympic"),
ex("snatch_balance_001","Snatch Balance","Full Body","Complex",5,"Elite","Barbell",5,
   ["Quadriceps","Anterior Deltoid"],["Gluteus Maximus","Trapezius"],["Rotator Cuff","Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability"], {"squat_ratio":1.0,"bench_ratio":0.6}, [], ["full_squat_snatch_001"], [], "olympic"),
ex("deficit_deadlift_001","Deficit Deadlift","Hinge","Hinge",4,"Advanced","Barbell",5,
   ["Hamstrings","Erector Spinae"],["Gluteus Maximus","Trapezius"],["Core"],
   ["Lower Back","Knee"],["Low Back Pain"], {"deadlift_ratio":1.0}, ["halting_snatch_deadlift_001"], ["snatch_grip_deadlift_001"], [], "olympic"),
ex("halting_snatch_deadlift_001","Halting Snatch Deadlift","Hinge","Hinge",4,"Advanced","Barbell",5,
   ["Hamstrings","Erector Spinae","Trapezius"],["Gluteus Maximus"],["Core"],
   ["Lower Back"],["Low Back Pain"], {"deadlift_ratio":0.9}, [], ["deficit_deadlift_001"], [], "olympic"),
ex("block_clean_001","Block Clean","Full Body","Explosive Pull",5,"Elite","Barbell",5,
   ["Trapezius","Quadriceps","Gluteus Maximus"],["Hamstrings","Anterior Deltoid"],["Core"],
   ["Lower Back","Knee","Wrist"],["Low Back Pain"], {"deadlift_ratio":1.0,"squat_ratio":0.9}, [], ["power_clean_001"], [], "olympic"),
ex("good_morning_001","Good Morning","Hinge","Hinge",3,"Intermediate","Barbell",5,
   ["Hamstrings","Erector Spinae"],["Gluteus Maximus"],["Core"],
   ["Lower Back"],["Low Back Pain"], {"squat_ratio":0.5}, [], ["rdl_barbell_001"], [], "barbell_basic"),
ex("heavy_overhead_carry_001","Heavy Overhead Carry","Carry","Carry",4,"Advanced","Barbell",5,
   ["Anterior Deltoid","Core"],["Trapezius","Forearm Flexors"],["Rotator Cuff","Erector Spinae"],
   ["Shoulder","Lower Back"],["Shoulder Instability","Low Back Pain"], {"bench_ratio":0.6}, [], ["farmers_walk_001"], [], "olympic"),
]

# =========================================================
# KETTLEBELL - Beginner
# =========================================================
NEW += [
ex("kb_deadlift_001","Kettlebell Deadlift","Hinge","Hinge",1,"Beginner","Kettlebell",4,
   ["Gluteus Maximus","Hamstrings"],["Erector Spinae"],["Core"],
   ["Hip","Lower Back"],["Low Back Pain"], {}, ["kb_swing_001"], [], [], "kettlebell"),
ex("kb_overhead_press_2h_001","Two-Handed Kettlebell Overhead Press","Vertical Push","Push",1,"Beginner","Kettlebell",4,
   ["Anterior Deltoid","Triceps Brachii"],["Trapezius"],["Core"],
   ["Shoulder"],["Shoulder Instability"], {}, ["kb_overhead_press_1h_001"], [], [], "kettlebell"),
ex("kb_floor_press_001","Kettlebell Floor Press","Horizontal Push","Push",1,"Beginner","Kettlebell",4,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],[], {}, [], [], ["floor_press_001"], "kettlebell"),
ex("kb_row_2h_001","Two-Handed Kettlebell Row","Horizontal Pull","Pull",1,"Beginner","Kettlebell",4,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii"],["Erector Spinae"],
   ["Lower Back","Shoulder"],[], {}, ["db_row_001"], [], [], "kettlebell"),
ex("suitcase_carry_001","Suitcase Carry","Carry","Carry",2,"Novice","Kettlebell",4,
   ["Obliques","Forearm Flexors"],["Trapezius"],["Erector Spinae","Core"],
   ["Lower Back","Shoulder"],["Low Back Pain"], {}, ["farmers_walk_001"], [], [], "kettlebell"),
]

# =========================================================
# KETTLEBELL - Intermediate
# =========================================================
NEW += [
ex("kb_swing_1h_001","One-Handed Kettlebell Swing","Hinge","Ballistic",2,"Novice","Kettlebell",4,
   ["Gluteus Maximus","Hamstrings"],["Forearm Flexors","Obliques"],["Core","Erector Spinae"],
   ["Hip","Lower Back","Shoulder"],["Low Back Pain"], {}, ["kb_clean_001"], ["kb_swing_001"], [], "kettlebell"),
ex("kb_clean_001","Kettlebell Clean","Full Body","Ballistic",3,"Intermediate","Kettlebell",4,
   ["Gluteus Maximus","Hamstrings","Forearm Flexors"],["Trapezius"],["Core"],
   ["Wrist","Elbow","Lower Back"],["Low Back Pain"], {}, ["kb_snatch_001"], ["kb_swing_1h_001"], [], "kettlebell"),
ex("kb_high_pull_001","Kettlebell High Pull","Hinge","Ballistic",2,"Novice","Kettlebell",4,
   ["Gluteus Maximus","Trapezius"],["Hamstrings","Anterior Deltoid"],["Core"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {}, [], ["kb_swing_1h_001"], [], "kettlebell"),
ex("kb_overhead_press_1h_001","Single-Arm Kettlebell Overhead Press","Vertical Push","Push",2,"Novice","Kettlebell",4,
   ["Anterior Deltoid","Triceps Brachii"],["Obliques"],["Core","Rotator Cuff"],
   ["Shoulder"],["Shoulder Instability"], {}, ["kb_push_press_001"], ["kb_overhead_press_2h_001"], [], "kettlebell"),
ex("kb_push_press_001","Kettlebell Push Press","Vertical Push","Push",3,"Intermediate","Kettlebell",4,
   ["Anterior Deltoid","Triceps Brachii","Quadriceps"],["Trapezius"],["Core"],
   ["Shoulder","Knee"],["Shoulder Instability"], {}, [], ["kb_overhead_press_1h_001"], [], "kettlebell"),
ex("kb_windmill_001","Kettlebell Windmill","Full Body","Rotation",3,"Intermediate","Kettlebell",4,
   ["Obliques","Anterior Deltoid"],["Hamstrings"],["Erector Spinae","Rotator Cuff"],
   ["Shoulder","Lower Back","Hip"],["Low Back Pain","Shoulder Instability"], {}, [], [], [], "kettlebell"),
ex("kb_racked_squat_001","Racked Kettlebell Squat","Squat","Squat",2,"Novice","Kettlebell",4,
   ["Quadriceps","Gluteus Maximus"],["Core"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, ["kb_overhead_squat_001"], ["goblet_squat_001"], [], "kettlebell"),
ex("kb_reverse_lunge_001","Kettlebell Reverse Lunge","Squat","Lunge",2,"Novice","Kettlebell",4,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee","Hip"],[], {}, [], ["reverse_lunge_001"], [], "kettlebell"),
ex("tgu_partial_001","Turkish Get-Up Partial (To Elbow)","Full Body","Complex",2,"Novice","Kettlebell",4,
   ["Core","Anterior Deltoid"],["Gluteus Maximus"],["Erector Spinae","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Shoulder Instability","Low Back Pain"], {}, ["turkish_getup_001"], [], [], "kettlebell"),
ex("kb_rack_carry_001","Kettlebell Rack Carry","Carry","Carry",2,"Novice","Kettlebell",4,
   ["Core","Trapezius"],["Forearm Flexors"],["Erector Spinae"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {}, [], ["suitcase_carry_001"], [], "kettlebell"),
]

# =========================================================
# KETTLEBELL - Advanced
# =========================================================
NEW += [
ex("kb_snatch_001","Kettlebell Snatch","Full Body","Ballistic",4,"Advanced","Kettlebell",4,
   ["Gluteus Maximus","Anterior Deltoid","Trapezius"],["Hamstrings","Forearm Flexors"],["Core","Rotator Cuff"],
   ["Shoulder","Wrist","Lower Back"],["Shoulder Instability","Low Back Pain"], {}, [], ["kb_clean_001"], [], "kettlebell"),
ex("kb_jerk_001","Kettlebell Jerk","Full Body","Complex",4,"Advanced","Kettlebell",4,
   ["Anterior Deltoid","Quadriceps"],["Triceps Brachii","Trapezius"],["Core"],
   ["Shoulder","Knee"],["Shoulder Instability"], {}, ["double_kb_cj_001"], ["kb_push_press_001"], [], "kettlebell"),
ex("double_kb_cj_001","Double Kettlebell Clean and Jerk","Full Body","Complex",5,"Elite","Kettlebell",4,
   ["Gluteus Maximus","Anterior Deltoid","Trapezius"],["Hamstrings","Triceps Brachii"],["Core","Erector Spinae"],
   ["Shoulder","Wrist","Lower Back","Knee"],["Low Back Pain","Shoulder Instability"], {}, [], ["kb_clean_001","kb_jerk_001"], [], "kettlebell"),
ex("kb_tactical_juggle_001","Kettlebell Tactical Juggle","Full Body","Ballistic",4,"Advanced","Kettlebell",4,
   ["Forearm Flexors","Anterior Deltoid"],["Obliques"],["Core","Rotator Cuff"],
   ["Wrist","Shoulder"],["Shoulder Instability"], {}, [], ["kb_clean_001"], [], "kettlebell"),
ex("kb_overhead_squat_001","Kettlebell Overhead Squat","Squat","Squat",4,"Advanced","Kettlebell",4,
   ["Quadriceps","Anterior Deltoid"],["Gluteus Maximus"],["Rotator Cuff","Core"],
   ["Shoulder","Knee","Lower Back"],["Shoulder Instability"], {}, [], ["kb_racked_squat_001"], [], "kettlebell"),
ex("kb_pistol_squat_001","Kettlebell-Loaded Pistol Squat","Squat","Squat",5,"Elite","Kettlebell",4,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae","Gluteus Medius"],
   ["Knee","Hip"],["Patellar Tendon"], {}, [], ["pistol_squat_001"], [], "kettlebell"),
ex("kb_flip_001","Kettlebell Flip","Full Body","Ballistic",4,"Advanced","Kettlebell",4,
   ["Forearm Flexors","Anterior Deltoid"],["Obliques"],["Core"],
   ["Wrist","Shoulder"],[], {}, [], [], [], "kettlebell"),
ex("kb_bottom_up_press_001","Bottom-Up Kettlebell Press","Vertical Push","Push",4,"Advanced","Kettlebell",4,
   ["Anterior Deltoid","Forearm Flexors"],["Triceps Brachii"],["Rotator Cuff","Core"],
   ["Shoulder","Wrist"],["Shoulder Instability"], {}, [], ["kb_overhead_press_1h_001"], [], "kettlebell"),
]

# =========================================================
# RINGS - Beginner
# =========================================================
NEW += [
ex("ring_support_hold_001","Ring Support Hold","Vertical Push","Isometric",2,"Novice","Rings",3,
   ["Triceps Brachii","Anterior Deltoid"],["Pectoralis Major"],["Rotator Cuff","Core"],
   ["Shoulder","Wrist"],["Shoulder Instability"], {}, ["ring_pushup_001"], [], [], "gymnastics"),
ex("ring_plank_001","Ring Plank","Core","Isometric",2,"Novice","Rings",3,
   ["Rectus Abdominis"],["Anterior Deltoid"],["Rotator Cuff","Wrist Flexors"],
   ["Shoulder","Wrist"],[], {}, ["ring_pushup_001"], [], [], "gymnastics"),
ex("ring_row_001","Ring Row","Horizontal Pull","Pull",1,"Beginner","Rings",3,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii"],["Rotator Cuff","Core"],
   ["Shoulder"],[], {}, ["ring_pullup_001"], [], ["inverted_table_row_001"], "gymnastics"),
ex("ring_pushup_001","Ring Push-Up","Horizontal Push","Push",2,"Novice","Rings",3,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Rotator Cuff","Core"],
   ["Shoulder","Wrist"],["Shoulder Instability"], {"pushups":10}, ["ring_flye_001"], ["ring_support_hold_001","ring_plank_001"], [], "gymnastics"),
ex("ring_scap_pullup_001","Scapular Pull-Up (Rings)","Vertical Pull","Isometric",1,"Beginner","Rings",3,
   ["Trapezius","Rhomboids"],["Latissimus Dorsi"],["Rotator Cuff"],
   ["Shoulder"],[], {}, ["ring_pullup_001"], [], ["scap_shrug_001"], "gymnastics"),
ex("assisted_ring_squat_001","Assisted Ring Squat","Squat","Squat",1,"Beginner","Rings",3,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Core","Rotator Cuff"],
   ["Knee","Shoulder"],[], {}, [], [], [], "gymnastics"),
]

# =========================================================
# RINGS - Intermediate
# =========================================================
NEW += [
ex("ring_pullup_001","Ring Pull-Up","Vertical Pull","Pull",2,"Novice","Rings",3,
   ["Latissimus Dorsi","Biceps Brachii"],["Rhomboids"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Rotator Cuff"], {"pullups":3}, ["ring_chinup_001"], ["ring_row_001","ring_scap_pullup_001"], [], "gymnastics"),
ex("ring_chinup_001","Ring Chin-Up","Vertical Pull","Pull",2,"Novice","Rings",3,
   ["Latissimus Dorsi","Biceps Brachii"],["Brachialis"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Golfer's Elbow"], {"pullups":3}, ["ring_lsit_hold_001"], ["ring_pullup_001"], [], "gymnastics"),
ex("ring_lsit_hold_001","Ring L-Sit Hold","Core","Isometric",3,"Intermediate","Rings",3,
   ["Rectus Abdominis","Hip Flexors"],["Triceps Brachii"],["Rotator Cuff","Wrist Flexors"],
   ["Shoulder","Wrist","Hip"],[], {}, [], ["ring_chinup_001"], ["parallel_bar_lsit_001"], "gymnastics"),
ex("ring_inverted_row_001","Ring Inverted Row","Horizontal Pull","Pull",2,"Novice","Rings",3,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii"],["Core","Rotator Cuff"],
   ["Shoulder"],[], {}, [], ["ring_row_001"], [], "gymnastics"),
ex("ring_rollout_001","Ring Rollout","Core","Anti-Extension",3,"Intermediate","Rings",3,
   ["Rectus Abdominis"],["Latissimus Dorsi"],["Erector Spinae","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Low Back Pain","Shoulder Instability"], {}, [], [], [], "gymnastics"),
ex("ring_flye_001","Ring Flye","Horizontal Push","Push",3,"Intermediate","Rings",3,
   ["Pectoralis Major"],["Anterior Deltoid"],["Rotator Cuff","Core"],
   ["Shoulder"],["Shoulder Instability"], {"pushups":15}, [], ["ring_pushup_001"], [], "gymnastics"),
ex("skin_the_cat_001","Skin the Cat","Vertical Pull","Complex",3,"Intermediate","Rings",3,
   ["Latissimus Dorsi","Core"],["Anterior Deltoid"],["Rotator Cuff"],
   ["Shoulder"],["Shoulder Instability"], {}, ["ring_false_grip_hang_001"], ["ring_pullup_001"], [], "gymnastics"),
]

# =========================================================
# RINGS - Advanced
# =========================================================
NEW += [
ex("ring_false_grip_hang_001","Ring False Grip Hang","Vertical Pull","Isometric",3,"Intermediate","Rings",3,
   ["Forearm Flexors","Latissimus Dorsi"],["Biceps Brachii"],["Rotator Cuff"],
   ["Wrist","Shoulder"],[], {}, ["ring_muscleup_001"], ["skin_the_cat_001"], [], "gymnastics"),
ex("archer_ring_pullup_001","Archer Ring Pull-Up","Vertical Pull","Pull",4,"Advanced","Rings",3,
   ["Latissimus Dorsi","Biceps Brachii"],["Brachialis"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Golfer's Elbow"], {"pullups":8}, [], ["ring_chinup_001"], ["archer_pullup_001"], "gymnastics"),
ex("archer_ring_pushup_001","Archer Ring Push-Up","Horizontal Push","Push",4,"Advanced","Rings",3,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Rotator Cuff","Core"],
   ["Shoulder","Wrist"],["Shoulder Instability"], {"pushups":20}, [], ["ring_flye_001"], [], "gymnastics"),
ex("ring_archer_dip_001","Ring Archer Dip","Vertical Push","Push",4,"Advanced","Rings",3,
   ["Triceps Brachii","Pectoralis Major"],["Anterior Deltoid"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"pushups":20}, [], ["parallel_bar_dip_001"], [], "gymnastics"),
ex("tucked_ring_front_lever_001","Tucked Ring Front Lever","Vertical Pull","Isometric",4,"Advanced","Rings",3,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids"],["Core","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {"pullups":8}, ["full_ring_front_lever_001"], ["ring_false_grip_hang_001"], ["tucked_front_lever_001"], "gymnastics"),
ex("tucked_ring_back_lever_001","Tucked Ring Back Lever","Vertical Pull","Isometric",4,"Advanced","Rings",3,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids"],["Core","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Low Back Pain","Shoulder Instability"], {"pullups":8}, ["full_ring_back_lever_001"], ["ring_false_grip_hang_001"], [], "gymnastics"),
ex("ring_handstand_001","Ring Handstand","Vertical Push","Isometric",5,"Elite","Rings",3,
   ["Anterior Deltoid","Core"],["Triceps Brachii"],["Rotator Cuff","Wrist Flexors"],
   ["Shoulder","Wrist"],["Shoulder Instability"], {"pushups":25}, [], ["ring_archer_dip_001"], ["freestanding_hspu_001"], "gymnastics"),
]

# =========================================================
# RINGS - Elite
# =========================================================
NEW += [
ex("full_ring_front_lever_001","Full Ring Front Lever","Vertical Pull","Isometric",5,"Elite","Rings",3,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids"],["Core","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Low Back Pain"], {"pullups":12}, [], ["tucked_ring_front_lever_001"], ["full_front_lever_001"], "gymnastics"),
ex("full_ring_back_lever_001","Full Ring Back Lever","Vertical Pull","Isometric",5,"Elite","Rings",3,
   ["Latissimus Dorsi","Rectus Abdominis"],["Rhomboids"],["Core","Rotator Cuff"],
   ["Shoulder","Lower Back"],["Low Back Pain","Shoulder Instability"], {"pullups":12}, [], ["tucked_ring_back_lever_001"], [], "gymnastics"),
ex("iron_cross_001","Iron Cross","Horizontal Push","Isometric",5,"Elite","Rings",3,
   ["Pectoralis Major","Anterior Deltoid"],["Triceps Brachii"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Shoulder Instability","Rotator Cuff"], {"pushups":30}, [], ["ring_handstand_001"], [], "gymnastics"),
ex("ring_planche_001","Ring Planche","Full Body","Isometric",5,"Elite","Rings",3,
   ["Anterior Deltoid","Pectoralis Major","Rectus Abdominis"],["Serratus Anterior"],["Wrist Flexors","Core"],
   ["Wrist","Shoulder"],["Wrist Pain","Shoulder Instability"], {"pushups":30}, [], ["ring_handstand_001"], ["full_planche_001"], "gymnastics"),
ex("maltese_cross_001","Maltese Cross","Full Body","Isometric",5,"Elite","Rings",3,
   ["Pectoralis Major","Anterior Deltoid","Rectus Abdominis"],["Triceps Brachii"],["Rotator Cuff","Core"],
   ["Shoulder","Elbow"],["Shoulder Instability","Rotator Cuff"], {"pushups":35}, [], ["iron_cross_001","ring_planche_001"], [], "gymnastics"),
]

# =========================================================
# RACK SUPPORT - Beginner / Intermediate / Advanced
# =========================================================
NEW += [
ex("rack_split_squat_001","Rack-Supported Split Squat","Squat","Lunge",1,"Beginner","Power Rack",5,
   ["Quadriceps","Gluteus Maximus"],["Hamstrings"],["Erector Spinae"],
   ["Knee"],[], {}, ["bulgarian_split_squat_001"], [], [], "rack"),
ex("iso_rack_pull_pins_001","Isometric Rack Pull (Against Pins)","Hinge","Isometric",1,"Beginner","Power Rack",5,
   ["Erector Spinae","Trapezius"],["Gluteus Maximus","Forearm Flexors"],["Core"],
   ["Lower Back"],["Low Back Pain"], {}, ["rack_pull_below_knee_001"], [], [], "rack"),
ex("rack_pushup_001","Rack-Supported Push-Up","Horizontal Push","Push",1,"Beginner","Power Rack",5,
   ["Pectoralis Major","Anterior Deltoid"],["Triceps Brachii"],["Core"],
   ["Wrist","Shoulder"],[], {}, [], [], ["incline_pushup_001"], "rack"),
ex("pin_bench_mid_001","Pin Bench Press (Mid-Range)","Horizontal Push","Push",2,"Novice","Power Rack",5,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"bench_ratio":0.5}, ["bottom_up_pin_bench_001"], [], [], "rack"),
ex("rack_pull_below_knee_001","Rack Pull (Below Knee)","Hinge","Hinge",3,"Intermediate","Power Rack",5,
   ["Erector Spinae","Trapezius"],["Gluteus Maximus","Forearm Flexors"],["Core"],
   ["Lower Back"],["Low Back Pain"], {"deadlift_ratio":0.9}, ["high_rack_pull_001"], ["iso_rack_pull_pins_001"], [], "rack"),
ex("pin_press_overhead_001","Pin Press (Overhead)","Vertical Push","Push",3,"Intermediate","Power Rack",5,
   ["Anterior Deltoid","Triceps Brachii"],["Trapezius"],["Core"],
   ["Shoulder"],["Shoulder Instability"], {"bench_ratio":0.5}, [], [], [], "rack"),
ex("cheat_row_pins_001","Cheat Row (From Pins)","Horizontal Pull","Pull",3,"Intermediate","Power Rack",5,
   ["Latissimus Dorsi","Rhomboids"],["Biceps Brachii","Trapezius"],["Erector Spinae"],
   ["Lower Back","Shoulder"],["Low Back Pain"], {"deadlift_ratio":0.6}, [], ["bb_bent_over_row_001"], [], "rack"),
ex("anderson_squat_001","Anderson Squat (From Pins)","Squat","Squat",3,"Intermediate","Power Rack",5,
   ["Quadriceps","Gluteus Maximus"],["Erector Spinae"],["Core"],
   ["Knee","Lower Back"],["Low Back Pain","Patellar Tendon"], {"squat_ratio":0.7}, ["heavy_quarter_squat_001"], ["rack_split_squat_001"], [], "rack"),
ex("high_rack_pull_001","High Rack Pull (Above Knee)","Hinge","Hinge",4,"Advanced","Power Rack",5,
   ["Erector Spinae","Trapezius"],["Gluteus Maximus","Forearm Flexors"],["Core"],
   ["Lower Back"],["Low Back Pain"], {"deadlift_ratio":1.2}, [], ["rack_pull_below_knee_001"], [], "rack"),
ex("bottom_up_pin_bench_001","Bottom-Up Pin Bench (Chest Level)","Horizontal Push","Push",4,"Advanced","Power Rack",5,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"bench_ratio":0.9}, [], ["pin_bench_mid_001"], [], "rack"),
ex("heavy_quarter_squat_001","Heavy Quarter Squat (From J-Cups)","Squat","Squat",4,"Advanced","Power Rack",5,
   ["Quadriceps"],["Gluteus Maximus"],["Erector Spinae","Core"],
   ["Knee","Lower Back"],["Patellar Tendon","Low Back Pain"], {"squat_ratio":1.1}, [], ["anderson_squat_001"], [], "rack"),
ex("deficit_pin_press_001","Deficit Pin Press","Horizontal Push","Push",4,"Advanced","Power Rack",5,
   ["Pectoralis Major","Triceps Brachii"],["Anterior Deltoid"],["Core"],
   ["Shoulder","Elbow"],["Shoulder Instability"], {"bench_ratio":0.8}, [], ["bottom_up_pin_bench_001"], [], "rack"),
]

print("Total new exercises:", len(NEW))

# ---- de-dup guard ----
ids = [e["id"] for e in NEW]
dupes = {i for i in ids if ids.count(i) > 1}
assert not dupes, f"duplicate ids in NEW: {dupes}"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.core.config import settings

OUTPUT_PATH = settings.DATA_DIR / "new_exercises.json"
with open(OUTPUT_PATH, "w") as f:
    json.dump(NEW, f, indent=2)

print(f"Wrote {len(NEW)} exercises to {OUTPUT_PATH}")
