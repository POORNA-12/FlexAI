"""Centralised, validated application configuration.

Single source of truth for environment settings (ADR-0001 D4).

Rules:
    * No credential has a default value. A missing ``DB_PASSWORD`` aborts startup
      with an actionable message instead of silently connecting to a guessable host.
    * ``backend/.env`` is the only configuration file that is read.
    * Consumers import settings from here; nothing else calls ``os.getenv`` for
      database or server configuration.
"""

from __future__ import annotations

import sys
import urllib.parse
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent / ".env"

_MISSING_SECRET_HELP = """
[startup] Configuration error: required setting '{field}' is missing.

Fix one of the following, then retry:
  1. Create backend/.env from the template:
         copy backend\\.env.example backend\\.env
  2. Set the value in backend/.env (no quotes, no spaces around '='):
         {example}
  3. Ensure the environment variable is exported for this shell.

The application refuses to start without an explicit database password: it must
never fall back to a hardcoded default (see docs/02-architecture/ADR-0001).
"""


class Settings(BaseSettings):
    """Environment-backed settings for the API and database layer."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    db_host: str = Field(default="127.0.0.1")
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_user: str = Field(default="yfx_app")
    db_password: str = Field(min_length=1)
    db_name: str = Field(default="supplier_schedule_manager")
    database_url: str | None = Field(default=None)

    # --- API server ---
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    # --- Dataset ---
    dataset_scale: str = Field(default="full")
    synthetic_data_seed: int = Field(default=20261022)

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS allow-list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def sqlalchemy_url(self) -> str:
        """Build the SQLAlchemy DSN, preferring an explicit DATABASE_URL."""
        if self.database_url:
            return self.database_url
        password = urllib.parse.quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance, or exit with an actionable message."""
    try:
        return Settings()
    except ValidationError as exc:
        missing = ", ".join(str(err["loc"][0]).upper() for err in exc.errors())
        print(
            _MISSING_SECRET_HELP.format(
                field=missing or "DB_PASSWORD",
                example="DB_PASSWORD=<your-database-password>",
            ),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
