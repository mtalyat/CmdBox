from __future__ import annotations

import json
from pathlib import Path

from app.models.config_models import AppConfig


class ConfigStore:
    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._ensure_parent()

    def _ensure_parent(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

    def get_path(self) -> Path:
        return self._config_path

    def set_path(self, config_path: Path) -> None:
        self._config_path = config_path
        self._ensure_parent()

    def load(self) -> AppConfig:
        return self.load_from(self._config_path)

    def load_from(self, config_path: Path) -> AppConfig:
        self.set_path(config_path)
        if not self._config_path.exists():
            return AppConfig.from_dict({})

        try:
            text = self._config_path.read_text(encoding="utf-8")
            data = json.loads(text)
            if not isinstance(data, dict):
                return AppConfig.from_dict({})
            return AppConfig.from_dict(data)
        except Exception:
            return AppConfig.from_dict({})

    def save(self, config: AppConfig) -> None:
        self.save_to(self._config_path, config)

    def save_to(self, config_path: Path, config: AppConfig) -> None:
        self.set_path(config_path)
        payload = config.to_dict()
        tmp_path = self._config_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self._config_path)
