import os
from pathlib import Path
import socket
import sys
import threading
import ctypes

from app.main_frame import run_app
from app.services.single_instance_ipc import IPC_HOST, IPC_PORT, build_open_project_message


def _set_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CmdBox.App")
    except Exception:
        # If this fails, app can still run with default process identity.
        pass


def _install_py313_threading_shutdown_guard() -> None:
    if sys.version_info < (3, 13):
        return

    original_shutdown = getattr(threading, "_shutdown", None)
    if not callable(original_shutdown):
        return

    def _safe_shutdown() -> None:
        try:
            original_shutdown()
        except SystemError as ex:
            if "_thread._ThreadHandle" in str(ex) and "is_done" in str(ex):
                # Python 3.13 + debugger/runtime edge case during interpreter teardown.
                return
            raise

    threading._shutdown = _safe_shutdown


def _disable_py313_threading_shutdown() -> None:
    if sys.version_info < (3, 13):
        return

    try:
        threading._shutdown = lambda: None
    except Exception:
        pass


def _forward_project_open_request(project_path: Path) -> bool:
    try:
        with socket.create_connection((IPC_HOST, IPC_PORT), timeout=0.35) as conn:
            conn.sendall(build_open_project_message(project_path))
            conn.settimeout(0.5)
            return conn.recv(16).startswith(b"OK")
    except OSError:
        return False


if __name__ == "__main__":
    _set_windows_app_user_model_id()
    _install_py313_threading_shutdown_guard()
    exit_code = 0
    try:
        project_arg = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
        if project_arg and _forward_project_open_request(project_arg):
            sys.exit(0)
        run_app(project_path=project_arg)
    except BaseException:
        exit_code = 1
        raise
    finally:
        _disable_py313_threading_shutdown()

    if sys.version_info >= (3, 13) and exit_code == 0:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(0)
