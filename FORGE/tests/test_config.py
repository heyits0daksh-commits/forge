"""
Smoke test for backend.core.config — mainly guards against path regressions
when the project is moved/deployed elsewhere.
"""
from pathlib import Path

from backend.core.config import settings


def test_exercises_json_path_exists():
    assert settings.EXERCISES_JSON_PATH.exists(), (
        f"Expected exercises.json at {settings.EXERCISES_JSON_PATH}"
    )


def test_data_dir_is_a_path():
    assert isinstance(settings.DATA_DIR, Path)


def test_defaults_are_sane():
    assert settings.API_PORT > 0
    assert settings.FRONTEND_API_BASE.startswith("http")
