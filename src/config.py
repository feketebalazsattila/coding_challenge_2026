from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "app.json"
CONFIG_PATH_ENV_VAR = "MOVIE_AGENT_CONFIG"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    root_message: str


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path


class OllamaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    base_url: str
    timeout_seconds: float = Field(gt=0)


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    file: Path


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig
    database: DatabaseConfig
    ollama: OllamaConfig
    logging: LoggingConfig

    @model_validator(mode="after")
    def resolve_paths(self) -> Self:
        self.database.path = _resolve_path(self.database.path)
        self.logging.file = _resolve_path(self.logging.file)
        return self


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _load_json_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open(encoding="utf-8") as config_file:
            data = json.load(config_file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Config file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Config file contains invalid JSON: {config_path}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Config file must contain a JSON object: {config_path}")

    return data


def load_settings(config_path: str | Path | None = None) -> Settings:
    configured_path = (
        Path(config_path)
        if config_path is not None
        else Path(os.getenv(CONFIG_PATH_ENV_VAR, DEFAULT_CONFIG_PATH))
    )
    resolved_config_path = _resolve_path(configured_path)

    try:
        settings = Settings.model_validate(_load_json_config(resolved_config_path))
    except ValidationError as exc:
        raise RuntimeError(f"Config file is invalid: {resolved_config_path}") from exc

    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()
