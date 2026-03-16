from __future__ import annotations

import json
from pathlib import Path

from app.models.app_settings_models import AppSettings


class AppSettingsStore:
    def __init__(self, settings_path: Path | None = None):
        self._settings_path = settings_path or (Path.home() / ".cmdbox_settings.json")
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self._settings_path.exists():
            return AppSettings.default()

        try:
            raw = self._settings_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return AppSettings.default()
            return AppSettings.from_dict(data)
        except Exception:
            return AppSettings.default()

    def save(self, settings: AppSettings) -> None:
        payload = settings.to_dict()
        tmp_path = self._settings_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp_path.replace(self._settings_path)
