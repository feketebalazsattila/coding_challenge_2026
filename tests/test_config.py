from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from config import load_settings


def test_load_settings_reads_json_config_and_resolves_paths() -> None:
    work_dir = Path(".test_tmp") / uuid.uuid4().hex
    work_dir.mkdir(parents=True)
    try:
        config_file = work_dir / "app.json"
        config_file.write_text(
            json.dumps(
                {
                    "app": {
                        "title": "Test API",
                        "root_message": "Hello from tests.",
                    },
                    "database": {
                        "path": "data/test.sqlite",
                    },
                    "ollama": {
                        "model": "test-model",
                        "base_url": "http://ollama.test",
                        "timeout_seconds": 7.5,
                    },
                    "logging": {
                        "level": "DEBUG",
                        "file": "logs/test.log",
                    },
                }
            ),
            encoding="utf-8",
        )

        settings = load_settings(config_file)

        assert settings.app.title == "Test API"
        assert settings.app.root_message == "Hello from tests."
        assert settings.database.path.name == "test.sqlite"
        assert settings.database.path.is_absolute()
        assert settings.ollama.model == "test-model"
        assert settings.ollama.base_url == "http://ollama.test"
        assert settings.ollama.timeout_seconds == 7.5
        assert settings.logging.level == "DEBUG"
        assert settings.logging.file.name == "test.log"
        assert settings.logging.file.is_absolute()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
