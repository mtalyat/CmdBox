from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex[:8]


@dataclass
class CommandButtonConfig:
    id: str = field(default_factory=_new_id)
    label: str = "New"
    show_name: bool = True
    show_errors: bool = True
    command: str = ""
    icon_value: str = ""
    shortcut: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "CommandButtonConfig":
        return CommandButtonConfig(
            id=str(data.get("id") or _new_id()),
            label=str(data.get("label") or "New"),
            show_name=bool(data.get("show_name", True)),
            show_errors=bool(data.get("show_errors", True)),
            command=str(data.get("command") or ""),
            icon_value=str(data.get("icon_value") or ""),
            shortcut=str(data.get("shortcut") or ""),
        )


@dataclass
class FilterConfig:
    id: str = field(default_factory=_new_id)
    name: str = "Filter"
    pattern: str = ""
    enabled: bool = False
    case_sensitive: bool = False
    use_regex: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FilterConfig":
        return FilterConfig(
            id=str(data.get("id") or _new_id()),
            name=str(data.get("name") or "Filter"),
            pattern=str(data.get("pattern") or ""),
            enabled=bool(data.get("enabled", False)),
            case_sensitive=bool(data.get("case_sensitive", False)),
            use_regex=bool(data.get("use_regex", False)),
        )


@dataclass
class AppConfig:
    buttons: list[CommandButtonConfig] = field(default_factory=list)
    filters: list[FilterConfig] = field(default_factory=list)
    sash_position: int = 420

    def to_dict(self) -> dict[str, Any]:
        return {
            "buttons": [b.to_dict() for b in self.buttons],
            "filters": [f.to_dict() for f in self.filters],
            "sash_position": self.sash_position,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AppConfig":
        buttons = [
            CommandButtonConfig.from_dict(item)
            for item in data.get("buttons", [])
            if isinstance(item, dict)
        ]
        filters = [
            FilterConfig.from_dict(item)
            for item in data.get("filters", [])
            if isinstance(item, dict)
        ]

        if not buttons:
            buttons = []

        if not filters:
            filters = []

        sash_position = int(data.get("sash_position") or 420)
        return AppConfig(buttons=buttons, filters=filters, sash_position=sash_position)
