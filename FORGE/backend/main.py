import copy
import json
import os
from typing import Dict, List, Optional

import networkx as nx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.models.schemas import (
    CONDITIONING_EMPHASES,
    EXPERIENCE_LEVELS as _EXPERIENCE_LEVELS,
    PRIMARY_GOALS,
    TRAINING_PHASES,
    ProgramRequest,
    ProgressionOverride,
    ReadinessInputs,
    UserBiometrics,
    WorkoutRequest,
)
from backend.services.injury_taxonomy import (
    INJURY_TAXONOMY,
    SEVERITY_DIFFICULTY_CEILING,
    classify_injury_risk,
    find_alternatives,
    part7_substitution_guidance,
    part7_recommended_swap,
    PART7_DISCLAIMER,
    grouped_injury_taxonomy,
)
from backend.services.exercise_metadata import build_equipment_catalog
from backend.services.knowledge_graph import build_knowledge_graph, explain_exercise, is_rehab_candidate
from backend.services.program_builder import SPLIT_TEMPLATES, SPORT_SPLIT_GUIDANCE, PHASE_GUIDANCE, generate_program
from backend.services.programming_role import ROLE_ORDER, classify_programming_role, session_order_rank
from backend.services.strength_standards import classify_strength_level, level_check
from backend.services.sport_profiles import (
    SPORT_MOVEMENT_EMPHASIS,
    SPORT_QUALITY_PROFILES,
    blended_transfer_score,
    movement_emphasis_multiplier,
    sport_conditioning_profile,
    transfer_rationale,
)
from backend.services.conditioning_protocols import conditioning_reference
import random

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    # No cookies/auth headers are used anywhere in this app, so credentials
    # aren't needed - and "*" origins + allow_credentials=True is an invalid
    # combination per the CORS spec (browsers reject it outright). See
    # config.py's CORS_ORIGINS comment for why "*" itself is kept.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXPERIENCE_LEVELS = _EXPERIENCE_LEVELS
LEVEL_RANK = {lvl: i for i, lvl in enumerate(EXPERIENCE_LEVELS)}
# How many rungs above the user's own level we'll still show (a controlled "stretch").
LEVEL_STRETCH = 1

# LEVEL_STRETCH above only ever answers "is this exercise too advanced to show
# at all" - it's a ceiling, not a preference. Nothing else in the engine used
# to care whether a *qualifying* exercise actually matched the user's level,
# so sorting/selection ran purely on sport_priority_score. In practice that
# meant an Elite lifter and a Beginner asking for the same sport/equipment got
# the exact same ranked list, because a Beginner-tier movement with a high
# sport score (e.g. Push-Up scoring 85 for Boxing) would consistently
# out-rank Advanced/Elite-tier lifts with a merely-good sport score - "better"
# here meaning "more appropriate to train at this person's level", not just
# "more sport-relevant in isolation".
#
# level_fit_multiplier fixes that by discounting an exercise's score based on
# how many rungs its own experience_level sits from the user's stated level -
# 0 rungs away = no discount, further away = progressively discounted. The
# discount is asymmetric: exercises *below* the user's level are penalized
# more per rung than exercises *above* it, because the ceiling check above
# already keeps "above" in check (at most LEVEL_STRETCH rungs get through at
# all), so once an above-level exercise clears that gate it should still
# compete normally - while nothing upstream stops a trivially-easy exercise
# from clearing every other check and dominating on sport score alone.
LEVEL_FIT_PENALTY_PER_RUNG_BELOW = 0.15
LEVEL_FIT_PENALTY_PER_RUNG_ABOVE = 0.05
LEVEL_FIT_MIN_MULTIPLIER = 0.35


def level_fit_multiplier(ex_level_rank: int, user_level_rank: int) -> float:
    gap = ex_level_rank - user_level_rank
    if gap >= 0:
        penalty = gap * LEVEL_FIT_PENALTY_PER_RUNG_ABOVE
    else:
        penalty = -gap * LEVEL_FIT_PENALTY_PER_RUNG_BELOW
    return max(LEVEL_FIT_MIN_MULTIPLIER, 1 - penalty)


def level_fit_label(ex_level_rank: int, user_level_rank: int) -> str:
    gap = ex_level_rank - user_level_rank
    if gap == 0:
        return "Matched to your level"
    if gap > 0:
        return "A stretch above your level" if gap <= LEVEL_STRETCH else "Above your level"
    return "Below your level (still safe, but not your ceiling)" if gap == -1 else "Well below your level"

# Request/response schemas (ProgressionOverride, UserBiometrics, WorkoutRequest,
# ProgramRequest) now live in backend/models/schemas.py - see that module's
# docstring for why. Imported above; nothing about their fields or defaults
# changed in the move.


# ==========================================
# 2. DAG & KNOWLEDGE ENGINE
# ==========================================

class ProgressionEngine:
    def __init__(self, json_path: str = None):
        if json_path is None:
            json_path = str(settings.EXERCISES_JSON_PATH)

        self.json_path = json_path
        self.base_dag = nx.DiGraph()
        self.knowledge_graph = None  # built in load_database: multi-relational graph (see knowledge_graph.py)
        self.exercises_by_id: Dict[str, Dict] = {}
        self.all_sports: List[str] = []
        self.all_equipment: List[str] = []
        self.all_injuries: List[str] = []
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"Database file '{self.json_path}' not found.")

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        exercises = data.get("exercises", [])
        self.exercises_by_id = {ex["id"]: ex for ex in exercises}

        for ex in exercises:
            self.base_dag.add_node(ex["id"], **ex)

        # Edge direction: regression -> progression (completing the regression unlocks the progression)
        for ex in exercises:
            for prog_id in ex.get("progressions", []):
                if prog_id in self.base_dag:
                    self.base_dag.add_edge(ex["id"], prog_id)

        if not nx.is_directed_acyclic_graph(self.base_dag):
            cycle = nx.find_cycle(self.base_dag)
            raise ValueError(f"Progression database contains a cycle, engine cannot resolve order: {cycle}")

        # Metadata derived straight from the data, so the frontend can never drift out of
        # sync with what the engine actually knows about (this used to be hand-typed twice).
        # Injuries now come primarily from INJURY_TAXONOMY (specific, severity-tagged
        # conditions like "ACL Tear - Grade 3 (Complete Rupture)") rather than the bare
        # joint_stress tags, so the user can say *how bad* an injury is, not just *where*
        # it is. The raw joint/tag strings from exercises.json are still unioned in below
        # so nothing that was previously selectable disappears.
        sports, equipment, injuries = set(), set(), set()
        injuries.update(INJURY_TAXONOMY.keys())
        for _, d in self.base_dag.nodes(data=True):
            sports.update(d.get("sport_priority", {}).keys())
            equipment.add(d.get("equipment", "Bodyweight"))
            injuries.update(d.get("joint_stress", []))
            injuries.update(d.get("injuries_to_avoid", []))
        self.all_sports = sorted(sports)
        self.all_equipment = sorted(equipment)
        self.all_injuries = sorted(injuries)

        # The actual multi-relational knowledge graph: progressions, equipment
        # substitutes, joint stress, rehab-candidacy, and sport transfer as
        # first-class typed edges - see knowledge_graph.py for why this exists
        # alongside base_dag rather than replacing it (base_dag stays the
        # per-request-mutable progression graph custom_progressions edits;
        # this is the queryable, base-data relationship map).
        self.knowledge_graph = build_knowledge_graph(exercises)

    def _apply_overrides(self, dag: nx.DiGraph, overrides: List[ProgressionOverride]):
        """Applies per-request customizations to a private COPY of the DAG.

        The engine previously mutated the single shared `self.base_dag` here, which meant
        one user's custom progression overrides would silently leak into and permanently
        corrupt every other user's results (and stack up over time). Every request now
        gets its own working graph.
        """
        for override in overrides:
            ex_id = override.exercise_id
            if ex_id not in dag:
                continue
            if override.custom_name:
                dag.nodes[ex_id]["name"] = override.custom_name
            if override.difficulty is not None:
                dag.nodes[ex_id]["difficulty"] = override.difficulty
            if override.equipment:
                dag.nodes[ex_id]["equipment"] = override.equipment
            if override.prerequisites:
                for prereq in override.prerequisites:
                    if prereq in dag:
                        dag.add_edge(prereq, ex_id)

        if not nx.is_directed_acyclic_graph(dag):
            cycle = nx.find_cycle(dag)
            raise HTTPException(
                status_code=400,
                detail=f"custom_progressions introduced a cycle: {cycle}",
            )

    def evaluate_biometrics_and_strength(self, biometrics: Optional[UserBiometrics]) -> Dict:
        if not biometrics:
            # Previously this defaulted to "average lifter" ratios (0.5 bench / 0.8 squat /
            # 1.0 deadlift) even when we had zero evidence the user could do any of that,
            # which would silently unlock barbell work for someone the engine knows nothing
            # about. With no data, the only defensible assumption is "prove it first."
            return {
                "bmi": None,
                "relative_bench_ratio": 0.0,
                "relative_squat_ratio": 0.0,
                "relative_deadlift_ratio": 0.0,
                "pullups_max_reps": 0,
                "pushups_max_reps": 0,
                "status": "No biometrics provided - conservative (bodyweight-only) defaults applied",
                # classify_strength_level(weight_kg=0.0) hits its own "nothing usable
                # entered" branch (same 0-means-untested convention as every other
                # field here), so this stays the single source of that shape instead
                # of a hand-typed duplicate of it.
                "level_estimate": classify_strength_level(weight_kg=0.0),
            }

        height_m = biometrics.height_cm / 100.0
        bmi = biometrics.weight_kg / (height_m ** 2)
        rel_bench = (biometrics.bench_press_1rm or 0.0) / biometrics.weight_kg
        rel_squat = (biometrics.squat_1rm or 0.0) / biometrics.weight_kg
        rel_deadlift = (biometrics.deadlift_1rm or 0.0) / biometrics.weight_kg

        # Independent, advisory-only estimate of overall training level from
        # these same numbers - see strength_standards.py. This never touches
        # strength_qualified/level_ok below (those still key off the
        # exercise's own strength_requirements and the person's *stated*
        # experience_level exactly as before); it just rides along in the
        # response so a mis-stated level is visible instead of silent (see
        # that module's docstring for why this was previously a real gap).
        level_estimate = classify_strength_level(
            weight_kg=biometrics.weight_kg,
            bench_press_1rm=biometrics.bench_press_1rm or 0.0,
            squat_1rm=biometrics.squat_1rm or 0.0,
            deadlift_1rm=biometrics.deadlift_1rm or 0.0,
            pullups_max_reps=biometrics.pullups_max_reps or 0,
            pushups_max_reps=biometrics.pushups_max_reps or 0,
            sex=biometrics.sex,
        )

        return {
            "bmi": round(bmi, 2),
            "relative_bench_ratio": round(rel_bench, 2),
            "relative_squat_ratio": round(rel_squat, 2),
            "relative_deadlift_ratio": round(rel_deadlift, 2),
            "pullups_max_reps": biometrics.pullups_max_reps or 0,
            "pushups_max_reps": biometrics.pushups_max_reps or 0,
            "status": "Biometrics analyzed",
            "level_estimate": level_estimate,
        }

    @staticmethod
    def _strength_gap(bio_eval: Dict, reqs: Dict) -> Dict:
        """How far the user is from qualifying for a locked exercise, per metric."""
        gap = {}
        pairs = [
            ("bench_ratio", "relative_bench_ratio", "x bodyweight bench"),
            ("squat_ratio", "relative_squat_ratio", "x bodyweight squat"),
            ("deadlift_ratio", "relative_deadlift_ratio", "x bodyweight deadlift"),
            ("pullups", "pullups_max_reps", "strict pull-ups"),
            ("pushups", "pushups_max_reps", "unbroken push-ups"),
        ]
        for req_key, bio_key, label in pairs:
            need = reqs.get(req_key, 0)
            have = bio_eval.get(bio_key, 0)
            if need and have < need:
                gap[req_key] = {"have": have, "need": need, "label": label}
        return gap

    # Weight each sub-factor contributes to the composite recovery score when
    # present. Renormalized over whatever subset was actually sent (a caller
    # who only sends sleep_hours still gets a sensible composite - sleep just
    # ends up carrying its full relative weight rather than being diluted by
    # missing fields defaulting to "neutral").
    _RECOVERY_WEIGHTS = {"sleep": 0.35, "soreness": 0.20, "stress": 0.15, "energy": 0.15, "motivation": 0.15}

    @classmethod
    def _compute_recovery(cls, flat_readiness: int, inputs: Optional[ReadinessInputs]) -> Dict:
        """Turns the readiness slider plus (optionally) a sleep/soreness/stress/
        energy/motivation breakdown into one recovery score and a couple of
        actionable flags. With no `inputs` at all this degrades exactly to the
        old behavior (the flat slider value, no flags) - nothing before this
        change gets a different result.
        """
        if inputs is None:
            return {
                "score": flat_readiness, "components": None,
                "poor_sleep": False, "high_soreness": False, "high_stress": False,
            }

        components = {}
        if inputs.sleep_hours is not None:
            # 8h -> 100, 4h or less -> 0, linear between, capped at 100 for long sleep.
            components["sleep"] = max(0.0, min(100.0, (inputs.sleep_hours - 4) / 4 * 100))
        if inputs.soreness is not None:
            components["soreness"] = (5 - inputs.soreness) / 4 * 100
        if inputs.stress is not None:
            components["stress"] = (5 - inputs.stress) / 4 * 100
        if inputs.energy is not None:
            components["energy"] = (inputs.energy - 1) / 4 * 100
        if inputs.motivation is not None:
            components["motivation"] = (inputs.motivation - 1) / 4 * 100

        if not components:
            return {
                "score": flat_readiness, "components": None,
                "poor_sleep": False, "high_soreness": False, "high_stress": False,
            }

        total_weight = sum(cls._RECOVERY_WEIGHTS[k] for k in components)
        composite = sum(components[k] * cls._RECOVERY_WEIGHTS[k] for k in components) / total_weight

        # Blend with the flat slider rather than replacing it outright - the slider
        # still carries the person's own overall gut-check even when they've also
        # filled in specifics (e.g. "I know my sleep/soreness look fine but I just
        # feel flat today").
        score = round(0.7 * composite + 0.3 * flat_readiness)
        score = max(1, min(100, score))

        return {
            "score": score,
            "components": {k: round(v) for k, v in components.items()},
            "poor_sleep": inputs.sleep_hours is not None and inputs.sleep_hours < 6,
            "high_soreness": inputs.soreness is not None and inputs.soreness >= 4,
            "high_stress": inputs.stress is not None and inputs.stress >= 4,
        }

    @staticmethod
    def _recovery_label(score: int) -> str:
        if score >= 80:
            return "Primed - ready for heavy training"
        if score >= 60:
            return "Ready - normal training"
        if score >= 40:
            return "Moderate - train smart, watch your top sets"
        return "Deload - prioritize recovery today"

    @staticmethod
    def _prescribe_volume(
        data: Dict, readiness_factor: float, deload: bool, poor_sleep: bool = False,
        conditioning_emphasis: str = "Mixed",
    ) -> Dict:
        """Turns a bare exercise definition into an actual sets/reps/load prescription.

        This is intentionally simple (it's a rules engine, not a coach), but it reacts to
        difficulty, category and today's readiness instead of returning a single flat
        "intensity factor" the old engine produced regardless of what the movement was.
        `poor_sleep` specifically trims heavy compound-lift intensity even on a day
        that isn't in overall deload range - a coach backs off the big bar lifts on
        bad sleep well before overall readiness collapses to 40%.
        `conditioning_emphasis` picks which energy system a Conditioning/Jump/Power
        exercise's work:rest interval is actually built around - see
        schemas.CONDITIONING_EMPHASES for what each one means.
        """
        category = data.get("category", "")
        movement_pattern = data.get("movement_pattern", "")
        equipment_lower = data.get("equipment", "Bodyweight").lower()
        difficulty = data.get("difficulty", 1)
        reqs = data.get("strength_requirements", {})
        is_loaded_strength = category in {
            "Horizontal Push", "Vertical Push", "Horizontal Pull", "Vertical Pull", "Squat", "Hinge",
        }

        if deload:
            sets = 2
        elif difficulty >= 4:
            sets = 5
        elif difficulty >= 3:
            sets = 4
        else:
            sets = 3

        # Push-Ups, Pull-Ups, Dips, Pistol Squats, Ring Rows, and their
        # progressions/static-hold variants (Front Lever, Planche, Passive
        # Dead Hang, Wall Sit, Human Flag...) all carry one of the six
        # "loaded strength" categories above because that's genuinely the
        # movement-pattern family they belong to - but there's no barbell,
        # dumbbell, or machine involved, so "X reps @ Y% of 1RM" has
        # nothing to actually reference. That "% 1RM" load previously got
        # generated anyway, purely from the exercise's difficulty rating,
        # completely disconnected from any real max the person has - it
        # showed up as e.g. "Negative Pull-Up: 3x6 reps @ 66% 1RM" and
        # "Passive Dead Hang: 3x8 reps @ 60% 1RM" (a static hold prescribed
        # in reps at all, on top of the fake load). Bodyweight-equipment
        # work now gets routed here instead: a genuine hold-time
        # prescription for anything whose movement_pattern is actually
        # "Isometric" (same hold-based format Core/Grip work already
        # uses), reps-only for everything else - no fabricated load %.
        _BODYWEIGHT_ONLY_EQUIPMENT = {"bodyweight", "pull-up bar", "rings", "suspension trainer", "parallel bars"}
        if is_loaded_strength and equipment_lower in _BODYWEIGHT_ONLY_EQUIPMENT:
            if movement_pattern == "Isometric":
                hold_s = round((15 + difficulty * 10) * (0.7 + 0.3 * readiness_factor))
                if deload:
                    hold_s = round(hold_s * 0.7)
                return {"type": "isometric", "sets": sets, "hold_seconds": hold_s, "rest_seconds": 60}
            reps = max(3, 15 - difficulty * 2)
            prescription = {
                "type": "strength_bodyweight",
                "sets": sets,
                "reps": reps,
                "rest_seconds": 90 if difficulty <= 2 else 150,
            }
            if difficulty >= 4:
                prescription["note"] = (
                    "Advanced bodyweight skill - prioritize clean reps over chasing more; "
                    "add reps before progressing to a harder variation."
                )
            return prescription

        if is_loaded_strength:
            base_pct = 55 + difficulty * 7
            load_pct_1rm = round(min(92, max(40, base_pct * (0.8 + 0.2 * readiness_factor))))
            # Bad sleep specifically caps intensity on the heavier compounds (difficulty
            # 3+) even when overall readiness/deload_mode wouldn't otherwise trigger it -
            # this is the "chest soreness / bad sleep -> lighter today" behavior a flat
            # readiness-only multiplier can't express, since it treats every exercise the
            # same regardless of how CNS-demanding it actually is.
            sleep_adjusted = poor_sleep and difficulty >= 3 and not deload
            if sleep_adjusted:
                load_pct_1rm = round(max(40, load_pct_1rm * 0.92))
                sets = max(2, sets - 1)
            reps = max(3, 14 - difficulty * 2 - int(load_pct_1rm / 15))
            prescription = {
                "type": "strength",
                "sets": sets,
                "reps": reps,
                "load_pct_1rm": load_pct_1rm,
                "rest_seconds": 90 if difficulty <= 2 else 150,
            }
            if sleep_adjusted:
                prescription["sleep_adjusted"] = True
                prescription["note"] = "Load trimmed for poor sleep - this is a CNS-demanding lift."
            return prescription

        if category in {"Conditioning", "Jump", "Power"}:
            if conditioning_emphasis == "Alactic":
                # Phosphagen system: short max-effort bursts, near-full recovery
                # so output quality never degrades rep to rep (a coach would
                # never let these turn into a lactic-burn set).
                work_s = round((5 + difficulty * 2) * (0.85 + 0.15 * readiness_factor))
                rest_s = round(work_s * (6 if not deload else 8))
            elif conditioning_emphasis == "Aerobic":
                # Steady-state / long intervals: rest stays short relative to
                # work so heart rate never fully recovers between efforts.
                work_s = round((45 + difficulty * 15) * (0.7 + 0.3 * readiness_factor))
                rest_s = round(work_s * (0.4 if not deload else 0.7))
            elif conditioning_emphasis == "Lactic":
                # Glycolytic "burn" zone: sustained high output with
                # incomplete recovery.
                work_s = round((20 + difficulty * 10) * (0.7 + 0.3 * readiness_factor))
                rest_s = round(work_s * (1.3 if not deload else 2.2))
            else:  # "Mixed" - original difficulty-only formula, unchanged behavior
                work_s = round((15 + difficulty * 8) * (0.7 + 0.3 * readiness_factor))
                rest_s = round(work_s * (1.5 if not deload else 2.5))
            prescription = {
                "type": "conditioning",
                "sets": sets,
                "work_seconds": work_s,
                "rest_seconds": rest_s,
            }
            if conditioning_emphasis != "Mixed":
                prescription["energy_system"] = conditioning_emphasis
            return prescription

        if category == "Carry":
            distance_m = round((25 + difficulty * 10) * (0.7 + 0.3 * readiness_factor))
            return {"type": "carry", "sets": sets, "distance_meters": distance_m, "rest_seconds": 90}

        if category in {"Core", "Grip"}:
            hold_s = round((15 + difficulty * 10) * (0.7 + 0.3 * readiness_factor))
            return {"type": "isometric", "sets": sets, "hold_seconds": hold_s, "rest_seconds": 60}

        # Sport specific / throws / strikes / complexes - technical quality over fatigue
        reps = max(4, 10 - difficulty)
        return {"type": "technical", "sets": sets, "reps": reps, "rest_seconds": 120}

    # How close to the top score a candidate has to be to count as "also a
    # reasonable pick" for rotation purposes. 12% keeps rotation among
    # exercises a coach would genuinely consider interchangeable - it won't
    # swap a clearly-best lift for a clearly-worse one just for variety.
    _VARIETY_BAND = 0.12

    # _select_role_balanced used to force *something* into every role slot
    # in ROLE_ORDER as long as anything at all qualified for it - even the
    # single worst-scoring exercise in the entire session. In practice this
    # surfaced worst when equipment/sport combinations left a role with only
    # one thin, badly-matched candidate: e.g. a bodyweight-only Judo session
    # has no grappling-relevant Conditioning finisher, so the engine forced
    # in "Shadow Boxing Rounds" (a Boxing-specific striking drill, authored
    # sport_priority 40/Judo, blended score ~25) ahead of exercises the same
    # session had already picked at 55-75 - a real coach would rather run a
    # second strength/accessory set than bolt on an off-discipline drill
    # just to fill a role checkbox. A role now only gets force-filled if its
    # best candidate actually clears a quality bar (an absolute floor, and a
    # floor relative to the best score anywhere else in this same session);
    # otherwise that slot is left to the normal score-ranked backfill below,
    # which pulls from every role's leftovers - so the seat still gets
    # filled, just with whatever is genuinely the next-best exercise for
    # this person's sport/equipment/level, not the weakest thing that
    # happened to be the only option in one specific role bucket.
    _ROLE_FILL_ABS_FLOOR = 30
    _ROLE_FILL_RELATIVE_FLOOR = 0.5

    @classmethod
    def _pick_with_variety(
        cls, candidates: List[Dict], recent_ids: set, rng: random.Random,
    ) -> Dict:
        """Picks one exercise from a role's score-sorted candidate list.

        Previously this was always candidates[0] - deterministic, so calling
        the engine again with the same filters (same sport/equipment/
        injuries/level) always returned the exact same exercise. That's
        correct for a single session, but it's *why* multi-week programs
        (program_builder.py calls this once per week per day-type with
        identical filters) came back with the same "Full Body A" exercises
        in week 4 as week 1 - there was never any mechanism that could
        produce a different answer.

        Fix: find every candidate within _VARIETY_BAND of the top score
        (the pool a coach would genuinely call "interchangeable" for this
        slot), prefer ones NOT in `recent_ids` (what the last call already
        used), and choose among those with a seeded RNG so the same seed
        always reproduces the same pick (deterministic per call, varied
        across calls) rather than picking randomly every single time.
        """
        if not candidates:
            return None
        top_score = candidates[0]["sport_priority_score"]
        floor = top_score * (1 - cls._VARIETY_BAND)
        tied = [c for c in candidates if c["sport_priority_score"] >= floor]
        fresh = [c for c in tied if c["id"] not in recent_ids]
        pool = fresh if fresh else tied
        return rng.choice(pool)

    # How many exercises of the same `category` (movement-pattern family -
    # Horizontal Push, Full Body, Vertical Pull, etc.) the backfill loop
    # below will stack into one session before it starts avoiding that
    # category. The one-per-role pass already guarantees the 7 role slots
    # get filled with genuinely different job assignments; without this
    # cap, any *extra* slots beyond that (a longer session, or a role that
    # got skipped by the quality floor above) were filled purely by raw
    # score across the whole remaining pool, which could - and did -
    # stack multiple near-identical high-scoring movements into one
    # session (e.g. three separate explosive kettlebell drills: Windmill,
    # Flip, and Tactical Juggle, all "Full Body"/ballistic, while the
    # session had zero squat, hinge, or horizontal-push work). 2 keeps
    # legitimate intentional pairs (a primary bench press + a secondary
    # incline press both being "Horizontal Push" is completely normal
    # programming) while stopping a third and beyond from crowding out
    # other movement patterns the session is otherwise missing entirely.
    _BACKFILL_MAX_PER_CATEGORY = 2

    # `programming_role` groups exercises by the JOB they do in a session
    # (Primary Strength, Accessory, ...), not by WHICH movement pattern they
    # train - and the one-per-role pass above only ever takes a single
    # "Primary Strength" pick and a single "Accessory / Hypertrophy" pick
    # across all six loaded-strength categories combined (Squat, Hinge,
    # Horizontal Push, Horizontal Pull, Vertical Push, Vertical Pull). That's
    # how a real session could satisfy every role slot and still come back
    # with two squat variations and zero hinge work, or all pressing and no
    # pulling, while "Power & Explosive" quietly went to a single jump/throw
    # and nothing else. A coach programming for ANY sport - grappling,
    # striking, field sport, whatever - reaches for a vertical push AND
    # pull, a horizontal push AND pull, a hinge, a squat pattern, and an
    # explosive/ballistic movement (jump, Olympic-lift variant, medball
    # throw) before calling a session balanced. This list is what the
    # coverage pass right after role-selection tops up, one pattern at a
    # time, only when a session's target_categories/limit actually leaves
    # room for it and a genuinely qualified candidate exists - it never
    # forces in a bad exercise just to check a box (same _ROLE_FILL floor
    # as everything else), and WHICH exercise wins each pattern is still
    # whatever scores highest for this person's specific sport, since
    # sport_priority_score already bakes in that sport's own movement-
    # pattern emphasis (sport_profiles.movement_emphasis_multiplier).
    # Order matters here: interleaved lower/upper, push/pull rather than
    # grouped (all lower-body patterns first) so that even a short session
    # whose slot budget can't fit all eight still comes away with a spread
    # across the body instead of front-loading e.g. Squat+Hinge and running
    # out of room before an upper-body pull or push ever gets picked.
    _COVERAGE_PATTERNS = [
        "Squat", "Horizontal Push", "Vertical Pull",
        "Hinge", "Vertical Push", "Horizontal Pull",
        "Power", "Jump",
    ]

    # Roles handled by the per-role pass below, in ROLE_ORDER's coaching
    # sequence, MINUS Primary Strength / Accessory - those two both draw
    # from the same six loaded-strength categories the coverage pass now
    # owns (see _COVERAGE_PATTERNS), and picking just one exercise per role
    # from that combined bucket is exactly what let a session end up all-
    # squat-no-hinge or all-press-no-pull despite "filling" both role slots.
    # The coverage pass below replaces that job with per-pattern picks;
    # anything it doesn't use still gets a fair shot in the generic backfill
    # afterwards (still labeled Primary Strength/Accessory, still capped by
    # _BACKFILL_MAX_PER_CATEGORY), so no candidate is actually excluded -
    # just no longer limited to one combined pick before pattern coverage
    # has had its turn.
    _STRUCTURAL_ROLES = [
        r for r in ROLE_ORDER if r not in ("Primary Strength", "Accessory / Hypertrophy")
    ]

    @classmethod
    def _select_role_balanced(
        cls,
        prescribed_exercises: List[Dict],
        limit: int,
        recent_exercise_ids: Optional[set] = None,
        variety_seed: int = 0,
    ) -> List[Dict]:
        """Trims a qualifying-exercise pool to `limit` while keeping role
        variety instead of just keeping the first N by score - a session
        capped at 6 exercises should still look like a session (something
        primary, something accessory, something conditioning) rather than
        6 near-duplicate accessory movements that happened to score highest.

        Also rotates among near-tied top candidates per role (see
        `_pick_with_variety`) so the same request run again - or the same
        day-slot run again next week in a program - doesn't mechanically
        return the identical exercise list every time.
        """
        recent_exercise_ids = recent_exercise_ids or set()
        rng = random.Random(variety_seed)

        by_role: Dict[str, List[Dict]] = {}
        for ex in prescribed_exercises:
            by_role.setdefault(ex["programming_role"], []).append(ex)
        for role_list in by_role.values():
            role_list.sort(key=lambda x: -x["sport_priority_score"])

        # The floor a role's best candidate has to clear to be worth forcing
        # into the session at all - see the class docstring above. Relative
        # to this session's own top score, so a request where nothing
        # scores especially high (a thin sport/equipment match overall)
        # doesn't get every role wiped out - only a role whose best option
        # is genuinely an outlier-bad pick next to what the rest of the
        # session already found.
        session_top_score = max(
            (ex["sport_priority_score"] for ex in prescribed_exercises), default=0
        )
        role_floor = max(cls._ROLE_FILL_ABS_FLOOR, session_top_score * cls._ROLE_FILL_RELATIVE_FLOOR)

        selected: List[Dict] = []
        selected_ids = set()
        category_counts: Dict[str, int] = {}
        for role in cls._STRUCTURAL_ROLES:
            candidates = by_role.get(role, [])
            if candidates and len(selected) < limit and candidates[0]["sport_priority_score"] >= role_floor:
                pick = cls._pick_with_variety(candidates, recent_exercise_ids, rng)
                selected.append(pick)
                selected_ids.add(pick["id"])
                category_counts[pick.get("category")] = category_counts.get(pick.get("category"), 0) + 1

        # Movement-pattern coverage pass - see _COVERAGE_PATTERNS docstring
        # above. Runs after the one-per-role pass (which already grabbed
        # whatever it found for Primary Strength/Accessory/Power & Explosive)
        # and before the generic score-only backfill, so any of the eight
        # fundamental patterns that role-selection happened to skip still
        # gets a genuine shot at a session slot - grouped by the exercise's
        # own `category` field, same quality floor, same recency-aware
        # variety pick as every other selection in this method.
        by_category: Dict[str, List[Dict]] = {}
        for ex in prescribed_exercises:
            by_category.setdefault(ex.get("category"), []).append(ex)
        for cat_list in by_category.values():
            cat_list.sort(key=lambda x: -x["sport_priority_score"])

        for pattern in cls._COVERAGE_PATTERNS:
            if len(selected) >= limit:
                break
            if category_counts.get(pattern, 0) > 0:
                continue  # already represented by the role pass above
            candidates = [c for c in by_category.get(pattern, []) if c["id"] not in selected_ids]
            if candidates and candidates[0]["sport_priority_score"] >= role_floor:
                pick = cls._pick_with_variety(candidates, recent_exercise_ids, rng)
                selected.append(pick)
                selected_ids.add(pick["id"])
                category_counts[pattern] = category_counts.get(pattern, 0) + 1

        remaining = [ex for ex in prescribed_exercises if ex["id"] not in selected_ids]
        remaining.sort(key=lambda x: -x["sport_priority_score"])
        # Fill the rest with the same recency-aware rotation, one slot at a
        # time (so each pick can react to what the previous pick already
        # used) - now also preferring categories that aren't already
        # stacked up, per _BACKFILL_MAX_PER_CATEGORY above.
        while remaining and len(selected) < limit:
            under_cap = [
                ex for ex in remaining
                if category_counts.get(ex.get("category"), 0) < cls._BACKFILL_MAX_PER_CATEGORY
            ]
            pool = under_cap if under_cap else remaining
            pick = cls._pick_with_variety(pool, recent_exercise_ids | selected_ids, rng)
            selected.append(pick)
            selected_ids.add(pick["id"])
            category_counts[pick.get("category")] = category_counts.get(pick.get("category"), 0) + 1
            remaining = [ex for ex in remaining if ex["id"] != pick["id"]]

        return selected

    @staticmethod
    def _resolve_injury_severity(user_injuries: set) -> Dict[str, int]:
        """Turn the user's selected injury strings into a {joint: worst_severity} map
        using INJURY_TAXONOMY. If someone has two flagged injuries on the same joint
        (unlikely but possible), the more severe one wins - a joint is only ever as
        safe as its worst injury. Strings that don't match a taxonomy entry (e.g. a
        raw joint name like "Knee", or a legacy flat tag like "Tennis Elbow" typed
        exactly as it appears in injuries_to_avoid) are simply skipped here and left
        for the existing literal-tag contraindication check further down, so nothing
        that worked before this taxonomy existed stops working now."""
        taxonomy_lower = {name.lower(): info for name, info in INJURY_TAXONOMY.items()}
        joint_severity: Dict[str, int] = {}
        for inj in user_injuries:
            entry = taxonomy_lower.get(inj)
            if entry is None:
                continue
            joint = entry["joint"]
            severity = entry["severity"]
            joint_severity[joint] = max(joint_severity.get(joint, 0), severity)
        return joint_severity

    def generate_session(self, request: WorkoutRequest):
        # Work on a private copy so custom_progressions never bleeds into other requests
        # or persists across them (see _apply_overrides docstring).
        dag = copy.deepcopy(self.base_dag) if request.custom_progressions else self.base_dag

        if request.custom_progressions:
            self._apply_overrides(dag, request.custom_progressions)

        bio_eval = self.evaluate_biometrics_and_strength(request.biometrics)
        user_injuries = {inj.strip().lower() for inj in request.injuries}
        # {joint_name: worst_severity_tier} for any user injury that matches the taxonomy -
        # this is what makes exclusion severity-aware instead of a blanket joint ban.
        injury_joint_severity = self._resolve_injury_severity(user_injuries)
        user_equipment = {eq.strip().lower() for eq in request.equipment_available}
        user_level_rank = LEVEL_RANK.get(request.experience_level, 2)

        # Recovery/fatigue: with no readiness_inputs this is exactly the old flat
        # slider behavior (see _compute_recovery docstring for why that's safe).
        recovery = self._compute_recovery(request.readiness, request.readiness_inputs)
        effective_readiness = recovery["score"]
        readiness_factor = effective_readiness / 100.0
        poor_sleep = recovery["poor_sleep"]
        # Below 40% effective readiness (or a stand-alone 5/5 soreness report, which
        # a merely-averaged composite could otherwise mask) the session auto-switches
        # to a deload: shorter, lighter, capped at moderate difficulty. This used to
        # just multiply intensity by readiness with no floor or ceiling, which could
        # still hand out max-effort barbell work at 5% readiness.
        max_soreness = bool(request.readiness_inputs and request.readiness_inputs.soreness == 5)
        deload_mode = effective_readiness < 40 or max_soreness

        prescribed_exercises = []
        excluded_exercises = []
        # Built once per request (not per exercise) - find_alternatives searches this
        # to recommend a safer swap instead of only reporting that something's excluded.
        all_exercises_by_id = {n: d for n, d in dag.nodes(data=True)}

        # Custom mode: evaluate exactly the exercises the person picked (in their
        # order) instead of the whole database - same safety checks below still
        # apply per exercise, so an unsafe pick still surfaces in excluded_exercises
        # with why, it's just scoped to their list rather than everything qualified.
        custom_mode = request.mode == "custom" and bool(request.selected_exercise_ids)
        unknown_custom_ids: List[str] = []
        if custom_mode:
            seen = set()
            node_pool = []
            for raw_id in request.selected_exercise_ids:
                cid = raw_id.strip()
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                if cid in all_exercises_by_id:
                    node_pool.append((cid, all_exercises_by_id[cid]))
                else:
                    unknown_custom_ids.append(cid)
        else:
            node_pool = list(dag.nodes(data=True))

        # Session-focus filter (Program Builder support): when a request scopes
        # itself to specific categories/muscles (e.g. a "Push" day), exercises
        # outside that focus are skipped entirely up front - they're not
        # "excluded for a reason" (that list is for equipment/injury/strength/
        # level reasons a person can act on), they're just not part of what
        # this particular session is about. None/None (the default for every
        # existing caller) means no filtering at all - unchanged behavior.
        # Not applied in custom mode - an explicit exercise pick shouldn't be
        # silently dropped by a focus filter the person never set for it.
        has_focus_filter = (not custom_mode) and bool(request.target_categories or request.target_muscles)

        for node_id, data in node_pool:
            if has_focus_filter:
                category = data.get("category")
                movement_pattern = data.get("movement_pattern")
                ex_muscles = set(data.get("primary_muscles", [])) | set(data.get("secondary_muscles", []))
                matches_category = bool(
                    request.target_categories
                    and (category in request.target_categories or movement_pattern in request.target_categories)
                )
                matches_muscle = bool(
                    request.target_muscles and ex_muscles & set(request.target_muscles)
                )
                if not (matches_category or matches_muscle):
                    continue

            eq = data.get("equipment", "Bodyweight")
            joint_stress_raw = data.get("joint_stress", [])
            joint_stress = {j.lower() for j in joint_stress_raw}
            injuries_to_avoid = {i.lower() for i in data.get("injuries_to_avoid", [])}
            reqs = data.get("strength_requirements", {})
            ex_level_rank = LEVEL_RANK.get(data.get("experience_level", "Intermediate"), 2)
            difficulty = data.get("difficulty", 1)

            has_equipment = eq.lower() == "bodyweight" or eq.lower() in user_equipment

            contraindications = sorted(user_injuries & (joint_stress | injuries_to_avoid))

            # Four-tier injury risk check (v4.0): a joint the user has a taxonomy-matched
            # injury in isn't just "off" or "on". We classify every joint this exercise
            # stresses into safe / caution / high_risk / contraindicated (see
            # injury_taxonomy.classify_injury_risk) and block on the first one that lands
            # in the excluded half (high_risk or contraindicated) - which is exactly the
            # same allowed/excluded boundary v3.0 used, just with the reasoning kept.
            # "caution" joints are still allowed but recorded so the person (and the UI)
            # can see the exercise is at the edge of what that injury tolerates.
            severity_blocked_joint = None
            blocked_tier = None
            caution_joints = []
            for joint_name in joint_stress_raw:
                severity = injury_joint_severity.get(joint_name)
                if severity is None:
                    continue
                tier = classify_injury_risk(severity, difficulty)
                if tier == "caution":
                    caution_joints.append(joint_name)
                elif tier in ("high_risk", "contraindicated"):
                    severity_blocked_joint = joint_name
                    blocked_tier = tier
                    break

            is_safe = len(contraindications) == 0 and severity_blocked_joint is None

            strength_qualified = (
                bio_eval["relative_bench_ratio"] >= reqs.get("bench_ratio", 0.0)
                and bio_eval["relative_squat_ratio"] >= reqs.get("squat_ratio", 0.0)
                and bio_eval["relative_deadlift_ratio"] >= reqs.get("deadlift_ratio", 0.0)
                and bio_eval["pullups_max_reps"] >= reqs.get("pullups", 0)
                and bio_eval["pushups_max_reps"] >= reqs.get("pushups", 0)
            )

            # Experience level is now actually used: an exercise is allowed at most one
            # rung above the user's stated level, even if their entered numbers happen to
            # clear the raw strength thresholds. Previously `experience_level` was accepted
            # by the API and shown in the UI but never once read by the engine.
            level_ok = ex_level_rank <= user_level_rank + LEVEL_STRETCH

            if deload_mode and data.get("difficulty", 1) >= 4:
                level_ok = False

            # Sport transfer is no longer just the hand-authored sport_priority number -
            # it's blended with a weighted overlap of this exercise's own derived
            # athletic_qualities against the sport's quality profile (sport_profiles.py),
            # so the ranking is grounded in something explainable rather than a single
            # opaque authored score.
            # blended_transfer_score is "how good is this exercise's overall
            # quality profile for this sport"; movement_emphasis_multiplier
            # is the separate "is this specifically the push/pull/hinge/etc.
            # pattern this sport actually needs more of" signal (see
            # sport_profiles.py docstring - a Boxing session should skew
            # toward pressing, a Judo session toward pulling, even when both
            # exercises score similarly on raw quality overlap).
            sport_score = round(
                blended_transfer_score(data, request.sport) * movement_emphasis_multiplier(data, request.sport)
                * level_fit_multiplier(ex_level_rank, user_level_rank)
            )
            sport_score = max(0, min(100, sport_score))
            role, role_rationale = classify_programming_role(data)

            if has_equipment and is_safe and strength_qualified and level_ok:
                prescribed = {
                    "id": node_id,
                    "name": data.get("name", node_id),
                    "category": data.get("category"),
                    "movement_pattern": data.get("movement_pattern"),
                    "difficulty": data.get("difficulty"),
                    "experience_level": data.get("experience_level"),
                    "experience_level_fit": level_fit_label(ex_level_rank, user_level_rank),
                    "equipment": eq,
                    "sport_priority_score": sport_score,
                    "sport_transfer_rationale": transfer_rationale(data, request.sport),
                    "programming_role": role,
                    "programming_role_rationale": role_rationale,
                    "session_order_rank": session_order_rank(role),
                    "prescription": self._prescribe_volume(
                        data, readiness_factor, deload_mode, poor_sleep, request.conditioning_emphasis
                    ),
                }
                if caution_joints:
                    prescribed["injury_caution"] = (
                        f"At the edge of what your {', '.join(sorted(caution_joints))} "
                        f"injury currently tolerates - monitor how it feels."
                    )
                # v4.0 movement/athletic-quality metadata, when present (backward compatible:
                # exercises enriched before running enrich_exercises.py simply omit these).
                for field in (
                    "movement_plane", "movement_type", "chain_type", "force_type",
                    "velocity_type", "technical_complexity", "CNS_fatigue",
                    "recovery_time_hours", "athletic_qualities",
                ):
                    if field in data:
                        prescribed[field] = data[field]
                prescribed_exercises.append(prescribed)
            else:
                reasons = []
                if not has_equipment:
                    reasons.append(f"Missing equipment: {eq}")
                if contraindications:
                    reasons.append(f"Injury contraindication: {', '.join(contraindications)}")
                if severity_blocked_joint:
                    severity = injury_joint_severity[severity_blocked_joint]
                    tier_label = {1: "mild", 2: "moderate", 3: "severe"}.get(severity, "flagged")
                    reasons.append(
                        f"Too demanding for a {tier_label} {severity_blocked_joint} injury "
                        f"(difficulty {difficulty}, risk tier: {blocked_tier})"
                    )
                if not strength_qualified:
                    reasons.append("Below relative-strength threshold")
                if not level_ok:
                    reasons.append(f"Above your experience level ({data.get('experience_level')})")

                excluded = {
                    "id": node_id,
                    "name": data.get("name", node_id),
                    "reasons": reasons,
                }

                if severity_blocked_joint:
                    excluded["risk_tier"] = blocked_tier
                    alts = find_alternatives(
                        data, all_exercises_by_id, injury_joint_severity,
                        user_equipment=user_equipment,
                    )
                    if alts:
                        severity = injury_joint_severity.get(severity_blocked_joint, 0)
                        excluded["alternatives"] = [
                            {
                                "id": a["id"],
                                "name": a.get("name", a["id"]),
                                "equipment": a.get("equipment", "Bodyweight"),
                                # Whether the person's own equipment list covers this
                                # swap right now - a belt squat swap is only actually
                                # useful to surface first if they have a belt squat.
                                "equipment_available": (
                                    a.get("equipment", "Bodyweight").lower() == "bodyweight"
                                    or a.get("equipment", "").lower() in user_equipment
                                ),
                                "difficulty": a.get("difficulty"),
                                # Not just "doesn't aggravate it" - actively trains that
                                # joint's stability at a load the injury can tolerate.
                                "rehab_pick": is_rehab_candidate(a, severity_blocked_joint, severity),
                            }
                            for a in alts
                        ]

                    # Combat Sports & Rugby S&C Manual, Part 7.7: if this
                    # exercise/joint pair is one the manual specifically
                    # names (e.g. Back Squat + Lower Back -> Belt Squat),
                    # attach that named guidance alongside the generic
                    # live-search alternatives above - same underlying
                    # joint-clearance logic, but with the manual's own
                    # coach-readable rationale attached.
                    manual_swaps = part7_recommended_swap(
                        data, all_exercises_by_id, severity_blocked_joint,
                    )
                    if manual_swaps:
                        excluded["manual_guidance"] = manual_swaps

                # DAG payoff: if the only thing blocking this exercise is strength, tell the
                # user exactly what's missing and, if its regression (predecessor in the
                # graph) is something they CAN already do, point them at it directly. This
                # is the actual reason the engine builds a graph instead of a flat list -
                # previously the DAG was built and then never read from again.
                if has_equipment and is_safe and level_ok and not strength_qualified:
                    gap = self._strength_gap(bio_eval, reqs)
                    excluded["progress_needed"] = gap
                    prereqs = list(dag.predecessors(node_id))
                    unlocked_prereq = next(
                        (p for p in prereqs if any(pe["id"] == p for pe in prescribed_exercises)),
                        None,
                    )
                    if unlocked_prereq:
                        excluded["next_step"] = (
                            f"Build up on '{dag.nodes[unlocked_prereq].get('name', unlocked_prereq)}' first"
                        )

                excluded_exercises.append(excluded)

        # Any custom-mode ids that don't exist in the database at all (typo, stale
        # id from a previous data version) - reported distinctly from an id that
        # exists but got excluded for a safety reason.
        for bad_id in unknown_custom_ids:
            excluded_exercises.append({
                "id": bad_id,
                "name": bad_id,
                "reasons": ["Unknown exercise id - not found in the current database"],
            })

        # Session-length cap (Program Builder support): when a request asks for
        # only N exercises, keep the pool role-balanced rather than an arbitrary
        # truncation - one exercise per programming-role phase first (highest
        # score in that role), then fill remaining slots by score across
        # whatever's left. Exercises trimmed here still qualified on every
        # safety/equipment/strength check; they're just not in this session
        # for space reasons, so they're not added to excluded_exercises.
        # Skipped in custom mode - the person already chose exactly which
        # exercises they want, trimming their own explicit list would be wrong.
        if (not custom_mode) and request.exercise_limit is not None and len(prescribed_exercises) > request.exercise_limit:
            recent_ids = {i.strip() for i in (request.exclude_exercise_ids or [])}
            prescribed_exercises = self._select_role_balanced(
                prescribed_exercises, request.exercise_limit,
                recent_exercise_ids=recent_ids, variety_seed=request.variety_seed,
            )

        # Sequencing, not just filtering: within each programming-role phase (primer ->
        # skill -> power -> primary strength -> accessory -> core -> conditioning), rank
        # by sport transfer. Across phases, always respect the coaching order - a
        # high-transfer conditioning finisher still runs last, never before the main lift.
        prescribed_exercises.sort(key=lambda x: (x["session_order_rank"], -x["sport_priority_score"]))

        session_structure = []
        for role in ROLE_ORDER:
            phase_exercises = [e for e in prescribed_exercises if e["programming_role"] == role]
            if phase_exercises:
                session_structure.append({
                    "phase": role,
                    "exercises": [e["id"] for e in phase_exercises],
                })

        # Roadmap: the top sport-relevant exercises that are locked on strength alone,
        # closest gap first, using the DAG's own strength gap data computed above.
        roadmap = sorted(
            (e for e in excluded_exercises if "progress_needed" in e and e["progress_needed"]),
            key=lambda e: (len(e["progress_needed"]), e["id"]),
        )[:5]

        return {
            "status": "success",
            "engine": "FORGE Knowledge Graph Engine v5.1",
            "mode": "custom" if custom_mode else "preset",
            "sport": request.sport,
            "experience_level": request.experience_level,
            # Advisory only - see level_check's own docstring. level_ok above
            # already ran against request.experience_level exactly as before;
            # this doesn't change which exercises got selected, it just shows
            # whether the entered numbers actually agree with that level.
            "level_check": level_check(request.experience_level, bio_eval["level_estimate"]),
            "deload_mode": deload_mode,
            "readiness_factor": round(readiness_factor, 2),
            "recovery": {
                "score": recovery["score"],
                "label": self._recovery_label(recovery["score"]),
                "components": recovery["components"],
                "poor_sleep": recovery["poor_sleep"],
                "high_soreness": recovery["high_soreness"],
                "high_stress": recovery["high_stress"],
            },
            "biometric_analysis": bio_eval,
            "session_summary": {
                "total_prescribed": len(prescribed_exercises),
                "total_excluded": len(excluded_exercises),
            },
            "prescribed_workout": prescribed_exercises,
            "session_structure": session_structure,
            "excluded_exercises": excluded_exercises,
            "progression_roadmap": roadmap,
        }


engine = ProgressionEngine()


# ==========================================
# 3. API ENDPOINTS
# ==========================================

@app.get("/api/v1/metadata")
def get_metadata():
    """Single source of truth for what the frontend can offer - derived from the same
    data file the engine filters against, so the UI's dropdowns can never fall out of
    sync with what exercises.json actually contains (previously they were hand-typed
    separately in app.py and had drifted: several equipment types and most injury tags
    in the data had no matching UI option at all)."""
    return {
        "sports": engine.all_sports,
        "equipment": engine.all_equipment,
        "injuries": engine.all_injuries,
        "injuries_grouped": grouped_injury_taxonomy(),
        "experience_levels": EXPERIENCE_LEVELS,
        "conditioning_emphases": CONDITIONING_EMPHASES,
        "training_phases": TRAINING_PHASES,
    }


@app.get("/api/v1/sports/{sport}")
def get_sport_profile(sport: str):
    """What the engine actually knows about a sport's training demands - the
    athletic-quality weights (sport_profiles.SPORT_QUALITY_PROFILES) and the
    movement-pattern bias (SPORT_MOVEMENT_EMPHASIS) that together decide why,
    e.g., a Boxing session leans toward pressing/rotational work and a Judo
    session leans toward pulling/grip work. Makes that reasoning inspectable
    instead of only visible indirectly through which exercises rank highest."""
    if sport not in engine.all_sports:
        raise HTTPException(status_code=404, detail=f"Unknown sport: {sport}")
    quality_profile = SPORT_QUALITY_PROFILES.get(sport, {})
    movement_emphasis = SPORT_MOVEMENT_EMPHASIS.get(sport, {})
    emphasized = sorted(
        ((k, v) for k, v in movement_emphasis.items() if v > 1.0),
        key=lambda kv: -kv[1],
    )
    de_emphasized = sorted(
        ((k, v) for k, v in movement_emphasis.items() if v < 1.0),
        key=lambda kv: kv[1],
    )
    return {
        "sport": sport,
        "athletic_quality_profile": quality_profile,
        "movement_pattern_emphasis": movement_emphasis,
        "prioritized_patterns": [p for p, _ in emphasized],
        "deprioritized_patterns": [p for p, _ in de_emphasized],
        "has_custom_profile": sport in SPORT_QUALITY_PROFILES or sport in SPORT_MOVEMENT_EMPHASIS,
        "recommended_split": SPORT_SPLIT_GUIDANCE.get(sport),
        # Combat Sports & Rugby S&C Manual, Part 5 - aerobic:lactic ratio,
        # gym emphasis, and weekly conditioning notes. None for sports the
        # manual doesn't cover (e.g. Rock Climbing, HYROX).
        "conditioning_profile": sport_conditioning_profile(sport) or None,
    }


@app.get("/api/v1/conditioning-protocols")
def get_conditioning_protocols():
    """Sport-agnostic reference material from the Combat Sports & Rugby S&C
    Manual: what aerobic vs. lactic conditioning actually is (Part 2), the
    pick-one-of-these aerobic and lactic session menus (Part 6), the
    pre-lift warm-up protocol (Part 9.1), and the two add-ons the manual
    says apply regardless of sport or split - neck training and grip/
    forearm work (Part 1). Program-specific aerobic:lactic weighting for a
    given sport lives on /api/v1/sports/{sport} and inside
    /api/v1/generate-program's `conditioning_guidance` block instead."""
    return conditioning_reference()


@app.get("/api/v1/injury-substitutions")
def get_injury_substitutions(joint: str = ""):
    """Combat Sports & Rugby S&C Manual, Part 7.7's named issue -> typical
    culprit -> safer substitute(s) table (Lower Back, Shoulder, Knee,
    Wrist, Elbow, Hip), each substitute resolved to a real exercises.json
    id/name where the database has one. Optionally filter to one joint
    (same 8-tag vocabulary as `/api/v1/injuries/grouped`). This is the
    manual's own reference table for common training niggles - the
    per-exercise `manual_guidance` already returned when an exercise is
    excluded on generate-workout/generate-program (see
    injury_taxonomy.part7_recommended_swap) covers the same ground for a
    specific exercise/injury pair in context."""
    all_ex = engine.exercises_by_id
    rows = part7_substitution_guidance(joint or None)
    resolved = []
    for row in rows:
        by_name = {e.get("name", "").lower(): e for e in all_ex.values()}
        subs = [
            {"id": by_name[s.lower()]["id"], "name": by_name[s.lower()]["name"]}
            for s in row["safer_substitutes"] if s.lower() in by_name
        ]
        resolved.append({**row, "safer_substitutes_resolved": subs})
    return {"substitutions": resolved, "disclaimer": PART7_DISCLAIMER}


@app.get("/api/v1/training-phases")
def get_training_phases():
    """The 5 competition-calendar phases from the manual's Part 9.3
    periodization table (Off-Season through Post-Competition) - what split
    each phase points to, its volume multiplier, and its lifting/
    conditioning focus. Pass one of these ids as `training_phase` on
    POST /api/v1/generate-program to have the split and weekly volume
    follow this table instead of the plain days/goal/sport heuristic."""
    return {
        "training_phases": [
            {"id": phase_id, **phase_data}
            for phase_id, phase_data in PHASE_GUIDANCE.items()
        ]
    }


@app.get("/api/v1/exercises")
def list_exercises(search: str = "", sport: str = "", equipment: str = "", limit: int = 500):
    """Lightweight catalog for building a custom session (mode="custom") - a person
    browses/searches this instead of the engine picking for them, then sends the
    ids they want as `selected_exercise_ids`. Deliberately thin (no safety/strength
    evaluation here - that only happens once, in generate_session, against the
    actual request) so this stays fast for a live search-as-you-type UI.
    `sport` filters to exercises that have any authored sport_priority for that
    sport; `equipment` matches the exercise's own equipment field case-insensitively.
    """
    search_lower = search.strip().lower()
    equipment_lower = equipment.strip().lower()
    results = []
    for node_id, data in engine.exercises_by_id.items():
        if search_lower and search_lower not in data.get("name", "").lower():
            continue
        if sport and sport not in data.get("sport_priority", {}):
            continue
        if equipment_lower and data.get("equipment", "Bodyweight").lower() != equipment_lower:
            continue
        results.append({
            "id": node_id,
            "name": data.get("name", node_id),
            "category": data.get("category"),
            "movement_pattern": data.get("movement_pattern"),
            "equipment": data.get("equipment", "Bodyweight"),
            "difficulty": data.get("difficulty"),
            "experience_level": data.get("experience_level"),
        })
        if len(results) >= limit:
            break
    return {"count": len(results), "exercises": results}


@app.get("/api/v1/equipment")
def get_equipment_catalog():
    """Every equipment type in the database, grouped into browsable sections
    (Free Weights, Machines, Strongman, ...) with an exercise count and the
    movement categories it unlocks - what the old flat alphabetical checkbox
    list couldn't show. Lets someone see, before selecting it, that e.g.
    Kettlebell covers pushing/pulling/hinging/carrying/core (not just
    swings), or that Belt Squat is available as a squat-pattern option for
    someone avoiding axial spinal load."""
    return {"equipment": build_equipment_catalog(list(engine.exercises_by_id.values()))}


@app.get("/api/v1/injuries/grouped")
def get_injuries_grouped():
    """Same data as the `injuries_grouped` key on /api/v1/metadata, as its own
    endpoint - joint (section) -> condition (subsection) -> severity grades.
    Kept separate too so a client only interested in the injury browser
    doesn't need to pull sports/equipment along with it."""
    return grouped_injury_taxonomy()


@app.get("/api/v1/knowledge-graph/{exercise_id}")
def get_exercise_knowledge(exercise_id: str):
    """Everything the knowledge graph knows about one exercise - progressions,
    regressions, equipment substitutes, joints it stresses, which injuries it's
    a genuine rehab candidate for, and its transfer score + rationale for every
    sport in the database. This is the graph made directly inspectable, not
    just a side effect of running a full workout generation."""
    result = explain_exercise(engine.knowledge_graph, exercise_id, engine.exercises_by_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown exercise id: {exercise_id}")
    return result


@app.post("/api/v1/estimate-level")
def estimate_level(payload: UserBiometrics):
    """Independent, standalone estimate of overall training level from raw
    lift/rep-max numbers - see strength_standards.py for the standards used
    and why this exists. Meant to run *before* the person has necessarily
    committed to an experience_level: the frontend can call this once
    biometrics are entered and use the result to suggest/pre-fill the
    experience_level dropdown on the session/program wizard, while the
    person keeps final say over what's actually submitted. Doesn't set or
    change anything server-side - the same estimate also rides along inside
    generate-workout/generate-program responses as `level_check`, once an
    experience_level has actually been chosen, so a mismatch stays visible
    there too instead of only at this one-off pre-fill step."""
    return classify_strength_level(
        weight_kg=payload.weight_kg,
        bench_press_1rm=payload.bench_press_1rm or 0.0,
        squat_1rm=payload.squat_1rm or 0.0,
        deadlift_1rm=payload.deadlift_1rm or 0.0,
        pullups_max_reps=payload.pullups_max_reps or 0,
        pushups_max_reps=payload.pushups_max_reps or 0,
        sex=payload.sex,
    )


@app.post("/api/v1/generate-workout")
def generate_workout(payload: WorkoutRequest):
    try:
        return engine.generate_session(payload)
    except HTTPException:
        raise
    except Exception as e:
        # Full detail only in DEBUG - an unhandled exception's message can
        # contain internals (file paths, data shape) that shouldn't go to a
        # client by default. Still logged either way so nothing is lost.
        print(f"[generate-workout] unhandled error: {e!r}")
        detail = str(e) if settings.DEBUG else "Internal error generating workout session."
        raise HTTPException(status_code=500, detail=detail)


# ==========================================
# 4. PROGRAM BUILDER ENDPOINTS
# ==========================================

@app.get("/api/v1/splits")
def get_splits():
    """Every training split the Program Builder can generate - id, display
    name, description, and which days-per-week counts it's designed for.
    Same principle as /api/v1/metadata: derived from SPLIT_TEMPLATES itself
    so this list can't drift out of sync with what generate-program actually
    supports. `preferred_split: "auto"` on a program request picks from
    these based on days_per_week + goal (and, where it applies, the sport -
    see `recommended_for_sports` below and SPORT_SPLIT_GUIDANCE) instead of
    the caller choosing one."""
    recommended_by_split: Dict[str, List[str]] = {}
    for sport, guidance in SPORT_SPLIT_GUIDANCE.items():
        recommended_by_split.setdefault(guidance["split"], []).append(sport)
    return {
        "splits": [
            {
                "id": split_id,
                "name": template["name"],
                "description": template["description"],
                "reference": template.get("reference"),
                "supported_days_per_week": template["supported_days_per_week"],
                "recommended_for_sports": sorted(recommended_by_split.get(split_id, [])),
            }
            for split_id, template in SPLIT_TEMPLATES.items()
        ]
    }


@app.get("/api/v1/goals")
def get_goals():
    """Primary goals accepted by /api/v1/generate-program."""
    return {"goals": PRIMARY_GOALS}


@app.post("/api/v1/generate-program")
def generate_program_endpoint(payload: ProgramRequest):
    try:
        return generate_program(engine, payload)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[generate-program] unhandled error: {e!r}")
        detail = str(e) if settings.DEBUG else "Internal error generating program."
        raise HTTPException(status_code=500, detail=detail)


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
