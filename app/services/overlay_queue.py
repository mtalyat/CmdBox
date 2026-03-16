from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path


class OverlayQueue:
    def __init__(self, state_path: Path | None = None, stale_seconds: float = 5.0) -> None:
        self._state_path = state_path or (Path.home() / ".cmdbox_overlay_queue.json")
        self._lock_path = self._state_path.with_suffix(".lock")
        self._stale_seconds = stale_seconds

        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def _lock(self):
        if os.name != "nt":
            yield
            return

        import msvcrt

        with self._lock_path.open("a+b") as fh:
            fh.seek(0, os.SEEK_END)
            if fh.tell() == 0:
                fh.write(b"0")
                fh.flush()

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)

    def _load_state(self) -> dict:
        if not self._state_path.exists():
            return {"instances": {}}

        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("instances"), dict):
                return data
        except Exception:
            pass
        return {"instances": {}}

    def _save_state(self, state: dict) -> None:
        tmp = self._state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self._state_path)

    def _prune_stale(self, state: dict, now: float) -> None:
        instances = state.get("instances", {})
        stale_ids: list[str] = []
        for instance_id, entry in instances.items():
            last_seen = float(entry.get("last_seen", 0.0))
            if now - last_seen > self._stale_seconds:
                stale_ids.append(instance_id)

        for instance_id in stale_ids:
            instances.pop(instance_id, None)

    def update(self, instance_id: str, active: bool) -> tuple[int | None, int]:
        now = time.time()

        with self._lock():
            state = self._load_state()
            self._prune_stale(state, now)
            instances: dict[str, dict] = state.setdefault("instances", {})

            if active:
                entry = instances.get(instance_id, {})
                if not entry.get("active"):
                    entry["active_since"] = now
                entry["active"] = True
                entry["last_seen"] = now
                instances[instance_id] = entry
            else:
                instances.pop(instance_id, None)

            active_items: list[tuple[str, float]] = []
            for iid, entry in instances.items():
                if entry.get("active"):
                    active_since = float(entry.get("active_since", entry.get("last_seen", now)))
                    active_items.append((iid, active_since))

            active_items.sort(key=lambda item: (item[1], item[0]))
            ordered_ids = [iid for iid, _ in active_items]

            self._save_state(state)

        if instance_id in ordered_ids:
            return ordered_ids.index(instance_id), len(ordered_ids)
        return None, len(ordered_ids)

    def unregister(self, instance_id: str) -> None:
        with self._lock():
            state = self._load_state()
            instances: dict[str, dict] = state.setdefault("instances", {})
            instances.pop(instance_id, None)
            self._save_state(state)
