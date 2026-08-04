"""
Central configuration for FORGE.

Every value that used to be hardcoded across main.py / app.py (data file paths,
host, port, CORS, API base URL) now lives here and can be overridden via a
.env file or real environment variables, without touching code.

Usage:
    from backend.core.config import settings
    settings.EXERCISES_JSON_PATH
"""
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (backend/core/config.py -> FORGE/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App metadata ---
    APP_NAME: str = "FORGE Engine - Knowledge Graph Prescription Engine"
    APP_VERSION: str = "5.0.0"
    DEBUG: bool = False

    # --- Paths ---
    DATA_DIR: Path = DEFAULT_DATA_DIR
    EXERCISES_FILENAME: str = "exercises.json"
    # Where the data-migration scripts (scripts/enrich_exercises.py,
    # generate_batch*_equipment.py) write their pre-migration snapshot before
    # touching exercises.json. Kept out of DATA_DIR itself so a fresh
    # `data/` listing isn't dominated by old snapshots (this is the setting
    # the README's "moved backups into data/backups/" bug fix note refers
    # to - previously the scripts had this path hardcoded to DATA_DIR
    # directly, so every re-run re-cluttered data/ instead).
    BACKUP_DIR: Path = DEFAULT_DATA_DIR / "backups"

    # --- API server ---
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    # Off by default: autoreload is a dev convenience, not something that
    # should be silently on for anyone who runs `python -m backend.main`
    # without an explicit .env. Set API_RELOAD=true in .env for local dev.
    API_RELOAD: bool = False
    # "*" is deliberate here (not a placeholder) - the web UI is meant to be
    # opened directly as a local file (file://), which sends `Origin: null`,
    # so a fixed allowlist would break the documented double-click workflow.
    # This is safe specifically because allow_credentials is False below:
    # per the CORS spec, "*" + credentials is invalid anyway (browsers reject
    # it), and this app has no cookies/auth to leak. If you add auth, swap
    # this for an explicit origin list and turn allow_credentials back on.
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])

    # --- Frontend (frontend/web/index.html) ---
    # The web UI computes its own API base in-browser (query param or same-
    # origin default) rather than reading this, but it's kept as the
    # documented default backend address for anyone scripting against the API.
    FRONTEND_API_BASE: str = "http://127.0.0.1:8000"
    METADATA_CACHE_TTL_SECONDS: int = 30

    @property
    def EXERCISES_JSON_PATH(self) -> Path:
        return self.DATA_DIR / self.EXERCISES_FILENAME


# Single shared instance — import this everywhere instead of re-instantiating Settings().
settings = Settings()
