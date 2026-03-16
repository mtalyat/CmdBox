from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from app.models.config_models import FilterConfig


@dataclass
class LogEntry:
    timestamp: datetime
    run_id: str
    source: str
    level: str
    message: str

    def render(self) -> str:
        t = self.timestamp.strftime("%H:%M:%S")
        return f"[{t}] [{self.level}] [{self.source}] [{self.run_id}] {self.message}"


class LogService:
    def __init__(self, max_entries: int = 10000):
        self._entries: list[LogEntry] = []
        self._max_entries = max_entries

    def add(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            overflow = len(self._entries) - self._max_entries
            self._entries = self._entries[overflow:]

    def clear(self) -> None:
        self._entries.clear()

    def all_entries(self) -> list[LogEntry]:
        return list(self._entries)

    def filtered(self, filters: list[FilterConfig]) -> list[LogEntry]:
        active = [f for f in filters if f.enabled and f.pattern.strip()]
        if not active:
            return self.all_entries()

        out: list[LogEntry] = []
        for entry in self._entries:
            haystack = f"{entry.level} {entry.source} {entry.message}"
            if any(self._matches(flt, haystack) for flt in active):
                out.append(entry)
        return out

    @staticmethod
    def _matches(flt: FilterConfig, haystack: str) -> bool:
        pattern = flt.pattern
        if flt.use_regex:
            try:
                flags = 0 if flt.case_sensitive else re.IGNORECASE
                return bool(re.search(pattern, haystack, flags))
            except re.error:
                return False
        else:
            if flt.case_sensitive:
                return pattern in haystack
            return pattern.lower() in haystack.lower()
