"""
knowledge_graph.py — the actual multi-relational graph FORGE reasons over.

WHY THIS EXISTS
`main.py`'s `base_dag` is a real graph, but it only ever encodes ONE
relationship: "completing exercise A unlocks exercise B" (progressions). Every
other relationship an exercise has - which joints it loads, which injuries it's
a safe rehab pick for, which sports it transfers to and why, which exercises
substitute for it when equipment is missing - was either a flat unconnected
field on the node (`sport_priority`, `joint_stress`) or logic buried inside a
single request-handling function (`generate_session`) that nothing else could
query.

This module builds one graph with those relationships as first-class,
labeled, directed edges between typed nodes (exercise / joint / injury /
sport), so:
  - the relationships are inspectable on their own (see main.py's new
    /api/v1/knowledge-graph/{exercise_id} endpoint) instead of only visible
    as a side effect of running a full prescription request, and
  - new reasoning can be added by adding a new edge type here, instead of by
    threading more ad-hoc logic through generate_session.

EDGE TYPES
    progresses_to      exercise -> exercise   (existing progressions field)
    substitute_for      exercise <-> exercise  (declared alternatives, plus a
                        derived fallback: same movement_pattern + same/lower
                        difficulty + different equipment)
    stresses_joint      exercise -> joint      (from joint_stress)
    rehab_candidate_for exercise -> injury     (derived: low load, and the
                        exercise's own athletic_qualities show it actively
                        trains stability of the injury's joint)
    transfers_to_sport  exercise -> sport      (from sport_profiles, one edge
                        per sport with weight + rationale)

Sport-transfer and rehab-candidacy also depend on values a single request can
override (difficulty via custom_progressions), so the same scoring functions
used to build these edges are also exposed standalone for main.py to call
against live, possibly-overridden node data - the graph is the map of the
default/base relationships, not the only place the logic lives.
"""

from typing import Dict, List, Optional

import networkx as nx

from backend.services.exercise_metadata import JOINT_STABILITY_TAG
from backend.services.injury_taxonomy import INJURY_TAXONOMY, classify_injury_risk
from backend.services.programming_role import classify_programming_role
from backend.services.sport_profiles import SPORT_QUALITY_PROFILES, blended_transfer_score, transfer_rationale

# Same joint -> stability-quality-tag mapping exercise_metadata.py uses to
# award stability tags in the first place - imported directly (not re-derived
# or copy-pasted) so "this exercise builds knee stability" means the same
# thing in both places and the two can never drift apart. They previously
# WERE two separate hand-copied dicts, and had drifted: this one only had 5
# of the 8 joints exercises.json's joint_stress actually uses (missing
# Wrist, Elbow, Lower Back), which meant build_knowledge_graph() below
# silently never created joint nodes - or stresses_joint edges - for those
# three joints, and is_rehab_candidate() could never return True for an
# injury on any of them. Importing the single source of truth fixes both at
# once and makes a future edit to one module's joint list impossible to
# forget to mirror in the other.

# A rehab candidate has to be genuinely light - "technically allowed" at the
# top of an injury's difficulty ceiling isn't the same as "a good rehab
# pick". Difficulty 1-2 only.
_REHAB_DIFFICULTY_CEILING = 2
# How strongly the exercise has to train that joint's stability tag to count
# as deliberately rehabbing it, rather than merely not aggravating it.
_REHAB_QUALITY_FLOOR = 40


def is_rehab_candidate(ex: Dict, joint: str, severity: int) -> bool:
    """Is this exercise a deliberate rehab/prehab pick for an injury at this
    joint and severity - not just "allowed", but actively training the
    joint's stability at a load the injury can tolerate."""
    difficulty = ex.get("difficulty", 1)
    if difficulty > _REHAB_DIFFICULTY_CEILING:
        return False
    if classify_injury_risk(severity, difficulty) not in ("safe", "caution"):
        return False
    stability_tag = JOINT_STABILITY_TAG.get(joint)
    if not stability_tag:
        return False
    return ex.get("athletic_qualities", {}).get(stability_tag, 0) >= _REHAB_QUALITY_FLOOR


def find_substitutes(
    ex: Dict, all_exercises: Dict[str, Dict], available_equipment: Optional[set] = None, limit: int = 5
) -> List[Dict]:
    """Equipment-swap reasoning: declared alternatives first, then a derived
    fallback of exercises sharing this one's movement_pattern at the same or
    easier difficulty but different equipment - the actual "what do I do
    instead if I don't have this equipment" answer, not just a static list."""
    ex_id = ex.get("id")
    pattern = ex.get("movement_pattern")
    equipment = ex.get("equipment")
    difficulty = ex.get("difficulty", 1)

    results: List[Dict] = []
    seen = set()

    for alt_id in ex.get("alternatives", []):
        alt = all_exercises.get(alt_id)
        if not alt or alt_id in seen:
            continue
        if available_equipment is not None:
            alt_eq = (alt.get("equipment") or "Bodyweight").lower()
            if alt_eq != "bodyweight" and alt_eq not in available_equipment:
                continue
        results.append(alt)
        seen.add(alt_id)

    if len(results) < limit:
        pool = [
            c for cid, c in all_exercises.items()
            if cid != ex_id
            and cid not in seen
            and c.get("movement_pattern") == pattern
            and c.get("equipment") != equipment
            and c.get("difficulty", 1) <= difficulty
        ]
        if available_equipment is not None:
            pool = [
                c for c in pool
                if (c.get("equipment") or "Bodyweight").lower() == "bodyweight"
                or (c.get("equipment") or "").lower() in available_equipment
            ]
        pool.sort(key=lambda c: difficulty - c.get("difficulty", 1))
        results.extend(pool[: limit - len(results)])

    return results[:limit]


def build_knowledge_graph(exercises: List[Dict]) -> nx.MultiDiGraph:
    """Builds the full multi-relational graph. Node ids are namespaced by
    type (`exercise:<id>`, `joint:<name>`, `injury:<name>`, `sport:<name>`)
    so the four node types can never collide."""
    g = nx.MultiDiGraph()
    by_id = {ex["id"]: ex for ex in exercises}

    for ex in exercises:
        role, role_rationale = classify_programming_role(ex)
        g.add_node(f"exercise:{ex['id']}", type="exercise", programming_role=role,
                    programming_role_rationale=role_rationale, **ex)

    for sport in SPORT_QUALITY_PROFILES:
        g.add_node(f"sport:{sport}", type="sport")
    for joint in JOINT_STABILITY_TAG:
        g.add_node(f"joint:{joint}", type="joint")
    for injury in INJURY_TAXONOMY:
        g.add_node(f"injury:{injury}", type="injury")

    for ex in exercises:
        src = f"exercise:{ex['id']}"

        for prog_id in ex.get("progressions", []):
            if prog_id in by_id:
                g.add_edge(src, f"exercise:{prog_id}", key="progresses_to")

        for alt_id in ex.get("alternatives", []):
            if alt_id in by_id:
                g.add_edge(src, f"exercise:{alt_id}", key="substitute_for")
                g.add_edge(f"exercise:{alt_id}", src, key="substitute_for")

        for joint in ex.get("joint_stress", []):
            if f"joint:{joint}" in g:
                g.add_edge(src, f"joint:{joint}", key="stresses_joint", difficulty=ex.get("difficulty", 1))

        for injury_name, info in INJURY_TAXONOMY.items():
            if is_rehab_candidate(ex, info["joint"], info["severity"]):
                g.add_edge(src, f"injury:{injury_name}", key="rehab_candidate_for", joint=info["joint"])

        for sport in SPORT_QUALITY_PROFILES:
            score = blended_transfer_score(ex, sport)
            if score > 0:
                g.add_edge(
                    src, f"sport:{sport}", key="transfers_to_sport",
                    weight=score, rationale=transfer_rationale(ex, sport),
                )

    return g


def explain_exercise(g: nx.MultiDiGraph, ex_id: str, all_exercises: Dict[str, Dict]) -> Optional[Dict]:
    """Everything the knowledge graph knows about one exercise - the direct
    operationalization of 'exercises as nodes connected to everything else',
    made queryable instead of only used internally during prescription."""
    node = f"exercise:{ex_id}"
    if node not in g:
        return None
    data = g.nodes[node]

    progressions, substitutes, joints, rehab_for, sport_transfer = [], [], [], [], []
    for _, target, key, edata in g.out_edges(node, keys=True, data=True):
        target_name = g.nodes[target].get("name", target.split(":", 1)[1])
        if key == "progresses_to":
            progressions.append({"id": target.split(":", 1)[1], "name": target_name})
        elif key == "substitute_for":
            substitutes.append({"id": target.split(":", 1)[1], "name": target_name})
        elif key == "stresses_joint":
            joints.append({"joint": target.split(":", 1)[1], "difficulty": edata.get("difficulty")})
        elif key == "rehab_candidate_for":
            rehab_for.append({"injury": target.split(":", 1)[1], "joint": edata.get("joint")})
        elif key == "transfers_to_sport":
            sport_transfer.append({
                "sport": target.split(":", 1)[1],
                "score": edata.get("weight"),
                "rationale": edata.get("rationale"),
            })

    regressions = [
        {"id": src.split(":", 1)[1], "name": g.nodes[src].get("name", src)}
        for src, _, key in g.in_edges(node, keys=True) if key == "progresses_to"
    ]
    sport_transfer.sort(key=lambda s: s["score"], reverse=True)

    return {
        "id": ex_id,
        "name": data.get("name", ex_id),
        "programming_role": data.get("programming_role"),
        "programming_role_rationale": data.get("programming_role_rationale"),
        "progressions": progressions,
        "regressions": regressions,
        "substitutes": substitutes or [
            {"id": s["id"], "name": s.get("name", s["id"])} for s in find_substitutes(data, all_exercises)
        ],
        "joints_stressed": joints,
        "rehab_candidate_for": rehab_for,
        "sport_transfer": sport_transfer,
    }
