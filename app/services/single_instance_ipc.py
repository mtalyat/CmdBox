from __future__ import annotations

import json
from pathlib import Path

IPC_HOST = "127.0.0.1"
IPC_PORT = 47651


def build_open_project_message(project_path: Path) -> bytes:
    payload = {"action": "open_project", "path": str(project_path)}
    return (json.dumps(payload) + "\n").encode("utf-8")


def parse_open_project_message(payload: bytes) -> Path | None:
    try:
        text = payload.decode("utf-8", errors="replace").strip()
        if not text:
            return None
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        if str(data.get("action") or "") != "open_project":
            return None
        raw_path = str(data.get("path") or "").strip()
        if not raw_path:
            return None
        return Path(raw_path)
    except Exception:
        return None
