from __future__ import annotations

import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4


LineCallback = Callable[[str, str, str], None]
DoneCallback = Callable[[str, int], None]
ErrorCallback = Callable[[str, str], None]


@dataclass
class CommandRun:
    run_id: str
    source_label: str
    command: str
    started_at: datetime


class CommandRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: set[threading.Thread] = set()
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def run(
        self,
        source_label: str,
        command: str,
        working_dir: Path | None,
        on_line: LineCallback,
        on_done: DoneCallback,
        on_error: ErrorCallback,
    ) -> str:
        run_id = uuid4().hex[:8]

        def _target() -> None:
            proc: subprocess.Popen[str] | None = None
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=str(working_dir) if working_dir else None,
                    env=env,
                )
                with self._lock:
                    self._processes[run_id] = proc
            except Exception as ex:
                on_error(run_id, str(ex))
                return
            try:
                if proc.stdout is not None:
                    for line in iter(proc.stdout.readline, ""):
                        if not line:
                            break
                        on_line(run_id, "   ", line.rstrip("\r\n"))
                    proc.stdout.close()

                proc.wait()
                on_done(run_id, proc.returncode)
            finally:
                with self._lock:
                    self._processes.pop(run_id, None)
                    current = threading.current_thread()
                    if current in self._workers:
                        self._workers.remove(current)

        worker = threading.Thread(target=_target)
        with self._lock:
            self._workers.add(worker)
        worker.start()
        return run_id

    def shutdown(self, join_timeout_seconds: float = 2.0) -> None:
        with self._lock:
            procs = list(self._processes.values())
            workers = list(self._workers)

        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

        for proc in procs:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=join_timeout_seconds)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        for worker in workers:
            if worker.is_alive():
                worker.join(timeout=join_timeout_seconds)

        with self._lock:
            self._workers = {w for w in self._workers if w.is_alive()}
