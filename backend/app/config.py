"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("devteam.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://devteam:devteam@localhost:5432/devteam"
    secret_key: str = ""
    access_token_minutes: int = 60 * 12
    cors_origins: str = "http://localhost:5173"

    # LLM (Groq is the default provider)
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 90

    # Workspaces: one directory per project, never executed on the host.
    workspace_root: Path = Path("./workspaces")
    # When the backend itself runs in Docker, the host path that backs workspace_root.
    workspace_host_path: str = ""

    # Sandbox
    sandbox_image: str = "devteam-sandbox:latest"
    sandbox_timeout_seconds: int = 60
    sandbox_memory: str = "512m"
    sandbox_cpus: str = "1"
    sandbox_pids_limit: int = 128
    sandbox_network_enabled: bool = False  # keep False; see README security notes

    max_repair_attempts: int = Field(default=2, ge=0, le=2)
    max_tasks: int = 12
    max_files_per_run: int = 40
    max_file_bytes: int = 200_000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.secret_key:
        s.secret_key = secrets.token_urlsafe(48)
        log.warning("SECRET_KEY not set: using an ephemeral key; logins reset on restart.")
    return s
