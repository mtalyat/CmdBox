from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LogDisplaySettings:
    show_timestamp: bool = True
    show_level: bool = True
    show_command_name: bool = True
    show_source: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "show_timestamp": self.show_timestamp,
            "show_level": self.show_level,
            "show_command_name": self.show_command_name,
            "show_source": self.show_source,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LogDisplaySettings":
        return LogDisplaySettings(
            show_timestamp=bool(data.get("show_timestamp", True)),
            show_level=bool(data.get("show_level", True)),
            show_command_name=bool(data.get("show_command_name", True)),
            show_source=bool(data.get("show_source", True)),
        )


@dataclass
class AppSettings:
    log_display: LogDisplaySettings

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_display": self.log_display.to_dict(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppSettings":
        raw_log = data.get("log_display", {})
        if not isinstance(raw_log, dict):
            raw_log = {}
        return AppSettings(log_display=LogDisplaySettings.from_dict(raw_log))

    @staticmethod
    def default() -> "AppSettings":
        return AppSettings(log_display=LogDisplaySettings())
