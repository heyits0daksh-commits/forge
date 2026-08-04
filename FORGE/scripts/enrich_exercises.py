"""
enrich_exercises.py — one-time (re-runnable) migration that adds the v4.0
optional metadata fields to every exercise in exercises.json.

Purely additive: every existing key on every exercise is preserved byte-for-
byte. Only new keys are added (movement_plane, movement_type, chain_type,
force_type, velocity_type, stability_requirement, balance_requirement,
coordination_requirement, mobility_requirement, technical_complexity,
learning_curve, skill_requirement, fatigue_cost, CNS_fatigue,
recovery_time_hours, athletic_qualities). Safe to re-run any time new
exercises are added to the file — it will just enrich whatever's new.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import settings
from backend.services.exercise_metadata import enrich_exercise

SRC = settings.EXERCISES_JSON_PATH
BACKUP = settings.BACKUP_DIR / "exercises_v3_backup.json"


def main():
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, BACKUP)

    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    for ex in data["exercises"]:
        enrichment = enrich_exercise(ex)
        ex.update(enrichment)

    data["version"] = "4.0.0"
    data["schema_notes"] = (
        "v4.0 adds movement-analysis and athletic-quality-tag fields to every "
        "exercise, derived from each exercise's existing category/pattern/"
        "equipment/difficulty (see exercise_metadata.py). All v3.0 fields are "
        "unchanged."
    )

    with open(SRC, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Enriched {len(data['exercises'])} exercises. Backup written to {BACKUP}.")


if __name__ == "__main__":
    main()
