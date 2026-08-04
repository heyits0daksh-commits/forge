"""
add_mma_sport.py — one-time (re-runnable) migration that adds "MMA" as a
sport_priority key to every exercise in exercises.json, plus the "MMA"
quality/movement profiles in backend/services/sport_profiles.py (already
added by hand - this script only touches the data file).

WHY DERIVED, NOT HAND-AUTHORED
Every other sport's sport_priority number was hand-typed per exercise. MMA is
a genuine hybrid of sports the data already scores (striking: Boxing, Muay
Thai; grappling: Wrestling, BJJ, Judo), so instead of hand-typing a 13th
opinion for all ~443 exercises, this derives it as a weighted blend of
whichever of those five an exercise already has a score for - the same
"encode the reasoning once, derive the numbers" principle sport_profiles.py
itself uses for the quality-overlap half of blended_transfer_score.

Exercises with none of the five component sports scored (e.g. a pure
isolation accessory movement) get no MMA key at all, same as they have no
Boxing/Wrestling/etc. key - "not scored for this sport" stays meaningfully
different from "scored zero for this sport".

Safe to re-run: MMA is recomputed from the component sports every time, never
accumulated onto a previous run's value.
"""
import json
import shutil
from pathlib import Path

# Resolved directly (not via backend.core.config.settings) so this script has
# zero dependency on pydantic being installed - it only ever touches the data
# file, same paths settings.py itself points at by default.
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "exercises.json"
BACKUP_DIR = ROOT / "data" / "backups"
BACKUP = BACKUP_DIR / "exercises_pre_mma_backup.json"

# Striking contributes slightly more than grappling because a fighter spends
# more total live rounds standing and striking than in any single grappling
# exchange, but grappling is still weighted heavily - neglecting it is exactly
# the "exploitable hole" MMA's movement-emphasis table is designed to avoid.
COMPONENT_WEIGHTS = {
    "Boxing": 0.28,
    "Muay Thai": 0.20,
    "Wrestling": 0.24,
    "BJJ": 0.16,
    "Judo": 0.12,
}


def derive_mma_score(sport_priority: dict) -> int | None:
    present = {sport: sport_priority[sport] for sport in COMPONENT_WEIGHTS if sport in sport_priority}
    if not present:
        return None
    total_weight = sum(COMPONENT_WEIGHTS[s] for s in present)
    weighted = sum(present[s] * COMPONENT_WEIGHTS[s] for s in present) / total_weight
    return round(max(0, min(100, weighted)))


def main():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, BACKUP)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for ex in data["exercises"]:
        sport_priority = ex.get("sport_priority", {})
        mma_score = derive_mma_score(sport_priority)
        if mma_score is not None:
            sport_priority["MMA"] = mma_score
            ex["sport_priority"] = sport_priority
            updated += 1

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Added MMA sport_priority to {updated}/{len(data['exercises'])} exercises. Backup: {BACKUP}")


if __name__ == "__main__":
    main()
