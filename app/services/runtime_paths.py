from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return Path(bundle_dir).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def icons_dir() -> Path:
    return app_root() / "icons"


def icon_file() -> Path:
    root_icon = app_root() / "Icon.png"
    if root_icon.exists():
        return root_icon
    return app_root() / "assets" / "Icon.png"


def default_project_file() -> Path:
    return app_root() / "default.cmdbox"


def user_data_dir() -> Path:
    path = Path.home() / ".cmdbox"
    path.mkdir(parents=True, exist_ok=True)
    return path
