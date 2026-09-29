from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex[:8]


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class CommandButtonConfig:
    id: str = field(default_factory=_new_id)
    label: str = "New"
    enabled: bool = True
    show_name: bool = True
    show_errors: bool = False
    success_value: int = 0
    show_gui_on_run: bool = False
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
            enabled=bool(data.get("enabled", True)),
            show_name=bool(data.get("show_name", True)),
            show_errors=bool(data.get("show_errors", False)),
            success_value=_as_int(data.get("success_value"), 0),
            show_gui_on_run=bool(data.get("show_gui_on_run", False)),
            command=str(data.get("command") or ""),
            icon_value=str(data.get("icon_value") or ""),
            shortcut=str(data.get("shortcut") or ""),
        )


@dataclass
class FilterConfig:
    id: str = field(default_factory=_new_id)
    name: str = "Filter"
    pattern: str = ""
    enabled: bool = True
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
class ProjectConfig:
    id: str = field(default_factory=_new_id)
    name: str = "Default"
    variables: dict[str, str] = field(default_factory=dict)
    allowed_button_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variables": dict(self.variables),
            "allowed_button_ids": list(self.allowed_button_ids),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProjectConfig":
        raw_vars = data.get("variables", {})
        raw_allowed = data.get("allowed_button_ids", [])
        variables: dict[str, str] = {}
        if isinstance(raw_vars, dict):
            for key, value in raw_vars.items():
                key_text = str(key).strip()
                if not key_text:
                    continue
                variables[key_text] = str(value)

        allowed_button_ids = [str(x) for x in raw_allowed if str(x).strip()] if isinstance(raw_allowed, list) else []
        return ProjectConfig(
            id=str(data.get("id") or _new_id()),
            name=str(data.get("name") or "Default"),
            variables=variables,
            allowed_button_ids=allowed_button_ids,
        )


@dataclass
class AppConfig:
    buttons: list[CommandButtonConfig] = field(default_factory=list)
    filters: list[FilterConfig] = field(default_factory=list)
    projects: list[ProjectConfig] = field(default_factory=list)
    active_project_id: str = ""
    sash_position: int = 420

    def to_dict(self) -> dict[str, Any]:
        return {
            "buttons": [b.to_dict() for b in self.buttons],
            "filters": [f.to_dict() for f in self.filters],
            "projects": [p.to_dict() for p in self.projects],
            "active_project_id": self.active_project_id,
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
        projects = [
            ProjectConfig.from_dict(item)
            for item in data.get("projects", [])
            if isinstance(item, dict)
        ]

        if not buttons:
            buttons = []

        if not filters:
            filters = []

        if not projects:
            projects = [ProjectConfig(name="Default")]

        active_project_id = str(data.get("active_project_id") or "").strip()
        if not active_project_id or active_project_id not in {p.id for p in projects}:
            active_project_id = projects[0].id

        sash_position = int(data.get("sash_position") or 420)
        return AppConfig(
            buttons=buttons,
            filters=filters,
            projects=projects,
            active_project_id=active_project_id,
            sash_position=sash_position,
        )
