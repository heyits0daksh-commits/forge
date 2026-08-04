"""
Injury taxonomy — v5.0 comprehensive musculoskeletal injury library.

WHAT THIS FILE IS
Maps specific, named injuries (as a user would actually describe their
problem, e.g. "ACL Tear - Grade 3 (Complete Rupture)") to structured metadata
used to filter/adapt exercise prescription: which joint it affects, how
severe it is, what to avoid, what progression/return-to-sport looks like,
and so on.

BACKWARD COMPATIBILITY (v3.0 -> v4.0 -> v5.0)
The engine (backend/main.py, backend/services/knowledge_graph.py) has only
ever read two keys off each entry: `entry["joint"]` and `entry["severity"]`.
That contract is unchanged here — every entry, old or new, still carries
those two keys with the same meaning and the same 1/2/3 severity scale, so
nothing downstream needs to change. Everything else below (~28 extra fields
per entry) is additive: richer reference/decision-support data that the
current engine doesn't read yet, but that a future UI, rehab-candidacy
scorer, or clinician-facing view can.

SEVERITY TIERS (unchanged from v4.0)
    3 = Severe   — structural failure: complete ruptures/tears, dislocations,
                   fractures, advanced collapse, cord/nerve involvement. The
                   joint cannot be trusted under any real load. Every
                   exercise stressing this joint is excluded outright.
    2 = Moderate — partial tears, subluxation, Grade 2 sprains, marginal/
                   displaced fractures. Light, controlled work only
                   (difficulty 3+ excluded).
    1 = Mild     — Grade 1 sprains/strains, fraying, early degeneration,
                   stable injuries. Most training tolerated; only the
                   highest-demand movements (difficulty 4+) excluded.

EXTENSIBILITY
The requirement driving this file's structure is that new injuries, new
exercises, and new movement patterns must be addable *without touching the
core decision engine* (classify_injury_risk / find_alternatives / main.py).
That's achieved two ways:
  1. Every field beyond joint/severity is inert as far as the engine is
     concerned — adding fields, or whole new injuries, never changes how
     filtering behaves unless main.py is explicitly updated to read them.
  2. Large, structurally repetitive families (muscle strains across every
     major muscle group, ligament sprains across every major joint, tendon
     injuries across every major tendon) are generated from small data
     tables (MUSCLE_GROUPS, LIGAMENTS, TENDONS below) plus a builder
     function, rather than hand-duplicated. Adding a new muscle/ligament/
     tendon to those tables — or a new named condition to
     NAMED_CONDITIONS — is the entire diff needed to add a fully-specified
     injury entry.

`joint` values are deliberately kept aligned with the joint_stress vocabulary
already used in exercises.json (Wrist, Elbow, Shoulder, Neck, Lower Back,
Hip, Knee, Ankle) — those are the only 8 tags exercises.json actually carries
— so no changes to exercises.json are required. Injuries whose tissue doesn't
map to one of those 8 1:1 (e.g. thoracic spine, TMJ, forearm compartments)
are assigned the closest functionally-relevant tag; this is noted per entry
via the `region` field, which is free-text and carries the real anatomical
detail the 8-tag `joint` field can't.

CLINICAL DISCLAIMER
This is a *programming heuristic layer* for an exercise-prescription app —
it is not a diagnostic tool and isn't a substitute for evaluation by a
qualified clinician (physician, physical therapist, athletic trainer). Field
content (healing phases, red flags, return-to-sport criteria, etc.) reflects
general, widely-taught rehabilitation principles for each injury category,
not an individualized medical assessment. Anyone with a suspected injury —
especially anything flagged severity 3 or listed under `clinical_red_flags`
— should be directed to seek appropriate medical evaluation before an
exercise program (including one FORGE generates) is treated as clearance to
train.
"""

from typing import Dict, List, Optional

# ============================================================================
# SCHEMA
# ============================================================================
# Every entry in INJURY_TAXONOMY carries these keys. `joint` and `severity`
# are load-bearing for the engine; everything else is reference/decision-
# support metadata.
INJURY_FIELDS = [
    "name", "alt_names", "tissue", "joint", "region", "severity",
    "severity_grades", "healing_phases", "pain_pattern", "mechanism",
    "movement_restrictions", "joint_position_restrictions", "rom_restrictions",
    "loading_restrictions", "velocity_restrictions", "impact_restrictions",
    "technical_faults_to_avoid", "biomechanical_stresses_to_avoid",
    "muscles_to_protect", "muscles_to_strengthen", "safe_movement_patterns",
    "contraindicated_movement_patterns", "exercise_modifications",
    "progression_criteria", "regression_criteria", "return_to_sport_criteria",
    "absolute_contraindications", "relative_contraindications",
    "clinical_red_flags", "risk_score_logic",
]


# ============================================================================
# DIFFICULTY CEILING (unchanged from v4.0) — an exercise whose difficulty
# exceeds the ceiling for a joint the user has flagged is excluded. Severity
# 3 has no ceiling (None = block every difficulty, i.e. avoid the joint
# entirely).
# ============================================================================
SEVERITY_DIFFICULTY_CEILING = {
    1: 3,     # mild: only the top two difficulty tiers (4, 5) are excluded
    2: 2,     # moderate: only light/rehab-level work (1-2) is allowed
    3: None,  # severe: joint is excluded outright, no difficulty is safe
}


# ==========================================================================
# INJURY INTELLIGENCE — four-tier risk model (v4.0, unchanged)
# ==========================================================================
RiskTier = str  # Literal["safe", "caution", "high_risk", "contraindicated"]


def classify_injury_risk(severity: int, difficulty: int) -> RiskTier:
    """Classify how risky a given exercise difficulty is for a joint injury of
    the given severity tier. Pure function of the same two numbers the v3.0
    ceiling check already used, so the allowed/excluded boundary is identical
    to before — this only subdivides each side of that boundary into two."""
    if severity >= 3:
        return "contraindicated"

    ceiling = SEVERITY_DIFFICULTY_CEILING.get(severity)
    if ceiling is None:
        return "contraindicated"

    if difficulty <= ceiling - 1:
        return "safe"
    if difficulty == ceiling:
        return "caution"
    if difficulty == ceiling + 1:
        return "high_risk"
    return "contraindicated"


def find_alternatives(
    exercise: dict,
    all_exercises: Dict[str, dict],
    injury_joint_severity: Dict[str, int],
    max_results: int = 3,
    user_equipment: Optional[set] = None,
) -> List[dict]:
    """When an exercise is excluded on injury grounds, don't just say no —
    point at exercises that cover the same movement pattern / category without
    loading the joint(s) that got it excluded. Live search over the database,
    not a hand-authored per-exercise alternatives list.

    Preference order:
      1. An exercise the data already declares as an alternative/regression
         of this one, if it clears the joint check.
      2. Any other exercise sharing this one's movement_pattern (or failing
         that, its category) that clears the joint check, ranked by pattern
         match, then whether the person actually has the equipment for it,
         then difficulty.

    `user_equipment` (lower-cased equipment strings the person has available)
    is optional so every existing caller keeps working unchanged. When
    provided, an alternative the person can actually do right now (e.g. a
    Belt Squat swap for a barbell squat, when they have a belt squat) is
    ranked ahead of an equally-valid one they'd need to buy new equipment
    for — a "safe" alternative nobody can act on isn't actually useful. Both
    are still returned if there's room; this only affects ordering, not
    what's included.
    """
    ex_id = exercise.get("id")
    pattern = exercise.get("movement_pattern")
    category = exercise.get("category")

    def clears_joints(candidate: dict) -> bool:
        for j in candidate.get("joint_stress", []):
            severity = injury_joint_severity.get(j)
            if severity is None:
                continue
            if classify_injury_risk(severity, candidate.get("difficulty", 1)) in ("high_risk", "contraindicated"):
                return False
        return True

    def equipment_tier(candidate: dict) -> int:
        """0 = a dedicated piece of equipment the person actually owns (e.g.
        Belt Squat) - the strongest possible swap, since it lets them keep
        training the pattern loaded rather than dropping to bodyweight.
        1 = bodyweight (always available, but a step down in training
        stimulus from what they were doing). 2 = equipment they don't have.
        Without this, a low-difficulty bodyweight version always outranked
        an owned dedicated substitute purely because "difficulty" sorts
        ascending - which is backwards when the whole point of asking about
        available equipment is that a Belt Squat swap is what they'd
        actually want offered first."""
        if user_equipment is None:
            return 0
        eq = candidate.get("equipment", "Bodyweight").lower()
        if eq != "bodyweight" and eq in user_equipment:
            return 0
        if eq == "bodyweight":
            return 1
        return 2

    declared: List[dict] = []
    seen = set()

    declared_ids = list(exercise.get("alternatives", [])) + list(exercise.get("regressions", []))
    for cand_id in declared_ids:
        cand = all_exercises.get(cand_id)
        if cand and cand_id not in seen and clears_joints(cand):
            declared.append(cand)
            seen.add(cand_id)
    # Declared alternatives were previously left in raw data order - sorted
    # here too so an owned dedicated substitute (e.g. Belt Squat) still
    # outranks a declared-but-generic bodyweight option instead of only the
    # fallback pool below getting equipment-aware ordering.
    declared.sort(key=lambda c: (equipment_tier(c), c.get("difficulty", 1)))
    candidates: List[dict] = list(declared)

    if len(candidates) < max_results:
        pool = [
            c for cid, c in all_exercises.items()
            if cid != ex_id
            and cid not in seen
            and (c.get("movement_pattern") == pattern or c.get("category") == category)
            and clears_joints(c)
        ]
        pool.sort(key=lambda c: (
            c.get("movement_pattern") != pattern,
            equipment_tier(c),
            c.get("difficulty", 1),
        ))
        candidates.extend(pool)

    return candidates[:max_results]


def _risk_note(severity: int, joint: str) -> str:
    ceiling = SEVERITY_DIFFICULTY_CEILING.get(severity)
    return (
        f"Severity {severity}/3 on '{joint}' -> difficulty ceiling "
        f"{ceiling if ceiling is not None else 'none (joint excluded outright)'}; "
        f"classify_injury_risk() applies the standard four-tier model to any "
        f"exercise whose joint_stress includes '{joint}'."
    )


def _phases(tissue: str) -> List[str]:
    return {
        "Muscle": [
            "Acute/inflammatory (0-72h): protect from further tearing, manage pain/swelling, gentle pain-free motion.",
            "Proliferative/repair (~3 days-3 weeks): progressive pain-free ROM, isometrics -> light isotonics.",
            "Remodeling/strengthening (~3-8+ weeks, longer for Grade III): progressive loading toward pre-injury capacity, then eccentrics/plyometrics.",
        ],
        "Ligament": [
            "Acute (0-1 week): protect the joint, control swelling, gentle protected ROM.",
            "Proliferative (~1-6 weeks): progressive ROM, proprioception/balance work, light resistance.",
            "Remodeling (~6 weeks-6+ months, longer if surgical): progressive loading, sport-specific stability and reactive work.",
        ],
        "Tendon": [
            "Reactive/acute (0-2 weeks): load management, isometrics for pain modulation.",
            "Dysrepair (~2-6 weeks): heavy slow resistance introduced cautiously, monitor 24h pain response.",
            "Degenerative/remodeling (~6 weeks-6+ months): progressive tendon loading, energy-storage/plyometric reintroduction.",
        ],
        "Bone": [
            "Inflammatory (0-1 week): protect, offload per fracture/stress-injury stability.",
            "Soft callus (~1-4 weeks): protected/partial weight-bearing progression per clinical guidance.",
            "Hard callus/remodeling (~4-12+ weeks): progressive loading as imaging/clinical status allows.",
        ],
        "Joint": [
            "Acute/protective phase: control swelling and pain, protect the joint from provocative positions.",
            "Motion & light-loading phase: restore ROM, begin light closed-chain and stability work.",
            "Progressive loading & return-to-activity phase: rebuild strength/power specific to the joint's demands.",
        ],
        "Cartilage": [
            "Acute/protective phase: offload per weight-bearing status, control effusion.",
            "Progressive loading phase: closed-chain loading introduced gradually, monitor for reactive swelling.",
            "Return-to-activity phase: sport/task-specific loading once pain- and effusion-free.",
        ],
        "Spine": [
            "Acute (0-2 weeks): relative rest from provocative positions, pain-modulating movement, avoid prolonged static postures.",
            "Sub-acute (~2-6 weeks): progressive mobility and motor-control (core/segmental stability) work.",
            "Remodeling (~6 weeks+): progressive loading, capacity-building for sport/occupational demand.",
        ],
        "Nerve": [
            "Acute irritation phase: reduce compressive/tensile load on the nerve, address contributing posture/positions.",
            "Desensitization & gliding phase: nerve-gliding/flossing, graded exposure to provocative positions.",
            "Progressive loading & functional phase: rebuild strength/endurance in the affected distribution.",
        ],
        "Fascia": [
            "Acute (0-2 weeks): reduce provocative loading, address contributing mechanical factors.",
            "Sub-acute (~2-6 weeks): progressive loading, soft-tissue and mobility work.",
            "Remodeling (~6 weeks+): progressive return to full activity/impact loading.",
        ],
    }.get(tissue, [
        "Acute/protective phase.",
        "Progressive loading phase.",
        "Return-to-activity phase.",
    ])


def _generic_pain(severity: int, label: str) -> str:
    return {
        1: f"Mild, often intermittent pain related to {label}; typically activity-related, resolves with rest.",
        2: f"Moderate, more consistent pain related to {label}; functional limitation present, may include swelling/instability.",
        3: f"Severe pain and/or significant functional loss related to {label}; may include instability, deformity, or neurological symptoms.",
    }[severity]


def _generic_restrictions(severity: int, target: str) -> str:
    return {
        1: f"Avoid the highest-demand loading/positions for the {target} until asymptomatic; most other training tolerated.",
        2: f"Avoid moderate-to-high loading and end-range positions for the {target}; light, controlled work only.",
        3: f"Avoid loading the {target} in any capacity until medically cleared.",
    }[severity]


# ============================================================================
# LEGACY ENTRIES (v3.0/v4.0) — names, joints, and severities unchanged.
# Enriched here with the full field set via generic, severity-driven
# defaults rather than hand-authored per-entry prose, since the specific
# clinical detail already lives in each name (grade, mechanism, structure).
# ============================================================================
_LEGACY = {
    # WRIST
    "Wrist Loose Bodies": {"joint": "Wrist", "severity": 1},
    "TFCC Tear - Class 1 Type A (Central Perforation)": {"joint": "Wrist", "severity": 2},
    "TFCC Tear - Class 1 Type B/C (Torn from Bone)": {"joint": "Wrist", "severity": 2},
    "TFCC Tear - Class 2 (Degenerative)": {"joint": "Wrist", "severity": 1},
    "Scapholunate Ligament Tear - Grade I (Mild Stretch)": {"joint": "Wrist", "severity": 1},
    "Scapholunate Ligament Tear - Grade II (Partial Tear)": {"joint": "Wrist", "severity": 2},
    "Scapholunate Ligament Tear - Grade III (Advanced Tear)": {"joint": "Wrist", "severity": 2},
    "Scapholunate Ligament Tear - Grade IV (Complete Tear)": {"joint": "Wrist", "severity": 3},
    "SLAC Wrist (Scapholunate Advanced Collapse)": {"joint": "Wrist", "severity": 3},
    "Perilunate Dislocation": {"joint": "Wrist", "severity": 3},
    # ELBOW
    "Elbow Ligament Sprain (MCL/LUCL) - Grade 1": {"joint": "Elbow", "severity": 1},
    "Elbow Ligament Sprain (MCL/LUCL) - Grade 2": {"joint": "Elbow", "severity": 2},
    "Elbow Ligament Sprain (MCL/LUCL) - Grade 3 (Complete Rupture)": {"joint": "Elbow", "severity": 3},
    "Radial Head Fracture - Type I (Non-Displaced)": {"joint": "Elbow", "severity": 2},
    "Radial Head Fracture - Type II (Displaced)": {"joint": "Elbow", "severity": 2},
    "Radial Head Fracture - Type III (Comminuted)": {"joint": "Elbow", "severity": 3},
    "Radial Head Fracture - Type IV (Fracture-Dislocation)": {"joint": "Elbow", "severity": 3},
    "Osteochondritis Dissecans (OCD) / Elbow Loose Bodies": {"joint": "Elbow", "severity": 2},
    "Distal Biceps Tendon Rupture": {"joint": "Elbow", "severity": 3},
    "LUCL Tear (Posterolateral Rotator Instability)": {"joint": "Elbow", "severity": 3},
    "Simple Elbow Dislocation": {"joint": "Elbow", "severity": 3},
    "Elbow Fracture-Dislocation": {"joint": "Elbow", "severity": 3},
    # SPINE / NECK / LOWER BACK
    "Severe Spinal Stenosis / Osteophyte Locking": {"joint": "Lower Back", "severity": 1},
    "Cervical Facet Injury - Stage 1 (Distraction Instability)": {"joint": "Neck", "severity": 1},
    "Cervical Facet Injury - Stage 2 (Unilateral Subluxation)": {"joint": "Neck", "severity": 2},
    "Cervical Facet Injury - Stage 3 (Bilateral Dislocation)": {"joint": "Neck", "severity": 3},
    "Lumbar Fracture - Stable (One Column)": {"joint": "Lower Back", "severity": 2},
    "Lumbar Fracture - Unstable (Two/Three Column)": {"joint": "Lower Back", "severity": 3},
    "Massive Central Disc Herniation": {"joint": "Lower Back", "severity": 3},
    "Unstable Spondylolisthesis / Facet Dislocation": {"joint": "Lower Back", "severity": 3},
    "Burst Fracture (Spine)": {"joint": "Lower Back", "severity": 3},
    "Fracture-Dislocation with Spinal Cord Injury": {"joint": "Lower Back", "severity": 3},
    "Spinal Cord Injury - ASIA Grade D/E (Mild Incomplete/Normal)": {"joint": "Lower Back", "severity": 2},
    "Spinal Cord Injury - ASIA Grade A/B/C (Severe/Complete)": {"joint": "Lower Back", "severity": 3},
    # KNEE - Ligament
    "ACL/Ligament Sprain - Grade 1 (Mild)": {"joint": "Knee", "severity": 1},
    "ACL/Ligament Tear - Grade 2 (Partial Tear)": {"joint": "Knee", "severity": 2},
    "ACL/Ligament Tear - Grade 3 (Complete Rupture)": {"joint": "Knee", "severity": 3},
    # KNEE - Meniscus
    "Meniscus Tear - Grade 1 (Early Fraying)": {"joint": "Knee", "severity": 1},
    "Meniscus Tear - Grade 2 (Deep Linear Tear)": {"joint": "Knee", "severity": 2},
    "Meniscus Tear - Grade 3 (True Structural Tear)": {"joint": "Knee", "severity": 3},
    # KNEE - Patella / loose bodies
    "Patellar Dislocation - Acute (First-Time)": {"joint": "Knee", "severity": 3},
    "Patellar Dislocation - Chronic Recurrent": {"joint": "Knee", "severity": 2},
    "Knee Loose Bodies - Stable/Non-Obstructive": {"joint": "Knee", "severity": 1},
    "Knee Loose Bodies - Unstable/Obstructive": {"joint": "Knee", "severity": 2},
    # ANKLE
    "Lateral Ankle Sprain - Grade 1 (Mild)": {"joint": "Ankle", "severity": 1},
    "Lateral Ankle Sprain - Grade 2 (Partial Tear)": {"joint": "Ankle", "severity": 2},
    "Lateral Ankle Sprain - Grade 3 (Complete Rupture)": {"joint": "Ankle", "severity": 3},
    "High Ankle Sprain (Syndesmosis Tear)": {"joint": "Ankle", "severity": 3},
    "Peroneal Tendon Subluxation": {"joint": "Ankle", "severity": 2},
    "Osteochondral Lesion / Ankle Loose Bodies": {"joint": "Ankle", "severity": 1},
    "Ankle Fracture - Weber Type A (Stable)": {"joint": "Ankle", "severity": 1},
    "Ankle Fracture - Weber Type B (Variable Stability)": {"joint": "Ankle", "severity": 2},
    "Ankle Fracture - Weber Type C (Highly Unstable)": {"joint": "Ankle", "severity": 3},
    "Ankle Fracture-Dislocation": {"joint": "Ankle", "severity": 3},
    # HIP
    "Snapping Hip Syndrome": {"joint": "Hip", "severity": 1},
    "Hip Labral Tear - Grade 1 (Fraying)": {"joint": "Hip", "severity": 1},
    "Hip Labral Tear - Grade 2 (Partial Tear)": {"joint": "Hip", "severity": 2},
    "Hip Labral Tear - Grade 3 (Complete Avulsion)": {"joint": "Hip", "severity": 3},
    "Avascular Necrosis (Hip) - Stage I/II": {"joint": "Hip", "severity": 1},
    "Avascular Necrosis (Hip) - Stage III/IV (Collapse)": {"joint": "Hip", "severity": 3},
    "Hip Dislocation - Grade 1 (Simple)": {"joint": "Hip", "severity": 3},
    "Hip Dislocation - Grade 2-4 (With Fracture)": {"joint": "Hip", "severity": 3},
    "Femoral Neck / Acetabular Fracture": {"joint": "Hip", "severity": 3},
    # SHOULDER
    "Shoulder Instability - Grade 1 (Micro-instability)": {"joint": "Shoulder", "severity": 1},
    "Shoulder Subluxation - Grade 2": {"joint": "Shoulder", "severity": 2},
    "Shoulder Dislocation - Grade 3 (Anterior, First-Time)": {"joint": "Shoulder", "severity": 3},
    "Shoulder Dislocation - Posterior or Chronic Anterior": {"joint": "Shoulder", "severity": 3},
    "Bony Bankart Lesion": {"joint": "Shoulder", "severity": 3},
    "SLAP Tear - Type I (Frayed)": {"joint": "Shoulder", "severity": 1},
    "SLAP Tear - Type II (Detached)": {"joint": "Shoulder", "severity": 2},
    "SLAP Tear - Type III/IV (Bucket-Handle Flap)": {"joint": "Shoulder", "severity": 3},
    "Rotator Cuff Tear - Small (<1cm)": {"joint": "Shoulder", "severity": 1},
    "Rotator Cuff Tear - Medium (1-3cm)": {"joint": "Shoulder", "severity": 2},
    "Rotator Cuff Tear - Large (3-5cm)": {"joint": "Shoulder", "severity": 2},
    "Rotator Cuff Tear - Massive (>5cm, Retracted)": {"joint": "Shoulder", "severity": 3},
    "Adhesive Capsulitis (Frozen Shoulder)": {"joint": "Shoulder", "severity": 2},
}


def _enrich_legacy(name: str, joint: str, severity: int) -> dict:
    label = name.lower()
    return {
        "name": name,
        "alt_names": [],
        "tissue": "Musculoskeletal (see name for specific structure)",
        "joint": joint,
        "region": joint,
        "severity": severity,
        "severity_grades": "Grade/type is encoded in the injury name; severity tier below is this system's 1 (mild) - 3 (severe) load-tolerance model, not a separate clinical grading scale.",
        "healing_phases": _phases("Joint"),
        "pain_pattern": _generic_pain(severity, label),
        "mechanism": "Mechanism is specific to this diagnosis — refer to clinical literature for the named structure/grade.",
        "movement_restrictions": _generic_restrictions(severity, joint.lower()),
        "joint_position_restrictions": f"Avoid end-range/provocative positions of the {joint.lower()} associated with this injury.",
        "rom_restrictions": "Pain-free ROM only until re-evaluated; avoid forcing ROM into a symptomatic range." if severity < 3 else "ROM work is clinician-directed only.",
        "loading_restrictions": {1: "Light-to-moderate loading tolerated if pain-free.", 2: "Light, controlled loading only.", 3: "No loading until medically cleared."}[severity],
        "velocity_restrictions": "Avoid high-velocity/ballistic loading of the joint until cleared." if severity > 1 else "Avoid maximal-velocity efforts until asymptomatic.",
        "impact_restrictions": "Avoid impact loading (running, jumping, cutting/pivoting) on the joint until cleared." if severity > 1 else "Impact tolerated in moderation if pain-free.",
        "technical_faults_to_avoid": ["Loading through pain", "Skipping graded-exposure progression", "Ignoring swelling/symptom flare after loading"],
        "biomechanical_stresses_to_avoid": [f"High shear/compressive/rotational load through the {joint.lower()}"],
        "muscles_to_protect": [],
        "muscles_to_strengthen": [f"Stabilizing musculature around the {joint.lower()}"],
        "safe_movement_patterns": ["Pain-free, controlled ROM within the current tolerance"],
        "contraindicated_movement_patterns": ["High-load/high-velocity/end-range movement at this joint"] if severity > 1 else ["Maximal-effort loading at this joint"],
        "exercise_modifications": ["Reduce ROM/load and rebuild gradually", "Substitute exercises that don't stress this joint while symptomatic"],
        "progression_criteria": ["Pain-free through current ROM/load", "No swelling or symptom flare 24h post-session", "Clinician sign-off for severity 2-3 before advancing"],
        "regression_criteria": ["Pain or swelling returns/increases with current loading", "Loss of ROM or strength versus prior session"],
        "return_to_sport_criteria": ["Full, pain-free ROM and strength symmetric to the uninjured side", "Sport-specific movement tolerated at full intensity without symptoms", "Clinician/PT clearance for severity 2-3"],
        "absolute_contraindications": ["Loading through sharp/mechanical pain", "Training through instability, locking, or giving-way episodes"],
        "relative_contraindications": ["High training volume/frequency before symptom resolution"],
        "clinical_red_flags": ["Neurovascular compromise (numbness, pallor, pulselessness)", "Joint locking or true instability/giving-way", "Signs of fracture or dislocation", "Progressive neurological symptoms"],
        "risk_score_logic": _risk_note(severity, joint),
    }


# ============================================================================
# MUSCLE STRAINS — generated across every major muscle group (v5.0 addition)
# ============================================================================
MUSCLE_GROUPS = [
    ("Neck Muscles (Sternocleidomastoid/Scalenes)", "Neck", "Anterior/Lateral Neck"),
    ("Trapezius", "Neck", "Neck/Upper Back"),
    ("Levator Scapulae", "Neck", "Neck/Upper Back"),
    ("Deltoids", "Shoulder", "Shoulder"),
    ("Rotator Cuff Muscles", "Shoulder", "Shoulder"),
    ("Pectoralis Major", "Shoulder", "Chest"),
    ("Pectoralis Minor", "Shoulder", "Chest"),
    ("Serratus Anterior", "Shoulder", "Chest/Scapula"),
    ("Latissimus Dorsi", "Shoulder", "Upper Back"),
    ("Rhomboids", "Shoulder", "Upper Back"),
    ("Erector Spinae", "Lower Back", "Spine"),
    ("Multifidus", "Lower Back", "Lumbar Spine"),
    ("Quadratus Lumborum", "Lower Back", "Lumbar Spine"),
    ("Rectus Abdominis", "Lower Back", "Abdomen/Core"),
    ("Obliques", "Lower Back", "Abdomen/Core"),
    ("Transverse Abdominis", "Lower Back", "Abdomen/Core"),
    ("Hip Flexors", "Hip", "Anterior Hip"),
    ("Iliopsoas", "Hip", "Anterior Hip/Deep"),
    ("Gluteus Maximus", "Hip", "Hip/Glute"),
    ("Gluteus Medius", "Hip", "Hip/Glute"),
    ("Gluteus Minimus", "Hip", "Hip/Glute"),
    ("Tensor Fasciae Latae (TFL)", "Hip", "Lateral Hip"),
    ("Piriformis", "Hip", "Deep Hip/Glute"),
    ("Adductors", "Hip", "Groin/Inner Thigh"),
    ("Abductors", "Hip", "Lateral Hip/Thigh"),
    ("Quadriceps", "Knee", "Anterior Thigh"),
    ("Hamstrings", "Knee", "Posterior Thigh"),
    ("Gastrocnemius", "Ankle", "Calf"),
    ("Soleus", "Ankle", "Calf (deep)"),
    ("Tibialis Anterior", "Ankle", "Shin"),
    ("Tibialis Posterior", "Ankle", "Deep Calf/Shin"),
    ("Peroneals", "Ankle", "Lateral Lower Leg"),
    ("Forearm Flexors", "Wrist", "Forearm (volar)"),
    ("Forearm Extensors", "Wrist", "Forearm (dorsal)"),
    ("Biceps", "Elbow", "Upper Arm (anterior)"),
    ("Triceps", "Elbow", "Upper Arm (posterior)"),
    ("Wrist Muscles", "Wrist", "Wrist"),
    ("Intrinsic Hand Muscles", "Wrist", "Hand"),
    ("Foot Intrinsic Muscles", "Ankle", "Foot"),
]

_STRAIN_LABEL = {1: "Grade I Strain (Mild)", 2: "Grade II Strain (Partial Tear)", 3: "Grade III Tear (Complete Rupture)"}
_STRAIN_ALT = {1: "Pull", 2: "Partial Tear", 3: "Complete Tear/Rupture"}


def _muscle_strain(muscle: str, joint: str, region: str, grade: int) -> dict:
    m = muscle.lower()
    pain = {
        1: f"Mild, localized soreness in the {m} during or shortly after activity; no significant strength loss, minimal swelling.",
        2: f"Moderate, well-localized pain with palpable tenderness in the {m}; noticeable strength loss, swelling/bruising common.",
        3: f"Sudden, severe pain often described as a 'pop' or tearing sensation in the {m}; marked strength loss, possible palpable defect, significant swelling/bruising.",
    }[grade]
    loading = {
        1: "Light-to-moderate isotonic loading tolerated once pain-free.",
        2: "Isometrics progressing to light isotonic loading only; avoid end-range eccentrics.",
        3: "No loading until cleared by a clinician; rehab loading thereafter is clinician-directed.",
    }[grade]
    prog = {
        1: ["Full pain-free active ROM", "No pain with isometric resistance", "No pain with functional movement at low intensity"],
        2: ["Full pain-free passive and active ROM", "Isometric strength ~80%+ of uninjured side", "Pain-free light functional loading"],
        3: ["Clinician clearance (with imaging follow-up as indicated)", "Progressive rehab-supervised strength restoration", "Pain-free full ROM before any resisted work resumes"],
    }[grade]
    rts = {
        1: ["Full, pain-free ROM and strength symmetric to the uninjured side", "No pain with sport-specific movement at full intensity"],
        2: ["Strength >=90% of uninjured side on objective testing", "Pain-free through sport-specific speed/agility work", "No apprehension with high-velocity or eccentric demand"],
        3: ["Clinician/physical therapist sign-off", "Strength and functional (hop/throw/lift) testing symmetric to uninjured side", "Full pain-free sport-specific movement at competition intensity"],
    }[grade]
    return {
        "name": f"{muscle} Strain - {_STRAIN_LABEL[grade]}",
        "alt_names": [f"{muscle} {_STRAIN_ALT[grade]}"],
        "tissue": "Muscle",
        "joint": joint,
        "region": region,
        "severity": grade,
        "severity_grades": "Grade I (mild, minimal fiber disruption) / Grade II (moderate, partial tear) / Grade III (severe, complete rupture) — standard muscle strain grading.",
        "healing_phases": _phases("Muscle"),
        "pain_pattern": pain,
        "mechanism": f"Sudden eccentric overload, forceful/ballistic contraction, or overstretch of the {m}.",
        "movement_restrictions": {
            1: f"Avoid maximal-effort or ballistic use of the {m} for 1-2 weeks; keep loaded work pain-free.",
            2: f"Avoid resisted and eccentric loading of the {m} until pain-free through full ROM; no ballistic/plyometric use.",
            3: f"Avoid all loading of the {m} until medically cleared; protected motion/immobilization may be indicated early on.",
        }[grade],
        "joint_position_restrictions": f"Avoid end-range lengthened positions of the {m} under load until healing progresses.",
        "rom_restrictions": "Pain-free active ROM only in the acute phase; avoid stretching into pain until subacute (Grade I/II) or clinician-cleared (Grade III).",
        "loading_restrictions": loading,
        "velocity_restrictions": "Avoid ballistic/high-velocity contraction until strength and pain-free ROM are restored." if grade > 1 else "Avoid maximal-velocity efforts for 1-2 weeks.",
        "impact_restrictions": "Avoid impact activity that loads this muscle (running, jumping, cutting) until pain-free strength is restored.",
        "technical_faults_to_avoid": ["Loading through pain / compensating with poor form", "Skipping the isometric -> isotonic -> eccentric progression", "Returning to ballistic work before strength symmetry is confirmed"],
        "biomechanical_stresses_to_avoid": [f"Rapid eccentric loading of the {m}", "Overstretching into end-range under load"],
        "muscles_to_protect": [muscle],
        "muscles_to_strengthen": [muscle, "surrounding synergists and antagonists for balanced loading"],
        "safe_movement_patterns": ["Pain-free isometric holds", "Controlled, short-range isotonic work with gradual load progression"],
        "contraindicated_movement_patterns": ["Ballistic/plyometric use of the muscle", "Maximal eccentric loading", "End-range stretching under load"] if grade > 1 else ["Maximal-effort ballistic use of the muscle"],
        "exercise_modifications": ["Reduce range/load and rebuild via isometrics -> isotonics -> eccentrics -> plyometrics", "Substitute exercises that don't stress this muscle group while it heals"],
        "progression_criteria": prog,
        "regression_criteria": ["Return/increase of pain with current loading", "Loss of strength or ROM versus the prior session", "Swelling or bruising recurs"],
        "return_to_sport_criteria": rts,
        "absolute_contraindications": ["Loading through sharp/tearing pain", "Return to sport before functional symmetry testing (Grade II/III)"] if grade > 1 else ["Loading through sharp pain"],
        "relative_contraindications": ["High-volume ballistic training before full strength is restored", "Training this muscle to failure in early rehab"],
        "clinical_red_flags": [
            "Sudden severe pain with a palpable gap/defect (possible complete rupture) — refer for imaging.",
            "Signs of compartment syndrome (severe pain out of proportion, tense swelling, numbness, pallor) — emergency referral.",
            "Inability to voluntarily contract the muscle at all.",
        ],
        "risk_score_logic": _risk_note(grade, joint),
    }


# ============================================================================
# GENERAL MUSCLE CONDITIONS — non-grade-specific muscle injury types
# ============================================================================
def _muscle_condition(name: str, joint: str, region: str, severity: int, pain: str, mechanism: str, red_flags: List[str]) -> dict:
    return {
        "name": name, "alt_names": [], "tissue": "Muscle", "joint": joint, "region": region, "severity": severity,
        "severity_grades": "Not graded I-III; severity reflects functional impact using this system's 1 (mild)-3 (severe) model.",
        "healing_phases": _phases("Muscle"),
        "pain_pattern": pain, "mechanism": mechanism,
        "movement_restrictions": _generic_restrictions(severity, joint.lower()),
        "joint_position_restrictions": f"Avoid sustained or end-range positions that reproduce symptoms near the {region.lower()}.",
        "rom_restrictions": "Gentle pain-free ROM/stretching generally tolerated and often therapeutic; avoid forcing through sharp pain.",
        "loading_restrictions": {1: "Normal training tolerated with monitoring.", 2: "Reduce volume/intensity until symptoms settle.", 3: "Avoid loading until re-evaluated."}[severity],
        "velocity_restrictions": "No specific restriction beyond symptom-guided loading." if severity == 1 else "Avoid high-velocity/ballistic loading until symptoms settle.",
        "impact_restrictions": "Generally tolerated if asymptomatic." if severity == 1 else "Reduce impact loading until symptoms resolve.",
        "technical_faults_to_avoid": ["Ignoring early warning symptoms and continuing to overload the area", "Poor recovery/sleep/hydration compounding tissue irritability"],
        "biomechanical_stresses_to_avoid": ["Repetitive overload without adequate recovery", "Sudden spikes in training load"],
        "muscles_to_protect": [], "muscles_to_strengthen": ["General strength/conditioning of the affected region once symptoms allow"],
        "safe_movement_patterns": ["Light aerobic activity, mobility work, self-myofascial release as tolerated"],
        "contraindicated_movement_patterns": ["High-load training through unresolved symptoms"],
        "exercise_modifications": ["Reduce training load/volume", "Address contributing factors (load management, technique, recovery)"],
        "progression_criteria": ["Symptom resolution or return to baseline", "No recurrence with graded return to full training load"],
        "regression_criteria": ["Symptoms recur or worsen with current training load"],
        "return_to_sport_criteria": ["Full training tolerance without symptom recurrence"],
        "absolute_contraindications": [] if severity < 3 else ["Continuing to train through the acute presentation"],
        "relative_contraindications": ["Rapid return to prior training volume without a graded reintroduction"],
        "clinical_red_flags": red_flags,
        "risk_score_logic": _risk_note(severity, joint),
    }


_MUSCLE_CONDITIONS = [
    _muscle_condition("Muscle Contusion - Thigh", "Knee", "Thigh (quad/hamstring)", 2,
        "Localized pain, swelling, bruising following direct blunt trauma; pain with contraction and passive stretch.",
        "Direct blunt trauma (contact, collision, equipment impact) to the muscle belly.",
        ["Rapidly expanding swelling or severe pain out of proportion (possible compartment syndrome) — emergency referral.",
         "Progressive loss of knee flexion/extension ROM over days (myositis ossificans risk) — refer for evaluation."]),
    _muscle_condition("Muscle Contusion - Calf", "Ankle", "Calf", 2,
        "Localized pain, swelling, bruising following direct blunt trauma to the calf.",
        "Direct blunt trauma to the gastrocnemius/soleus.",
        ["Severe pain, tense swelling, numbness (possible compartment syndrome) — emergency referral."]),
    _muscle_condition("Muscle Contusion - Shoulder/Upper Arm", "Shoulder", "Shoulder/Upper Arm", 1,
        "Localized pain, swelling, bruising following direct blunt trauma.",
        "Direct blunt trauma (contact, fall, equipment impact).",
        ["Rapidly expanding swelling or severe pain out of proportion — refer for evaluation."]),
    _muscle_condition("Muscle Contusion - Forearm", "Wrist", "Forearm", 2,
        "Localized pain, swelling, bruising in the forearm following direct trauma.",
        "Direct blunt trauma to the forearm musculature.",
        ["Severe pain, tense swelling, numbness/tingling in the hand (possible compartment syndrome) — emergency referral."]),
    _muscle_condition("Muscle Spasm", "Lower Back", "Variable (commonly low back/neck)", 1,
        "Sudden, involuntary, painful muscle contraction; palpable tightness/knot.",
        "Overload, dehydration, fatigue, or protective response to underlying irritation.",
        ["Spasm accompanied by neurological symptoms (numbness, weakness) — refer for evaluation."]),
    _muscle_condition("Muscle Cramp", "Lower Back", "Variable (commonly calf/hamstring)", 1,
        "Sudden, brief, painful involuntary muscle contraction, usually during or after exertion.",
        "Fatigue, dehydration/electrolyte imbalance, or unaccustomed load.",
        ["Frequent/severe cramping with muscle weakness or dark urine (possible rhabdomyolysis) — urgent medical evaluation."]),
    _muscle_condition("Delayed Onset Muscle Soreness (DOMS)", "Lower Back", "Variable (whichever muscle group was loaded)", 1,
        "Diffuse, dull soreness peaking 24-72h after unaccustomed or high-eccentric-load exercise; resolves within a week.",
        "Unaccustomed eccentric loading or a sharp increase in training volume/intensity.",
        ["Severe swelling, dark urine, disproportionate pain (possible exertional rhabdomyolysis) — urgent medical evaluation."]),
    _muscle_condition("Myofascial Pain Syndrome / Trigger Points", "Neck", "Variable (commonly neck/upper back)", 1,
        "Localized deep, aching pain from a hyperirritable point in a taut muscle band; may refer pain to a predictable pattern.",
        "Repetitive strain, sustained postures, or unresolved muscle overload.",
        ["Progressive neurological symptoms rather than typical referred pain pattern — refer for evaluation."]),
    _muscle_condition("Chronic Muscle Tightness / Overuse Syndrome", "Lower Back", "Variable", 1,
        "Persistent tightness/stiffness with cumulative overload; may include mild ache with activity.",
        "Repetitive loading without adequate recovery over weeks to months.",
        ["Progressive weakness or symptoms unrelieved by rest and load management — refer for evaluation."]),
    _muscle_condition("Acute Compartment Syndrome - Anterior Leg", "Ankle", "Anterior Lower Leg", 3,
        "Severe pain out of proportion to injury, worsened by passive stretch of the compartment; tightness, paresthesia, and pallor may develop.",
        "Direct trauma, fracture, or rarely severe exertional overload causing intracompartmental pressure to rise.",
        ["This is a surgical emergency — the 5 P's (Pain out of proportion, Paresthesia, Pallor, Pulselessness, Paralysis) require IMMEDIATE emergency care, not exercise programming."]),
    _muscle_condition("Acute Compartment Syndrome - Deep Posterior Leg", "Ankle", "Deep Posterior Lower Leg", 3,
        "Severe pain out of proportion to injury, worsened by passive stretch of the toes; tightness and paresthesia in the sole.",
        "Direct trauma, fracture, or severe exertional overload.",
        ["Surgical emergency — immediate emergency care required; do not attempt to manage with exercise/rest alone."]),
    _muscle_condition("Chronic Exertional Compartment Syndrome - Anterior Leg", "Ankle", "Anterior Lower Leg", 2,
        "Predictable, reproducible tightness/aching pain that builds during exertion and resolves with rest, over weeks-months of training.",
        "Repetitive exertional loading (typically running) in a susceptible individual.",
        ["Symptoms that fail to resolve with rest, or develop suddenly and severely (possible acute conversion) — urgent evaluation."]),
]


# ============================================================================
# LIGAMENT SPRAINS — generated across major joints not already covered by
# name in the legacy set (v5.0 addition)
# ============================================================================
LIGAMENTS = [
    ("PCL", "Knee", "Knee (posterior)"),
    ("MCL", "Knee", "Knee (medial)"),
    ("LCL", "Knee", "Knee (lateral)"),
    ("MPFL", "Knee", "Knee (patellofemoral)"),
    ("ATFL", "Ankle", "Ankle (lateral)"),
    ("CFL", "Ankle", "Ankle (lateral)"),
    ("PTFL", "Ankle", "Ankle (lateral, deep)"),
    ("Deltoid Ligament", "Ankle", "Ankle (medial)"),
    ("AC Ligament", "Shoulder", "Shoulder (AC joint)"),
    ("Coracoclavicular Ligament", "Shoulder", "Shoulder (AC joint)"),
    ("Glenohumeral Ligaments", "Shoulder", "Shoulder (capsule)"),
    ("UCL", "Elbow", "Elbow (medial)"),
    ("RCL", "Elbow", "Elbow (lateral)"),
    ("Iliofemoral Ligament", "Hip", "Hip (anterior)"),
    ("Pubofemoral Ligament", "Hip", "Hip (anteroinferior)"),
    ("Ischiofemoral Ligament", "Hip", "Hip (posterior)"),
    ("Posterior Ligament Complex", "Lower Back", "Lumbar Spine"),
    ("Interspinous Ligaments", "Lower Back", "Lumbar Spine"),
    ("SI Joint Ligaments", "Hip", "Sacroiliac Joint"),
]


def _ligament_sprain(ligament: str, joint: str, region: str, grade: int) -> dict:
    lg = ligament.lower()
    label = {1: "Grade I Sprain (Mild)", 2: "Grade II Sprain (Partial Tear)", 3: "Grade III Sprain (Complete Rupture)"}[grade]
    pain = {
        1: f"Mild pain/tenderness over the {lg} with minimal swelling; no instability.",
        2: f"Moderate pain and swelling over the {lg}; mild-to-moderate laxity on stress testing, some functional loss.",
        3: f"Significant pain (may paradoxically be less if the ligament is fully torn), marked swelling, and frank instability on stress testing.",
    }[grade]
    return {
        "name": f"{ligament} Sprain - {label}",
        "alt_names": [f"{ligament} Tear"] if grade > 1 else [f"{ligament} Strain"],
        "tissue": "Ligament", "joint": joint, "region": region, "severity": grade,
        "severity_grades": "Grade I (stretched, stable) / Grade II (partial tear, mild-moderate laxity) / Grade III (complete tear, gross instability).",
        "healing_phases": _phases("Ligament"),
        "pain_pattern": pain,
        "mechanism": f"Forced motion beyond the {lg}'s normal range — twisting, valgus/varus force, hyperextension, or direct trauma depending on joint.",
        "movement_restrictions": {
            1: f"Avoid end-range/stress positions for the {lg} for 1-2 weeks; otherwise well tolerated.",
            2: f"Avoid loaded end-range and rotational/shear stress on the {lg} until proprioception and strength are restored.",
            3: f"Avoid any stress on the {lg} until medically evaluated; bracing/surgical consult often indicated.",
        }[grade],
        "joint_position_restrictions": f"Avoid the specific end-range position that stresses the {lg} (per its anatomical line of pull) until cleared.",
        "rom_restrictions": "Protected ROM early, progressing as swelling and pain allow; avoid forcing end-range." if grade > 1 else "Full pain-free ROM generally tolerated within days.",
        "loading_restrictions": {1: "Light-to-moderate loading tolerated once pain-free.", 2: "Light, controlled loading with bracing/taping as needed.", 3: "No loading until medically cleared."}[grade],
        "velocity_restrictions": "Avoid cutting/pivoting or high-velocity direction changes until proprioceptive control and strength are restored.",
        "impact_restrictions": "Avoid impact and multidirectional loading until cleared for return-to-sport testing." if grade > 1 else "Impact generally tolerated once pain-free.",
        "technical_faults_to_avoid": ["Skipping proprioceptive/balance retraining", "Returning to cutting/pivoting before strength and stability are restored"],
        "biomechanical_stresses_to_avoid": [f"Valgus/varus, rotational, or shear load across the joint that stresses the {lg}"],
        "muscles_to_protect": [], "muscles_to_strengthen": ["Dynamic stabilizers of the joint (proprioceptive and strength training)"],
        "safe_movement_patterns": ["Closed-chain, controlled-ROM loading within the pain-free range", "Balance/proprioceptive drills"],
        "contraindicated_movement_patterns": ["Open-chain end-range loading that stresses the ligament", "Uncontrolled cutting/pivoting/twisting"] if grade > 1 else ["Maximal-effort stress on the ligament"],
        "exercise_modifications": ["Brace/tape as indicated", "Progress from closed-chain to open-chain, straight-line to multidirectional loading"],
        "progression_criteria": ["Full pain-free ROM", "Strength and proprioception restored toward symmetry", "No pain/instability with progressively demanding loading"],
        "regression_criteria": ["Pain, swelling, or a sense of instability returns with current loading"],
        "return_to_sport_criteria": ["Strength and single-leg/functional testing symmetric to the uninjured side", "No instability or apprehension with sport-specific cutting/pivoting at full speed", "Clinician clearance for Grade II/III"],
        "absolute_contraindications": ["Return to cutting/pivoting sport before instability is resolved (Grade II/III)", "Loading through a positive instability/apprehension test"],
        "relative_contraindications": ["Unbraced high-demand training in the early post-injury period"],
        "clinical_red_flags": ["Gross instability or a joint that gives way with normal activity", "Neurovascular compromise distal to the joint", "Signs of associated fracture (point bony tenderness, inability to bear weight)"],
        "risk_score_logic": _risk_note(grade, joint),
    }


# ============================================================================
# TENDON INJURIES — generated across major tendons (v5.0 addition)
# ============================================================================
TENDONS = [
    ("Achilles Tendon", "Ankle", "Posterior Ankle/Heel"),
    ("Patellar Tendon", "Knee", "Anterior Knee"),
    ("Quadriceps Tendon", "Knee", "Anterior Knee (suprapatellar)"),
    ("Hamstring Tendons", "Knee", "Posterior Thigh/Ischial"),
    ("Rotator Cuff Tendons", "Shoulder", "Shoulder"),
    ("Long Head Biceps Tendon", "Shoulder", "Anterior Shoulder"),
    ("Distal Biceps Tendon", "Elbow", "Anterior Elbow"),
    ("Triceps Tendon", "Elbow", "Posterior Elbow"),
    ("Tibialis Posterior Tendon", "Ankle", "Medial Ankle"),
    ("Tibialis Anterior Tendon", "Ankle", "Anterior Ankle"),
    ("Peroneal Tendons", "Ankle", "Lateral Ankle"),
    ("Wrist Flexor Tendons", "Wrist", "Volar Wrist/Forearm"),
    ("Wrist Extensor Tendons", "Wrist", "Dorsal Wrist/Forearm (lateral epicondyle common origin)"),
]

_TENDON_KIND = {
    "tendinopathy": ("Tendinitis/Tendinosis (Tendinopathy)", 1,
                      "Gradual-onset, activity-related pain and stiffness, often worse at the start of activity and easing with warm-up, then returning after."),
    "partial_tear": ("Partial Tear", 2,
                      "More constant pain with palpable tenderness and weakness; may follow a sudden load after a period of tendinopathy."),
    "rupture": ("Complete Rupture", 3,
                 "Sudden, often audible pop with acute severe pain, marked weakness/loss of function, and possibly a palpable gap or altered contour."),
}


def _tendon_injury(tendon: str, joint: str, region: str, kind: str) -> dict:
    label, severity, pain = _TENDON_KIND[kind]
    t = tendon.lower()
    return {
        "name": f"{tendon} - {label}",
        "alt_names": [f"{tendon.split()[0]} Tendinitis"] if kind == "tendinopathy" else [],
        "tissue": "Tendon", "joint": joint, "region": region, "severity": severity,
        "severity_grades": "Tendinopathy/tendinitis (reactive-to-degenerative overload, no structural tear) -> partial tear -> complete rupture (structural failure).",
        "healing_phases": _phases("Tendon"),
        "pain_pattern": pain,
        "mechanism": f"Cumulative overload (tendinopathy) or a sudden forceful/eccentric load (partial-to-complete tear) on the {t}.",
        "movement_restrictions": {
            1: f"Manage load rather than rest completely — reduce the aggravating volume/intensity on the {t} while maintaining some pain-guided loading.",
            2: f"Avoid resisted and end-range loading of the {t} until re-evaluated; isometrics for pain relief may still be appropriate.",
            3: f"Avoid all loading of the {t} until medically evaluated — surgical repair is often indicated for complete rupture.",
        }[severity],
        "joint_position_restrictions": f"Avoid end-range stretch positions that load the {t} under tension until symptoms/healing allow.",
        "rom_restrictions": "Gentle pain-guided ROM; avoid aggressive stretching of a reactive or torn tendon.",
        "loading_restrictions": {1: "Isometric-to-heavy-slow-resistance loading is the core of tendinopathy rehab, dosed to a tolerable pain response.", 2: "Light, controlled isometric loading only until re-evaluated.", 3: "No loading until medically cleared."}[severity],
        "velocity_restrictions": "Avoid plyometric/energy-storage loading of the tendon until the later stages of rehab (tendinopathy) or until fully cleared (tear/rupture).",
        "impact_restrictions": "Reduce impact loading that reproduces symptoms; reintroduce gradually once tolerating heavier strength work." if severity == 1 else "Avoid impact loading until cleared.",
        "technical_faults_to_avoid": ["Complete rest without any loading (delays tendon adaptation)", "Too-rapid return to high-volume plyometric/impact work", "Ignoring a rising 24h pain response as a sign to back off"],
        "biomechanical_stresses_to_avoid": [f"Rapid spikes in the volume of high-load/energy-storage activity for the {t}"],
        "muscles_to_protect": [], "muscles_to_strengthen": [f"The muscle-tendon unit of the {tendon.lower()} via progressive resistance training"],
        "safe_movement_patterns": ["Isometric holds for pain modulation", "Slow, heavy resistance training within tolerable load"],
        "contraindicated_movement_patterns": ["Plyometric/ballistic loading of a reactive or torn tendon", "Loading through sharp/worsening pain"],
        "exercise_modifications": ["Isometrics -> isotonic (heavy slow resistance) -> energy-storage/plyometric progression", "Reduce aggravating volume while maintaining general training elsewhere"],
        "progression_criteria": ["24h pain response acceptable and trending down", "Strength improving toward symmetry", "Tolerates increasing load without symptom flare"],
        "regression_criteria": ["Pain increases and persists >24h after loading", "Morning stiffness/pain worsens"],
        "return_to_sport_criteria": ["Strength and function symmetric to the uninjured side", "Tolerates full sport-specific energy-storage/plyometric demand without symptom flare", "Clinician clearance for partial tear/rupture"],
        "absolute_contraindications": ["Continuing high-load training through a suspected partial/complete rupture"],
        "relative_contraindications": ["Rapid reintroduction of plyometric volume without a graded buildup"],
        "clinical_red_flags": ["Sudden pop with inability to perform the tendon's key function (e.g. can't do a single-leg heel raise, can't extend the elbow against resistance) — suspect rupture, refer urgently.", "Palpable gap or defect in the tendon"],
        "risk_score_logic": _risk_note(severity, joint),
    }


# ============================================================================
# NAMED CONDITIONS — Joint Disorders, Cartilage, Bone, Spine, Nerve, Fascia,
# Overuse, and Degenerative categories (v5.0 addition). Each hand-specified
# via the shared `_generic` builder for condition-specific accuracy.
# ============================================================================
def _generic(name, alt_names, tissue, joint, region, severity, pain, mechanism,
             move_restr, red_flags, rts_extra=None, contraindicated=None) -> dict:
    return {
        "name": name, "alt_names": alt_names, "tissue": tissue, "joint": joint, "region": region, "severity": severity,
        "severity_grades": f"Severity tier {severity}/3 in this system's mild(1)-severe(3) load-tolerance model.",
        "healing_phases": _phases(tissue),
        "pain_pattern": pain, "mechanism": mechanism,
        "movement_restrictions": move_restr,
        "joint_position_restrictions": f"Avoid positions that reproduce symptoms in the {region.lower()}.",
        "rom_restrictions": "Pain-free ROM only; avoid forcing through a symptomatic range." if severity > 1 else "Gentle pain-free ROM/mobility work generally tolerated and often therapeutic.",
        "loading_restrictions": {1: "Light-to-moderate loading tolerated if pain-free.", 2: "Light, controlled loading only.", 3: "No loading until medically cleared."}[severity],
        "velocity_restrictions": "Avoid high-velocity/ballistic loading until symptoms resolve." if severity > 1 else "No specific restriction beyond symptom-guided loading.",
        "impact_restrictions": "Avoid impact loading until cleared." if severity > 1 else "Generally tolerated if asymptomatic.",
        "technical_faults_to_avoid": ["Loading through pain", "Ignoring a worsening symptom trend", "Skipping graded-exposure progression back to full activity"],
        "biomechanical_stresses_to_avoid": [f"Repetitive or high-magnitude load through the {region.lower()} beyond current tolerance"],
        "muscles_to_protect": [], "muscles_to_strengthen": [f"Stabilizing/supporting musculature around the {region.lower()}"],
        "safe_movement_patterns": ["Pain-free, controlled loading within current tolerance"],
        "contraindicated_movement_patterns": contraindicated or ["High-load or end-range movement that reproduces symptoms"],
        "exercise_modifications": ["Reduce load/ROM/volume and rebuild gradually", "Substitute exercises that don't stress the affected area while symptomatic"],
        "progression_criteria": ["Symptom-free through current loading", "No flare 24h after loading", "Clinician sign-off for severity 2-3 before advancing"],
        "regression_criteria": ["Symptoms return or worsen with current loading"],
        "return_to_sport_criteria": ["Full pain-free ROM and strength", "Sport-specific movement tolerated at full intensity"] + (rts_extra or []),
        "absolute_contraindications": ["Loading through sharp/mechanical pain"],
        "relative_contraindications": ["Rapid return to prior training load without a graded buildup"],
        "clinical_red_flags": red_flags,
        "risk_score_logic": _risk_note(severity, joint),
    }


NAMED_CONDITIONS = [
    # --- Joint Disorders ---
    _generic("Shoulder Impingement Syndrome", ["Subacromial Impingement"], "Joint", "Shoulder", "Shoulder (subacromial space)", 1,
        "Pain with overhead/reaching motion, often a painful arc between ~60-120 degrees of abduction.",
        "Repetitive overhead activity, poor scapular control, or rotator cuff weakness narrowing the subacromial space.",
        "Avoid sustained/repetitive overhead loading until scapular control and cuff strength improve.",
        ["Sudden severe weakness (possible acute cuff tear) — refer for evaluation."]),
    _generic("Shoulder Instability (General/Atraumatic)", ["Multidirectional Instability"], "Joint", "Shoulder", "Shoulder", 1,
        "A sense of looseness/apprehension with certain positions rather than sharp pain; may include subluxation episodes.",
        "Repetitive microtrauma, generalized ligamentous laxity, or inadequate dynamic stabilizer strength.",
        "Avoid end-range positions that reproduce apprehension; build rotator cuff/scapular strength.",
        ["Frank dislocation event or persistent neurological symptoms — refer for evaluation."]),
    _generic("Lateral Epicondylalgia (Tennis Elbow)", ["Lateral Epicondylitis"], "Tendon", "Elbow", "Lateral Elbow", 1,
        "Pain over the lateral elbow with gripping or wrist extension against resistance.",
        "Repetitive wrist extension/gripping overload (racquet sports, manual work).",
        "Reduce repetitive gripping/wrist-extension load; isometric-to-progressive resistance loading is the core rehab strategy.",
        ["Persistent pain despite load management over months — refer for evaluation."]),
    _generic("Medial Epicondylalgia (Golfer's Elbow)", ["Medial Epicondylitis"], "Tendon", "Elbow", "Medial Elbow", 1,
        "Pain over the medial elbow with gripping or resisted wrist flexion/pronation.",
        "Repetitive wrist flexion/pronation overload (golf, throwing, manual work).",
        "Reduce repetitive gripping/wrist-flexion load; progressive resistance loading is the core rehab strategy.",
        ["Numbness/tingling into the ring/little fingers (possible ulnar nerve involvement) — refer for evaluation."]),
    _generic("Hip Impingement (Femoroacetabular Impingement, FAI)", ["FAI Syndrome"], "Joint", "Hip", "Hip", 1,
        "Groin pain with deep hip flexion, often with a pinching sensation (e.g. deep squat, prolonged sitting).",
        "Bony morphology (cam/pincer) causing abnormal contact between femur and acetabulum at end-range flexion/rotation.",
        "Avoid deep, loaded hip flexion combined with internal rotation until symptoms settle; work within a pain-free range.",
        ["Locking or catching with true mechanical block (possible labral tear) — refer for evaluation."]),
    _generic("Hip Instability (Atraumatic/Microinstability)", [], "Joint", "Hip", "Hip", 1,
        "A sense of looseness or 'giving way' rather than sharp pain, often with pivoting/end-range rotation.",
        "Capsular laxity, repetitive end-range loading, or after labral injury.",
        "Avoid uncontrolled end-range rotation under load; build hip/pelvic stabilizer strength.",
        ["True instability/subluxation episodes — refer for evaluation."]),
    _generic("Patellofemoral Pain Syndrome (PFPS)", ["Runner's Knee"], "Joint", "Knee", "Anterior Knee", 1,
        "Diffuse anterior knee pain, worse with stairs, squatting, or prolonged sitting (theater sign).",
        "Altered patellar tracking/loading, often from hip/quad strength or movement-pattern deficits.",
        "Reduce high-flexion loaded knee positions (deep squats, lunges) until symptoms settle; address hip/quad strength.",
        ["True mechanical locking or giving-way (possible loose body/instability) — refer for evaluation."]),
    _generic("Chondromalacia Patella", [], "Cartilage", "Knee", "Patellofemoral Joint", 1,
        "Anterior knee pain and grinding/crepitus with knee flexion under load (stairs, squats).",
        "Cartilage softening/breakdown on the underside of the patella from repetitive/abnormal patellofemoral loading.",
        "Reduce deep-flexion loaded knee positions until symptoms settle; build quad/hip control.",
        ["Significant effusion or locking — refer for evaluation."]),
    _generic("Patellar Instability (Recurrent)", [], "Joint", "Knee", "Anterior Knee", 2,
        "Apprehension or a sense of the kneecap shifting, especially with combined flexion and rotation.",
        "Prior dislocation, structural predisposition (trochlear dysplasia), or MPFL insufficiency.",
        "Avoid combined knee flexion + rotation under load; avoid positions that reproduce apprehension.",
        ["A dislocation event — refer for urgent evaluation."]),
    _generic("Osteochondral Injury (General)", ["OCD Lesion"], "Cartilage", "Knee", "Joint Surface (variable)", 2,
        "Deep, poorly localized joint pain, sometimes with catching/locking if a fragment is unstable.",
        "Repetitive microtrauma or an acute traumatic impact to the joint surface.",
        "Avoid high-impact/pivoting loading on the joint until imaging/clinical status clarifies stability.",
        ["Locking, catching, or a loose-body sensation — refer for evaluation."]),
    _generic("Chronic Ankle Instability", [], "Joint", "Ankle", "Ankle", 1,
        "Recurrent 'giving way' or a sense of looseness, often after prior sprains, without necessarily acute pain.",
        "Residual laxity and impaired proprioception following prior ankle sprain(s).",
        "Avoid uneven/unstable surfaces and uncontrolled cutting until proprioceptive control improves; brace/tape as needed.",
        ["Recurrent frank giving-way episodes causing falls — refer for evaluation."]),
    _generic("Carpal Instability", [], "Joint", "Wrist", "Wrist", 2,
        "Pain and a clicking/clunking sensation with wrist loading or specific motions.",
        "Ligamentous injury (often scapholunate) altering normal carpal bone kinematics.",
        "Avoid loaded end-range wrist extension and axial loading (e.g. planks, push-ups) until evaluated.",
        ["Progressive weakness or grip loss — refer for evaluation."]),
    _generic("Temporomandibular Joint (TMJ) Disorder", ["TMJ Dysfunction"], "Joint", "Neck", "Jaw/TMJ", 1,
        "Jaw pain, clicking/popping, or restricted opening, sometimes with associated headache/neck tension.",
        "Clenching/grinding, direct trauma, or postural/cervical contributing factors.",
        "Avoid loaded neck positions that aggravate jaw tension (e.g. heavy overhead bracing with jaw clenching); no major exercise-programming impact beyond general awareness.",
        ["Jaw locking that cannot self-reduce, or trauma with suspected fracture — refer for evaluation."]),

    # --- Cartilage (beyond meniscus, already in legacy) ---
    _generic("Articular Cartilage Lesion - Knee", ["Chondral Defect - Knee"], "Cartilage", "Knee", "Knee Joint Surface", 2,
        "Deep joint-line pain and swelling with loading, sometimes with mechanical catching.",
        "Acute impact/shear injury or chronic overload of the articular surface.",
        "Avoid high-impact/pivoting loading until imaging/clinical status clarifies severity.",
        ["Locking or a loose-body sensation — refer for evaluation."]),
    _generic("Articular Cartilage Lesion - Hip", [], "Cartilage", "Hip", "Hip Joint Surface", 2,
        "Deep groin/hip pain with weight-bearing and rotational loading.",
        "Chronic FAI-related overload or acute traumatic shear injury.",
        "Avoid deep, loaded hip flexion/rotation until evaluated.",
        ["Mechanical locking or catching — refer for evaluation."]),
    _generic("Articular Cartilage Lesion - Ankle", ["Talar Dome Lesion"], "Cartilage", "Ankle", "Ankle Joint Surface", 2,
        "Deep ankle pain with weight-bearing, sometimes with catching/locking.",
        "Often follows an ankle sprain with an associated impaction injury to the talar dome.",
        "Avoid high-impact/pivoting loading until evaluated.",
        ["Persistent locking/catching — refer for evaluation."]),

    # --- Bone Injuries ---
    _generic("Stress Reaction - Tibia", ["Bone Stress Reaction"], "Bone", "Knee", "Tibia", 1,
        "Gradual-onset, activity-related bone pain that initially resolves with rest and progressively worsens if training continues.",
        "Cumulative repetitive loading (running/jumping volume) exceeding the bone's adaptive capacity.",
        "Reduce impact loading immediately; avoid running/jumping until re-evaluated.",
        ["Pain at rest or with normal walking (possible progression to stress fracture) — refer for evaluation."]),
    _generic("Stress Fracture - Tibia", [], "Bone", "Knee", "Tibia", 2,
        "Focal, well-localized bone pain, worse with impact, often present with walking; point tenderness on exam.",
        "Continued repetitive loading beyond a stress reaction without adequate offloading.",
        "Non-impact activity only (pool running, cycling as tolerated) until cleared; no running/jumping.",
        ["Anterior (tension-side) tibial stress fracture — higher nonunion/complication risk, requires prompt medical evaluation."]),
    _generic("Stress Fracture - Metatarsal", [], "Bone", "Ankle", "Foot (Metatarsal)", 2,
        "Focal forefoot pain with weight-bearing, point tenderness over a specific metatarsal.",
        "Repetitive impact loading (running, jumping, marching).",
        "Non-impact activity only until cleared; may require protected weight-bearing (boot).",
        ["5th metatarsal (Jones) fracture — higher nonunion risk, requires prompt medical evaluation."]),
    _generic("Stress Fracture - Femoral Neck", [], "Bone", "Hip", "Femoral Neck", 3,
        "Groin or anterior thigh pain with weight-bearing, may be poorly localized early on.",
        "Repetitive impact loading, often in the context of relative energy deficiency/low bone density.",
        "Non-weight-bearing/protected weight-bearing per medical guidance; no impact loading.",
        ["This is a high-risk stress fracture site with fracture-displacement risk — requires prompt medical evaluation, do not continue training."]),
    _generic("Stress Fracture - Pars Interarticularis (Spondylolysis)", ["Pars Stress Fracture"], "Bone", "Lower Back", "Lumbar Spine (Pars)", 2,
        "Focal low back pain with extension/rotation loading, common in young athletes in extension-heavy sports.",
        "Repetitive lumbar extension/rotation loading (gymnastics, cricket fast bowling, weightlifting).",
        "Avoid lumbar extension/rotation loading until cleared; core stability work in neutral spine.",
        ["Bilateral pars defects with slip progression (spondylolisthesis) or neurological symptoms — refer for evaluation."]),
    _generic("Avulsion Fracture - Pelvis/Hip", [], "Bone", "Hip", "Pelvis", 2,
        "Sudden, sharp pain at a tendon attachment site (e.g. ASIS, ischial tuberosity) during forceful contraction, often in adolescents.",
        "Forceful, often eccentric muscle contraction pulling a bone fragment from its attachment (sprinting, kicking).",
        "Avoid loading the involved muscle-tendon-bone unit until imaging-confirmed healing.",
        ["Significant fragment displacement — may require surgical evaluation."]),
    _generic("Compression Fracture - Thoracic/Lumbar Spine", [], "Bone", "Lower Back", "Thoracic/Lumbar Spine", 2,
        "Localized back pain, worse with axial loading/flexion, may follow a fall or, in older adults, minimal trauma.",
        "Axial loading beyond bone tolerance — trauma, or low bone density with minor mechanical stress.",
        "Avoid axial loading and spinal flexion until medically cleared; screen for underlying bone health.",
        ["Neurological symptoms (numbness, weakness, bowel/bladder changes) — emergency evaluation for possible cord/cauda equina involvement."]),
    _generic("Bone Bruise (Bone Contusion)", [], "Bone", "Knee", "Variable (commonly knee)", 1,
        "Deep, diffuse joint pain and swelling following an impact, without a fracture line on imaging.",
        "Direct impact or compressive trauma to the bone (contact injury, fall).",
        "Reduce impact/high-load activity on the joint until pain and swelling resolve.",
        ["Pain significantly worse than expected, or non-weight-bearing — refer for evaluation to rule out fracture."]),
    _generic("Periostitis (Shin)", ["Periosteal Reaction"], "Bone", "Ankle", "Tibial Shaft (periosteum)", 1,
        "Aching, diffuse pain along the shin during/after impact activity.",
        "Repetitive impact loading irritating the periosteum, often an early-stage MTSS/stress-reaction presentation.",
        "Reduce impact loading volume; address contributing training-load/footwear factors.",
        ["Pain progressing to focal point tenderness (possible progression to stress fracture) — refer for evaluation."]),
    _generic("Shin Splints (Medial Tibial Stress Syndrome, MTSS)", [], "Bone", "Ankle", "Medial Tibial Border", 1,
        "Diffuse aching pain along the medial tibial border, worse at the start of a run and easing with warm-up, then returning after.",
        "Rapid increase in running volume/intensity, often combined with biomechanical or footwear factors.",
        "Reduce running volume/intensity; address load progression, footwear, and surface.",
        ["Focal point tenderness rather than diffuse pain (possible progression to stress fracture) — refer for evaluation."]),

    # --- Spine Disorders ---
    _generic("Cervical Strain (Acute)", ["Neck Strain"], "Spine", "Neck", "Cervical Spine", 1,
        "Localized neck pain and stiffness, often with reduced ROM, following an awkward load or sustained posture.",
        "Muscular overload, sustained poor posture, or minor traumatic mechanism.",
        "Avoid loaded end-range neck positions and heavy overhead/loaded carries until pain settles.",
        ["Radiating arm pain/numbness/weakness (possible radiculopathy) — refer for evaluation."]),
    _generic("Cervical Disc Herniation", [], "Spine", "Neck", "Cervical Spine", 2,
        "Neck pain that may radiate into the arm following a dermatomal pattern, sometimes with numbness/weakness.",
        "Disc material displacement from repetitive flexion/loading or an acute traumatic mechanism.",
        "Avoid loaded cervical flexion and axial loading (heavy overhead work) until symptoms settle.",
        ["Progressive weakness, or myelopathic signs (gait/balance changes, hand clumsiness) — urgent evaluation."]),
    _generic("Cervical Radiculopathy", [], "Nerve", "Neck", "Cervical Nerve Root", 2,
        "Neck pain radiating into the arm in a specific nerve-root distribution, with possible numbness/weakness.",
        "Nerve root compression from disc herniation, foraminal narrowing, or facet hypertrophy.",
        "Avoid positions that reproduce or worsen radicular symptoms (loaded cervical extension/rotation toward the symptomatic side).",
        ["Progressive motor weakness or myelopathic signs — urgent evaluation."]),
    _generic("Whiplash-Associated Disorder", ["Whiplash"], "Spine", "Neck", "Cervical Spine", 1,
        "Neck pain and stiffness, sometimes with headache/dizziness, following a rapid acceleration-deceleration mechanism.",
        "Rapid, forceful acceleration-deceleration of the neck (commonly a motor vehicle collision).",
        "Avoid loaded end-range neck positions until pain/ROM improve; early gentle movement is generally favored over prolonged rest.",
        ["Severe headache, visual changes, or neurological symptoms — refer for evaluation."]),
    _generic("Thoracic Strain", [], "Spine", "Lower Back", "Thoracic Spine", 1,
        "Localized mid-back pain, often related to a specific loaded rotational or flexion movement.",
        "Muscular overload or sustained poor posture through the thoracic spine.",
        "Avoid loaded thoracic rotation/flexion until pain settles.",
        ["Chest pain, breathing difficulty, or radicular symptoms — refer for evaluation to rule out other causes."]),
    _generic("Thoracic Facet Dysfunction", [], "Spine", "Lower Back", "Thoracic Spine (facet joints)", 1,
        "Localized mid-back pain, often with a specific movement direction that reproduces it, and restricted segmental motion.",
        "Repetitive or sustained loading/positioning stressing the facet joints.",
        "Avoid the specific loaded movement direction that reproduces symptoms until it settles.",
        ["Radicular or band-like chest pain — refer for evaluation."]),
    _generic("Lumbar Strain (Acute)", ["Low Back Strain"], "Spine", "Lower Back", "Lumbar Spine", 1,
        "Localized low back pain and stiffness, often following a lifting or twisting mechanism.",
        "Muscular/ligamentous overload from lifting, twisting, or sustained poor posture.",
        "Avoid loaded spinal flexion/rotation until pain settles; maintain gentle movement rather than complete rest.",
        ["Radiating leg pain, numbness, or saddle anesthesia/bowel-bladder changes (possible cauda equina) — emergency evaluation."]),
    _generic("Lumbar Disc Herniation", [], "Spine", "Lower Back", "Lumbar Spine", 2,
        "Low back pain often radiating down the leg (sciatica) following a dermatomal pattern; worse with sitting/flexion.",
        "Disc material displacement from repetitive flexion/loading or a sudden loaded flexion-rotation mechanism.",
        "Avoid loaded lumbar flexion and prolonged sitting; favor extension-biased positions if they reduce symptoms (McKenzie-style, individualized).",
        ["Saddle anesthesia, bowel/bladder changes, or progressive bilateral leg weakness (cauda equina syndrome) — EMERGENCY, immediate medical care."]),
    _generic("Lumbar Disc Bulge", [], "Spine", "Lower Back", "Lumbar Spine", 1,
        "Low back pain, sometimes with mild referred leg symptoms, without frank nerve root compression.",
        "Disc degeneration/loading without full herniation.",
        "Avoid loaded end-range flexion under high load; otherwise generally well tolerated with graded loading.",
        ["Progressive radicular symptoms — refer for evaluation."]),
    _generic("Sciatica", [], "Nerve", "Lower Back", "Sciatic Nerve / Lumbosacral", 2,
        "Pain radiating from the low back/buttock down the posterior leg, sometimes with numbness/tingling, following the sciatic distribution.",
        "Nerve root or sciatic nerve irritation/compression (disc herniation, piriformis, spinal stenosis).",
        "Avoid positions that reproduce or worsen leg symptoms; nerve-gliding and graded loading as tolerated.",
        ["Progressive weakness, foot drop, or saddle anesthesia/bowel-bladder changes — urgent/emergency evaluation."]),
    _generic("Lumbar Facet Syndrome", [], "Spine", "Lower Back", "Lumbar Spine (facet joints)", 1,
        "Localized low back pain, often worse with extension/rotation, easing with flexion.",
        "Repetitive extension/rotation loading stressing the facet joints.",
        "Avoid loaded spinal extension/rotation until symptoms settle; flexion-biased core work often tolerated.",
        ["Radicular symptoms into the leg — refer for evaluation."]),
    _generic("Spondylolysis (Stable)", [], "Bone", "Lower Back", "Lumbar Spine (Pars)", 1,
        "Focal low back pain with extension loading; may be asymptomatic and found incidentally.",
        "Repetitive lumbar extension/rotation loading, often in adolescent extension-sport athletes.",
        "Avoid lumbar extension/rotation loading until cleared; maintain neutral-spine core training.",
        ["Progressive slip (spondylolisthesis) or neurological symptoms — refer for evaluation."]),
    _generic("Spondylolisthesis (Low-Grade, Stable)", [], "Spine", "Lower Back", "Lumbar Spine", 2,
        "Low back pain, sometimes with hamstring tightness or mild radicular symptoms, worse with extension.",
        "Anterior slippage of one vertebra on another, often from a pars defect or degenerative facet changes.",
        "Avoid loaded lumbar extension and high-shear loading (heavy loaded hyperextension, deep loaded lunges) until stable and cleared.",
        ["Progressive slip, neurological symptoms, or bowel/bladder changes — urgent evaluation."]),
    _generic("Lumbar Spinal Stenosis", [], "Spine", "Lower Back", "Lumbar Spine (canal)", 1,
        "Low back and leg pain/heaviness that worsens with walking/standing (extension) and eases with sitting/flexion.",
        "Degenerative narrowing of the spinal canal or neural foramina.",
        "Favor flexion-biased positions/exercise; avoid prolonged loaded extension/standing.",
        ["Progressive bilateral leg weakness or bowel/bladder changes (possible cauda equina) — emergency evaluation."]),
    _generic("Sacroiliac (SI) Joint Dysfunction", [], "Joint", "Hip", "Sacroiliac Joint", 1,
        "Localized low back/buttock pain, often unilateral, provoked by single-leg loading or transitional movements.",
        "Altered SI joint mechanics from asymmetric loading, pregnancy-related laxity, or direct trauma.",
        "Avoid single-leg loaded positions and asymmetric loading that reproduce pain until it settles; pelvic stability work.",
        ["Progressive neurological symptoms — refer for evaluation (SI dysfunction itself is not a red-flag condition)."]),

    # --- Nerve Disorders ---
    _generic("Carpal Tunnel Syndrome", [], "Nerve", "Wrist", "Wrist (median nerve)", 1,
        "Numbness/tingling in the thumb-index-middle fingers, often worse at night, with possible grip weakness.",
        "Repetitive wrist flexion/extension or sustained loaded wrist positions compressing the median nerve.",
        "Avoid sustained/loaded wrist flexion or extension (e.g. front rack, deep push-up wrist position) until symptoms settle.",
        ["Progressive thenar (thumb-base) muscle wasting or constant numbness — refer for evaluation."]),
    _generic("Cubital Tunnel Syndrome", [], "Nerve", "Elbow", "Elbow (ulnar nerve)", 1,
        "Numbness/tingling in the ring and little fingers, often worse with prolonged elbow flexion.",
        "Repetitive/sustained elbow flexion or direct pressure over the medial elbow compressing the ulnar nerve.",
        "Avoid sustained/loaded end-range elbow flexion and direct pressure on the medial elbow until symptoms settle.",
        ["Progressive hand intrinsic muscle weakness/wasting — refer for evaluation."]),
    _generic("Thoracic Outlet Syndrome", [], "Nerve", "Shoulder", "Neck/Shoulder (brachial plexus/subclavian vessels)", 1,
        "Numbness, tingling, heaviness, or pain in the arm/hand, often provoked by overhead positions.",
        "Compression of the neurovascular bundle between the neck and shoulder (scalenes, first rib, pec minor).",
        "Avoid sustained overhead positions and heavy shrug-dominant loading until symptoms settle; address postural/scalene tightness.",
        ["Arm swelling/color change (possible vascular TOS) or progressive weakness — refer for evaluation."]),
    _generic("Common Peroneal Neuropathy", [], "Nerve", "Knee", "Lateral Knee/Fibular Head (peroneal nerve)", 1,
        "Numbness on the top of the foot/lateral shin, possible foot drop, often from pressure at the fibular head.",
        "Direct compression (e.g. prolonged kneeling/crossed legs, tight bracing) or traction injury near the fibular head.",
        "Avoid sustained direct pressure over the fibular head and positions that reproduce symptoms.",
        ["Foot drop or progressive weakness — refer for evaluation."]),
    _generic("Tarsal Tunnel Syndrome", [], "Nerve", "Ankle", "Medial Ankle (tibial nerve)", 1,
        "Numbness/tingling/burning on the sole of the foot, often worse with standing/walking.",
        "Compression of the tibial nerve as it passes behind the medial malleolus.",
        "Avoid sustained loaded ankle eversion/pronation and prolonged standing until symptoms settle.",
        ["Progressive intrinsic foot muscle weakness — refer for evaluation."]),
    _generic("Peripheral Nerve Entrapment (General)", [], "Nerve", "Wrist", "Variable", 1,
        "Numbness, tingling, or burning in a specific nerve distribution, sometimes with associated weakness.",
        "Mechanical compression or repetitive irritation of a peripheral nerve at a vulnerable anatomical site.",
        "Avoid the specific sustained/repetitive position that reproduces symptoms until the entrapment is addressed.",
        ["Progressive motor weakness or muscle wasting in the nerve's distribution — refer for evaluation."]),

    # --- Fascia & Connective Tissue ---
    _generic("Plantar Fasciitis", ["Plantar Fasciopathy"], "Fascia", "Ankle", "Plantar Foot (heel)", 1,
        "Sharp heel pain with the first steps in the morning or after rest, easing somewhat with activity then worsening later in the day.",
        "Repetitive loading of the plantar fascia, often from a training-load spike, footwear change, or calf tightness.",
        "Reduce high-impact loading volume; avoid prolonged barefoot walking on hard surfaces until symptoms settle.",
        ["Sudden, sharp tearing pain with a pop (possible plantar fascia rupture) — refer for evaluation."]),
    _generic("IT Band Syndrome", ["Iliotibial Band Syndrome"], "Fascia", "Knee", "Lateral Knee/Thigh", 1,
        "Sharp or aching lateral knee pain, typically appearing at a consistent point during running and easing with rest.",
        "Repetitive knee flexion/extension (running/cycling) with altered hip control causing friction/compression near the lateral femoral condyle.",
        "Reduce running volume/downhill running until symptoms settle; address hip abductor strength and running mechanics.",
        ["Symptoms that fail to respond to load management over several weeks — refer for evaluation."]),
    _generic("Fascial Adhesions", [], "Fascia", "Lower Back", "Variable", 1,
        "Localized stiffness/restriction and dull ache with movement in the affected region.",
        "Post-injury or post-surgical scar tissue formation, or chronic under-mobilized tissue.",
        "Gentle mobility/soft-tissue work generally tolerated and often therapeutic; avoid aggressive loading that reproduces sharp pain.",
        ["Rapidly worsening pain or new neurological symptoms — refer for evaluation."]),

    # --- Overuse Conditions (named/aliased) ---
    _generic("Jumper's Knee (Patellar Tendinopathy)", ["Patellar Tendinitis"], "Tendon", "Knee", "Anterior Knee (patellar tendon)", 1,
        "Localized pain at the inferior pole of the patella, worse with jumping/landing and after sitting.",
        "Repetitive jump-landing loading exceeding the tendon's adaptive capacity.",
        "Reduce jumping/landing volume; isometric-to-heavy-slow-resistance loading is the core rehab strategy.",
        ["Persistent pain despite load management over months — refer for evaluation."]),
    _generic("Thrower's Shoulder (Internal Impingement)", [], "Joint", "Shoulder", "Posterior Shoulder", 1,
        "Posterior shoulder pain during the late-cocking/acceleration phase of throwing.",
        "Repetitive overhead throwing load causing posterior capsule tightness and internal impingement.",
        "Reduce high-velocity overhead/throwing volume until symptoms settle; address posterior capsule mobility and scapular control.",
        ["Sudden loss of velocity/control with pain (possible labral or cuff injury) — refer for evaluation."]),
    _generic("Swimmer's Shoulder", [], "Joint", "Shoulder", "Shoulder", 1,
        "Anterior/lateral shoulder pain with repetitive overhead stroke mechanics, especially at higher training volumes.",
        "High-volume repetitive overhead loading with relative rotator cuff/scapular stabilizer fatigue.",
        "Reduce overhead training volume until symptoms settle; build rotator cuff and scapular stabilizer strength.",
        ["Sudden weakness or night pain unrelated to activity — refer for evaluation."]),
    _generic("Osgood-Schlatter Disease", [], "Bone", "Knee", "Tibial Tuberosity (pediatric)", 1,
        "Pain and a bony prominence at the tibial tuberosity in a growing adolescent, worse with jumping/kneeling.",
        "Repetitive traction from the patellar tendon on the tibial tuberosity growth plate during a growth spurt.",
        "Reduce jumping/loaded knee-extension volume during symptomatic periods; generally self-limiting with skeletal maturity.",
        ["Severe pain with minimal activity, or signs suggesting avulsion fracture — refer for evaluation."]),
    _generic("Sever's Disease (Calcaneal Apophysitis)", [], "Bone", "Ankle", "Calcaneus (pediatric, heel)", 1,
        "Heel pain in a growing child/adolescent, worse with running/jumping, often bilateral.",
        "Repetitive traction/compression at the calcaneal growth plate during a growth spurt.",
        "Reduce running/jumping volume during symptomatic periods; generally self-limiting with skeletal maturity.",
        ["Pain that persists significantly beyond the expected growth window, or is unilateral with atypical features — refer for evaluation."]),
    _generic("Repetitive Strain Injury (RSI) - Forearm/Wrist", [], "Muscle", "Wrist", "Forearm/Wrist", 1,
        "Gradual-onset aching, tightness, or pain with repetitive hand/wrist tasks, easing with rest.",
        "Repetitive, high-frequency low-load activity (typing, manual work, repetitive gripping) without adequate recovery.",
        "Reduce repetitive load/frequency; address ergonomics and build progressive tolerance.",
        ["Numbness/tingling suggesting nerve involvement, or progressive weakness — refer for evaluation."]),

    # --- Degenerative Conditions ---
    _generic("Osteoarthritis - Knee", [], "Cartilage", "Knee", "Knee", 1,
        "Aching joint pain and stiffness, worse with activity and after rest (gel phenomenon), possibly with crepitus.",
        "Progressive cartilage degeneration from cumulative joint loading, prior injury, or biomechanical factors.",
        "Favor lower-impact loading modalities; avoid high-impact/deep-flexion loading during symptomatic flares.",
        ["Rapidly progressive pain, significant effusion, or joint deformity — refer for evaluation."]),
    _generic("Osteoarthritis - Hip", [], "Cartilage", "Hip", "Hip", 1,
        "Groin/lateral hip pain and stiffness, worse with activity and prolonged sitting, reduced rotation ROM.",
        "Progressive cartilage degeneration from cumulative joint loading or prior structural factors (e.g. FAI).",
        "Favor lower-impact loading; avoid deep, loaded end-range hip flexion/rotation during symptomatic flares.",
        ["Rapidly progressive pain or significant loss of function — refer for evaluation."]),
    _generic("Osteoarthritis - Shoulder", [], "Cartilage", "Shoulder", "Shoulder", 1,
        "Deep shoulder ache and stiffness, worse with overhead activity, possible crepitus.",
        "Progressive glenohumeral cartilage degeneration from cumulative loading or prior injury.",
        "Reduce high-load overhead work during symptomatic flares; maintain ROM within comfort.",
        ["Rapidly progressive pain or significant loss of function — refer for evaluation."]),
    _generic("Osteoarthritis - Ankle", [], "Cartilage", "Ankle", "Ankle", 1,
        "Aching ankle pain and stiffness with weight-bearing, often following prior significant ankle trauma.",
        "Progressive cartilage degeneration, frequently post-traumatic after fracture/severe sprain.",
        "Favor lower-impact loading; avoid high-impact/pivoting activity during symptomatic flares.",
        ["Rapidly progressive pain or significant loss of function — refer for evaluation."]),
    _generic("Osteoarthritis - Wrist/Hand", [], "Cartilage", "Wrist", "Wrist/Hand", 1,
        "Aching joint pain and stiffness with gripping/loading, possible reduced grip strength.",
        "Progressive cartilage degeneration, sometimes post-traumatic (e.g. after SLAC wrist).",
        "Reduce high-load gripping/axial wrist loading during symptomatic flares.",
        ["Rapidly progressive pain or significant loss of function — refer for evaluation."]),
    _generic("Degenerative Disc Disease - Cervical", [], "Spine", "Neck", "Cervical Spine", 1,
        "Chronic neck stiffness/ache, sometimes with intermittent radicular symptoms, worse with prolonged static postures.",
        "Progressive disc dehydration/height loss over time, altering segmental spine mechanics.",
        "Avoid prolonged loaded end-range neck positions during symptomatic periods; maintain mobility and strength.",
        ["New or progressive radicular/myelopathic symptoms — refer for evaluation."]),
    _generic("Degenerative Disc Disease - Lumbar", [], "Spine", "Lower Back", "Lumbar Spine", 1,
        "Chronic low back stiffness/ache, worse with prolonged static postures, often better with movement.",
        "Progressive disc dehydration/height loss over time, altering segmental spine mechanics.",
        "Avoid prolonged loaded end-range flexion during symptomatic periods; maintain general mobility and progressive strength training.",
        ["New or progressive radicular symptoms or bowel/bladder changes — refer for evaluation."]),
]


# ============================================================================
# ASSEMBLE THE FULL TAXONOMY
# ============================================================================
INJURY_TAXONOMY: Dict[str, dict] = {}

for _name, _info in _LEGACY.items():
    INJURY_TAXONOMY[_name] = _enrich_legacy(_name, _info["joint"], _info["severity"])

for _muscle, _joint, _region in MUSCLE_GROUPS:
    for _grade in (1, 2, 3):
        _entry = _muscle_strain(_muscle, _joint, _region, _grade)
        INJURY_TAXONOMY[_entry["name"]] = _entry

for _entry in _MUSCLE_CONDITIONS:
    INJURY_TAXONOMY[_entry["name"]] = _entry

for _ligament, _joint, _region in LIGAMENTS:
    for _grade in (1, 2, 3):
        _entry = _ligament_sprain(_ligament, _joint, _region, _grade)
        INJURY_TAXONOMY[_entry["name"]] = _entry

for _tendon, _joint, _region in TENDONS:
    for _kind in ("tendinopathy", "partial_tear", "rupture"):
        _entry = _tendon_injury(_tendon, _joint, _region, _kind)
        INJURY_TAXONOMY[_entry["name"]] = _entry

for _entry in NAMED_CONDITIONS:
    INJURY_TAXONOMY[_entry["name"]] = _entry


# Sanity: every entry must carry the load-bearing keys the engine reads, and
# every entry name must be unique (dict construction above already guarantees
# uniqueness by key, but this also catches an empty/malformed entry early).
for _n, _e in INJURY_TAXONOMY.items():
    assert "joint" in _e and "severity" in _e, f"Malformed injury entry: {_n}"
    assert _e["severity"] in (1, 2, 3), f"Invalid severity for: {_n}"

del _name, _info, _muscle, _joint, _region, _grade, _entry, _ligament, _tendon, _kind, _n, _e


# ============================================================================
# GROUPED VIEW — Section (joint) -> Subsection (condition) -> Grades
# ============================================================================
# Powers the frontend's injury browser: sections like "Knee" / "Shoulder" /
# "Wrist", each broken into named conditions ("ACL Tear", "Meniscus Tear",
# ...), each of those broken into its severity/grade variants where the
# condition has more than one (most muscle/ligament/tendon entries are
# generated in 2-3 grades; many named conditions only have one severity).
#
# The grouping key is everything in `name` before " - " (every generated
# entry follows "{Condition} - {Grade label}"; single-severity named
# conditions have no " - " at all, so they're their own one-grade group).
# This is derived at import time from INJURY_TAXONOMY itself, so it can never
# drift out of sync with the actual data - same principle as
# ProgressionEngine.load_database deriving all_injuries from the live graph.
SEVERITY_LABEL = {1: "Mild", 2: "Moderate", 3: "Severe"}


def _condition_group(name: str) -> str:
    return name.split(" - ", 1)[0].strip()


# ============================================================================
# COMBAT SPORTS & RUGBY S&C MANUAL, PART 7.7 — NAMED SUBSTITUTION TABLE
# ============================================================================
# `find_alternatives` above already does general-purpose, live substitution
# by movement-pattern + joint-clearance for ANY exercise/injury combination
# it's asked about - that's the engine's actual safety mechanism and this
# table doesn't change it. What was missing (flagged in the README as not
# yet ported) is the manual's own *named* version of that same idea: a
# coach-readable "if this common issue shows up, here's what a coach would
# reach for" reference, matched to a joint the same way the rest of this
# file already keys everything (Lower Back, Shoulder, Knee, Wrist, Elbow),
# plus the manual's own default-culprit exercises and its explicit
# clinical caveat. `part7_recommended_swap` cross-checks each named
# substitute against exercises.json by name so the ids returned are real
# and clickable, not just text.
PART7_SUBSTITUTION_TABLE: List[Dict] = [
    {
        "joint": "Lower Back",
        "issue": "Low back irritation",
        "typical_culprit": ["Barbell Back Squat", "Barbell Conventional Deadlift"],
        "safer_substitutes": ["Belt Squat", "Trap Bar Deadlift", "Single-Leg Hip Thrust", "GHD Hip Extension"],
        "note": "Trap bar's higher handles reduce forward lean vs. a conventional pull; belt squat loads the hips instead of the spine.",
    },
    {
        "joint": "Shoulder",
        "issue": "Shoulder pain / impingement",
        "typical_culprit": ["Flat Bench Press", "Barbell Overhead Press"],
        "safer_substitutes": ["Landmine Press", "Floor Press", "Neutral-Grip Dumbbell Press"],
        "note": "The landmine's arc path and the floor press's shortened range both reduce end-range shoulder stress vs. a straight barbell bar path.",
    },
    {
        "joint": "Knee",
        "issue": "Knee pain",
        "typical_culprit": ["Barbell Back Squat", "Walking Lunge"],
        "safer_substitutes": ["Belt Squat", "Box Squat (Barbell)", "Backward Sled Drag", "Leg Press"],
        "note": "A higher box and belt-loaded squat both reduce knee shear vs. a deep barbell back squat; reverse sled drag trains the quads with minimal joint compression.",
    },
    {
        "joint": "Wrist",
        "issue": "Wrist pain",
        "typical_culprit": ["Barbell Front Squat", "Flat Bench Press"],
        "safer_substitutes": ["Dumbbell Goblet Squat", "Kettlebell Floor Press", "Landmine Press"],
        "note": "Kettlebell/dumbbell grips let the wrist stay neutral instead of loaded in extension the way a barbell front rack or bench grip does; straps help on pulling movements.",
    },
    {
        "joint": "Elbow",
        "issue": "Elbow pain (grappler's elbow)",
        "typical_culprit": ["EZ Bar Curl", "Weighted Pull-Up"],
        "safer_substitutes": ["Neutral Grip Pull-Up", "Fat-Grip Row"],
        "note": "Neutral-grip pulling and a fatter bar/handle both reduce direct forearm/elbow isolation load; reduce direct arm isolation work temporarily.",
    },
    {
        "joint": "Hip",
        "issue": "Hamstring strain history",
        "typical_culprit": ["Speed Deadlift", "Romanian Deadlift"],
        "safer_substitutes": ["Nordic Hamstring Curl", "Dumbbell Goblet Squat", "Belt Squat"],
        "note": "Start Nordic curls light; reintroduce heavy hinge loading gradually rather than jumping back to full-intensity sprinting or RDLs.",
    },
    {
        "joint": "Knee",  # "returning from any lower-body injury" - keyed to Knee since that's this table's closest 8-tag match; Hip/Ankle injuries route here too via the generic find_alternatives path.
        "issue": "Returning from any lower-body injury",
        "typical_culprit": ["Barbell Back Squat", "Barbell Conventional Deadlift"],
        "safer_substitutes": ["Belt Squat", "Dumbbell Goblet Squat"],
        "note": "Belt squat and goblet squat let you keep training the pattern while unloading the spine - progress back to the barbell once pain-free.",
    },
]

PART7_DISCLAIMER = (
    "Persistent pain is a signal to see a physiotherapist or sports medicine "
    "professional, not just to swap exercises - these substitutions are for "
    "training around minor niggles, not diagnosing or treating injuries."
)


def part7_substitution_guidance(joint: Optional[str] = None) -> List[Dict]:
    """The manual's Part 7.7 table, optionally filtered to one joint (the
    same 8-tag vocabulary as everything else in this file). Returns the
    full table when `joint` is None."""
    if joint is None:
        return PART7_SUBSTITUTION_TABLE
    return [row for row in PART7_SUBSTITUTION_TABLE if row["joint"] == joint]


def part7_recommended_swap(exercise: dict, all_exercises: Dict[str, dict], joint: str) -> List[dict]:
    """Cross-reference this exercise's joint against the manual's named
    substitution table and resolve each named substitute to a real
    exercises.json entry by name (case-insensitive), so the result is a
    clickable exercise, not just a string a UI would have to re-parse.
    Only returns rows whose `typical_culprit` list actually contains this
    exercise's name - a generic knee-pain row shouldn't attach itself to
    every squat variant regardless of which one the person was doing."""
    name = exercise.get("name", "")
    by_name = {e.get("name", "").lower(): e for e in all_exercises.values()}
    matches = []
    for row in part7_substitution_guidance(joint):
        if name.lower() not in [c.lower() for c in row["typical_culprit"]]:
            continue
        resolved = []
        for sub_name in row["safer_substitutes"]:
            cand = by_name.get(sub_name.lower())
            if cand:
                resolved.append({"id": cand["id"], "name": cand["name"]})
        matches.append({
            "issue": row["issue"],
            "note": row["note"],
            "substitutes": resolved,
        })
    return matches


def grouped_injury_taxonomy() -> Dict[str, List[dict]]:
    """{joint: [{condition, grades: [{name, severity, severity_label, tissue,
    region}, ...]}, ...]}, sections and subsections alphabetical, grades
    ordered mild -> severe."""
    by_joint: Dict[str, Dict[str, list]] = {}
    for name, entry in INJURY_TAXONOMY.items():
        joint = entry["joint"]
        condition = _condition_group(name)
        by_joint.setdefault(joint, {}).setdefault(condition, []).append({
            "name": name,
            "severity": entry["severity"],
            "severity_label": SEVERITY_LABEL[entry["severity"]],
            "tissue": entry.get("tissue", ""),
            "region": entry.get("region", ""),
        })

    result: Dict[str, List[dict]] = {}
    for joint, conditions in by_joint.items():
        result[joint] = [
            {
                "condition": cond,
                "grades": sorted(grades, key=lambda g: g["severity"]),
            }
            for cond, grades in sorted(conditions.items())
        ]
        result[joint].sort(key=lambda c: c["condition"])
    return dict(sorted(result.items()))
