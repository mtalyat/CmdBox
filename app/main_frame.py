from __future__ import annotations

import json
import re
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import wx

from app.models.app_settings_models import AppSettings
from app.models.config_models import AppConfig, CommandButtonConfig, FilterConfig
from app.services.command_runner import CommandRunner
from app.services.log_service import LogEntry, LogService
from app.services.overlay_queue import OverlayQueue
from app.services.runtime_paths import app_root, default_project_file, icon_file, icons_dir, user_data_dir
from app.storage.app_settings_store import AppSettingsStore
from app.storage.config_store import ConfigStore
from app.widgets.button_grid import ButtonGridPanel
from app.widgets.command_arguments_dialog import CommandArgumentsDialog
from app.widgets.log_panel import LogPanel
from app.widgets.run_overlay import RunOverlay
from app.widgets.settings_dialog import SettingsDialog

EMPTY_SOURCE = "--------"

LEVEL_CMD = "CMD"
LEVEL_ERROR = "ERR"
LEVEL_INFO = "INF"
LEVEL_WARN = "WRN"


PROJECT_EXT = ".cmdbox"
PROJECT_WILDCARD = "CmdBox Project (*.cmdbox)|*.cmdbox|JSON files (*.json)|*.json|All files (*.*)|*.*"
RECENT_PROJECT_FILE = ".cmdbox_recent"
RECENT_PROJECT_LIMIT = 10
ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".ico", ".gif")
COMMAND_ARG_RE = re.compile(r"\{([^{}]+)\}")


class MainFrame(wx.Frame):
    def __init__(self, project_path: Optional[Path] = None):
        super().__init__(None, title="CmdBox", size=(1100, 700))
        self._apply_app_icon()

        startup_project = self._resolve_startup_project_path(project_path)
        store_path = startup_project or default_project_file()
        self._store = ConfigStore(store_path)
        self._config = self._store.load_from(startup_project) if startup_project else AppConfig.from_dict({})
        self._project_path: Optional[Path] = startup_project
        self._recent_projects: list[Path] = self._read_recent_projects()
        if startup_project:
            self._recent_projects = self._merge_recent_project(startup_project, self._recent_projects)
        self._dirty = False
        self._app_settings_store = AppSettingsStore()
        self._app_settings: AppSettings = self._app_settings_store.load()

        self._runner = CommandRunner()
        self._log_service = LogService(max_entries=10000)
        self._hotkey_bindings: dict[int, str] = {}
        self._next_hotkey_id = 5000
        self._recent_menu_items: dict[int, Path] = {}
        self._active_runs: dict[str, CommandButtonConfig] = {}
        self._run_overlay = RunOverlay(None)
        self._overlay_instance_id = uuid4().hex
        self._overlay_queue = OverlayQueue()
        self._overlay_queue_timer = wx.Timer(self)

        self._create_menu()
        self._build_ui()
        self._bind_events()
        self._update_title()
        self._refresh_hotkeys()
        self._overlay_queue_timer.Start(350)

        self.Centre()

    def _resolve_command_bitmap(self, button_cfg: CommandButtonConfig, size: tuple[int, int] = (24, 24)) -> wx.Bitmap | None:
        icon_value = button_cfg.icon_value.strip()
        if not icon_value:
            return None

        p = Path(icon_value)
        if p.exists() and p.is_file():
            img = wx.Image(str(p))
            if img.IsOk():
                return wx.Bitmap(img.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH))

        icon_root = icons_dir()
        if not p.is_absolute() and icon_root.exists() and icon_root.is_dir():
            if p.suffix:
                candidate = icon_root / p.name
                if candidate.exists() and candidate.is_file():
                    img = wx.Image(str(candidate))
                    if img.IsOk():
                        return wx.Bitmap(img.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH))
            else:
                for ext in ICON_EXTENSIONS:
                    candidate = icon_root / f"{icon_value}{ext}"
                    if candidate.exists() and candidate.is_file():
                        img = wx.Image(str(candidate))
                        if img.IsOk():
                            return wx.Bitmap(img.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH))

        art_id = getattr(wx, icon_value, None)
        if art_id:
            bmp = wx.ArtProvider.GetBitmap(art_id, wx.ART_OTHER, size)
            if bmp and bmp.IsOk():
                return bmp

        return None

    def _show_run_overlay(self, button_cfg: CommandButtonConfig) -> None:
        queue_index, _queue_count = self._overlay_queue.update(self._overlay_instance_id, active=bool(self._active_runs))
        if queue_index is None:
            self._run_overlay.hide_overlay()
            return

        bitmap = self._resolve_command_bitmap(button_cfg, size=(24, 24))
        label = button_cfg.label.strip() or "Command"
        self._run_overlay.show_running(
            bitmap=bitmap,
            label=label,
            running_count=len(self._active_runs),
            slot_index=queue_index,
        )

    def _sync_overlay_queue(self) -> None:
        if not self._active_runs:
            self._overlay_queue.update(self._overlay_instance_id, active=False)
            self._run_overlay.hide_overlay()
            return

        last_run_id = next(reversed(self._active_runs))
        self._show_run_overlay(self._active_runs[last_run_id])

    def _on_overlay_queue_tick(self, _evt: wx.TimerEvent) -> None:
        try:
            self._sync_overlay_queue()
        except Exception:
            # Queue sync failures should never crash the UI.
            pass

    def _on_command_started(self, run_id: str, button_cfg: CommandButtonConfig) -> None:
        self._active_runs[run_id] = button_cfg
        self._show_run_overlay(button_cfg)

    def _on_command_finished(self, run_id: str) -> None:
        self._active_runs.pop(run_id, None)
        self._sync_overlay_queue()

    def _resolve_app_icon_path(self) -> Optional[Path]:
        candidates = [icon_file()]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _apply_app_icon(self) -> None:
        icon_path = self._resolve_app_icon_path()
        if not icon_path:
            return

        try:
            image = wx.Image(str(icon_path))
            if not image.IsOk():
                return

            icons = wx.IconBundle()
            for size in (16, 24, 32, 48, 64, 128, 256):
                scaled = image.Scale(size, size, wx.IMAGE_QUALITY_HIGH)
                bmp = wx.Bitmap(scaled)
                icon = wx.Icon()
                icon.CopyFromBitmap(bmp)
                if icon.IsOk():
                    icons.AddIcon(icon)

            if icons.GetIconCount() > 0:
                self.SetIcons(icons)
        except Exception:
            # Missing/invalid icon must never block app startup.
            return

    def _recent_pointer_path(self) -> Path:
        return user_data_dir() / RECENT_PROJECT_FILE

    def _merge_recent_project(self, project_path: Path, items: list[Path]) -> list[Path]:
        resolved = project_path.resolve()
        out: list[Path] = [resolved]
        for item in items:
            try:
                candidate = item.resolve()
            except Exception:
                continue
            if candidate != resolved and candidate.exists() and candidate.is_file():
                out.append(candidate)
            if len(out) >= RECENT_PROJECT_LIMIT:
                break
        return out

    def _read_recent_projects(self) -> list[Path]:
        pointer = self._recent_pointer_path()
        if not pointer.exists():
            return []

        try:
            raw = pointer.read_text(encoding="utf-8").strip()
            if not raw:
                return []

            values: list[str]
            if raw.startswith("["):
                parsed = json.loads(raw)
                values = [str(x) for x in parsed] if isinstance(parsed, list) else []
            else:
                # Backward compatibility with old single-path format.
                values = [raw]

            out: list[Path] = []
            for value in values:
                candidate = Path(value)
                if not candidate.is_absolute():
                    candidate = (app_root() / candidate).resolve()
                if candidate.exists() and candidate.is_file() and candidate not in out:
                    out.append(candidate)
                if len(out) >= RECENT_PROJECT_LIMIT:
                    break

            return out
        except Exception:
            return []

    def _read_recent_project_path(self) -> Optional[Path]:
        recents = self._read_recent_projects()
        return recents[0] if recents else None

    def _write_recent_projects(self) -> None:
        try:
            payload = [str(p.resolve()) for p in self._recent_projects[:RECENT_PROJECT_LIMIT]]
            self._recent_pointer_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            # Failure to write MRU pointer should never block the app.
            pass

    def _touch_recent_project(self, project_path: Path) -> None:
        self._recent_projects = self._merge_recent_project(project_path, self._recent_projects)
        self._write_recent_projects()
        self._refresh_recent_menu()

    def _resolve_startup_project_path(self, project_path: Optional[Path]) -> Optional[Path]:
        if project_path:
            return project_path.resolve()
        return self._read_recent_project_path()

    def _create_menu(self) -> None:
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        edit_menu = wx.Menu()
        add_menu = wx.Menu()
        self._open_recent_menu = wx.Menu()

        self._new_item = file_menu.Append(wx.ID_NEW, "&New\tCtrl+N")
        self._open_item = file_menu.Append(wx.ID_OPEN, "&Open...\tCtrl+O")
        file_menu.AppendSubMenu(self._open_recent_menu, "Open &Recent")
        file_menu.AppendSeparator()
        self._save_item = file_menu.Append(wx.ID_SAVE, "&Save\tCtrl+S")
        self._save_as_item = file_menu.Append(wx.ID_SAVEAS, "Save &As...")
        self._settings_item = file_menu.Append(wx.ID_PREFERENCES, "&Settings...")
        file_menu.AppendSeparator()
        self._exit_item = file_menu.Append(wx.ID_EXIT, "E&xit")

        self._add_button_item = add_menu.Append(wx.ID_ANY, "Add &Button")
        self._add_filter_item = add_menu.Append(wx.ID_ANY, "Add &Filter")
        edit_menu.AppendSubMenu(add_menu, "&Add")

        menu_bar.Append(file_menu, "&File")
        menu_bar.Append(edit_menu, "&Edit")
        self.SetMenuBar(menu_bar)
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        if not hasattr(self, "_open_recent_menu"):
            return

        for item in list(self._open_recent_menu.GetMenuItems()):
            self._open_recent_menu.Delete(item.GetId())
        self._recent_menu_items.clear()

        if not self._recent_projects:
            empty_item = self._open_recent_menu.Append(wx.ID_ANY, "(No Recent Projects)")
            empty_item.Enable(False)
            return

        for i, project_path in enumerate(self._recent_projects[:RECENT_PROJECT_LIMIT], start=1):
            item_id = wx.Window.NewControlId()
            label = f"{i}. {project_path}"
            item = self._open_recent_menu.Append(item_id, label)
            self.Bind(wx.EVT_MENU, self._on_open_recent_project, item)
            self._recent_menu_items[item_id] = project_path

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        self.splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)

        self.button_grid = ButtonGridPanel(
            self.splitter,
            buttons=self._config.buttons,
            on_buttons_changed=self._on_buttons_changed,
            on_run_button=self._on_run_button,
        )
        self.log_panel = LogPanel(
            self.splitter,
            filters=self._config.filters,
            on_filters_changed=self._on_filters_changed,
            on_clear=self._on_clear_log,
            log_display_settings=self._app_settings.log_display,
        )

        self.splitter.SplitHorizontally(self.button_grid, self.log_panel)
        self.splitter.SetMinimumPaneSize(120)
        self.splitter.SetSashPosition(self._config.sash_position)

        root.Add(self.splitter, 1, wx.EXPAND)
        panel.SetSizer(root)

    def _bind_events(self) -> None:
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_MENU, self._on_new_project, self._new_item)
        self.Bind(wx.EVT_MENU, self._on_open_project, self._open_item)
        self.Bind(wx.EVT_MENU, self._on_save_project, self._save_item)
        self.Bind(wx.EVT_MENU, self._on_save_as_project, self._save_as_item)
        self.Bind(wx.EVT_MENU, self._on_open_settings, self._settings_item)
        self.Bind(wx.EVT_MENU, self._on_exit, self._exit_item)
        self.Bind(wx.EVT_MENU, self._on_add_button_menu, self._add_button_item)
        self.Bind(wx.EVT_MENU, self._on_add_filter_menu, self._add_filter_item)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self._on_sash_changed, self.splitter)
        self.Bind(wx.EVT_HOTKEY, self._on_global_hotkey)
        self.Bind(wx.EVT_TIMER, self._on_overlay_queue_tick, self._overlay_queue_timer)

    def _parse_shortcut(self, shortcut: str) -> tuple[int, int] | None:
        raw = shortcut.strip().upper()
        if not raw:
            return None

        parts = [p.strip() for p in raw.split("+") if p.strip()]
        if not parts:
            return None

        modifiers = 0
        key_token = ""
        for part in parts:
            if part in {"CTRL", "CONTROL"}:
                modifiers |= wx.MOD_CONTROL
            elif part == "ALT":
                modifiers |= wx.MOD_ALT
            elif part == "SHIFT":
                modifiers |= wx.MOD_SHIFT
            elif part in {"WIN", "CMD", "SUPER"}:
                modifiers |= wx.MOD_WIN
            elif key_token:
                return None
            else:
                key_token = part

        if not key_token:
            return None

        special_keys = {
            "SPACE": wx.WXK_SPACE,
            "TAB": wx.WXK_TAB,
            "ENTER": wx.WXK_RETURN,
            "RETURN": wx.WXK_RETURN,
            "ESC": wx.WXK_ESCAPE,
            "ESCAPE": wx.WXK_ESCAPE,
            "BACKSPACE": wx.WXK_BACK,
            "DELETE": wx.WXK_DELETE,
            "INSERT": wx.WXK_INSERT,
            "HOME": wx.WXK_HOME,
            "END": wx.WXK_END,
            "PAGEUP": wx.WXK_PAGEUP,
            "PAGEDOWN": wx.WXK_PAGEDOWN,
            "UP": wx.WXK_UP,
            "DOWN": wx.WXK_DOWN,
            "LEFT": wx.WXK_LEFT,
            "RIGHT": wx.WXK_RIGHT,
        }
        if key_token in special_keys:
            return modifiers, special_keys[key_token]

        if key_token.startswith("F") and key_token[1:].isdigit():
            fn = int(key_token[1:])
            if 1 <= fn <= 24:
                return modifiers, wx.WXK_F1 + (fn - 1)

        if len(key_token) == 1 and key_token.isalnum():
            return modifiers, ord(key_token)

        return None

    def _find_button_by_id(self, button_id: str) -> CommandButtonConfig | None:
        for btn in self.button_grid.get_buttons():
            if btn.id == button_id:
                return btn
        return None

    def _refresh_hotkeys(self) -> None:
        for hotkey_id in list(self._hotkey_bindings.keys()):
            self.UnregisterHotKey(hotkey_id)
        self._hotkey_bindings.clear()

        used: set[tuple[int, int]] = set()
        for btn in self.button_grid.get_buttons():
            if not btn.shortcut.strip():
                continue

            parsed = self._parse_shortcut(btn.shortcut)
            if not parsed:
                self._append_log(LEVEL_ERROR, "HOTKEY", EMPTY_SOURCE, f"Invalid shortcut '{btn.shortcut}' for '{btn.label}'")
                continue

            if parsed in used:
                self._append_log(LEVEL_ERROR, "HOTKEY", EMPTY_SOURCE, f"Duplicate shortcut '{btn.shortcut}' for '{btn.label}'")
                continue
            used.add(parsed)

            hotkey_id = self._next_hotkey_id
            self._next_hotkey_id += 1
            ok = self.RegisterHotKey(hotkey_id, parsed[0], parsed[1])
            if ok:
                self._hotkey_bindings[hotkey_id] = btn.id
            else:
                self._append_log(LEVEL_ERROR, "HOTKEY", EMPTY_SOURCE, f"Could not register shortcut '{btn.shortcut}' for '{btn.label}'")

    def _on_global_hotkey(self, evt: wx.KeyEvent) -> None:
        button_id = self._hotkey_bindings.get(evt.GetId())
        if not button_id:
            return
        btn = self._find_button_by_id(button_id)
        if btn:
            self._on_run_button(btn)

    def _project_label(self) -> str:
        if self._project_path:
            return self._project_path.name
        return f"Untitled{PROJECT_EXT}"

    def _update_title(self) -> None:
        dirty = "*" if self._dirty else ""
        self.SetTitle(f"CmdBox - {self._project_label()}{dirty}")

    def _mark_dirty(self, dirty: bool = True) -> None:
        self._dirty = dirty
        self._update_title()

    def _snapshot_config_from_ui(self) -> AppConfig:
        self._config.buttons = self.button_grid.get_buttons()
        self._config.filters = self.log_panel.get_filters()
        self._config.sash_position = self.splitter.GetSashPosition()
        return self._config

    def _apply_config_to_ui(self) -> None:
        self.button_grid.set_buttons(self._config.buttons)
        self.log_panel.set_filters(self._config.filters)
        if self.splitter.IsSplit():
            self.splitter.SetSashPosition(self._config.sash_position)

    def _ensure_project_extension(self, path_value: Path) -> Path:
        if path_value.suffix.lower() == PROJECT_EXT:
            return path_value
        if path_value.suffix:
            return path_value
        return path_value.with_suffix(PROJECT_EXT)

    def _can_discard_changes(self) -> bool:
        if not self._dirty:
            return True

        res = wx.MessageBox(
            "You have unsaved project changes. Save before continuing?",
            "Unsaved Changes",
            wx.YES_NO | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_QUESTION,
        )
        if res == wx.CANCEL:
            return False
        if res == wx.YES:
            return self._save_current_project()
        return True

    def _new_default_config(self) -> AppConfig:
        default_path = default_project_file()
        if default_path.exists() and default_path.is_file():
            try:
                import json as _json
                data = _json.loads(default_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return AppConfig.from_dict(data)
            except Exception:
                pass
        return AppConfig.from_dict({})

    def _set_project(self, path_value: Optional[Path], config: AppConfig) -> None:
        self._project_path = path_value
        self._config = config
        self._apply_config_to_ui()
        self._log_service.clear()
        self.log_panel.clear_entries()
        if path_value:
            self._touch_recent_project(path_value)
        self._refresh_hotkeys()
        self._mark_dirty(False)

    def _load_project_from_path(self, path_value: Path) -> bool:
        try:
            loaded = self._store.load_from(path_value)
            self._set_project(path_value, loaded)
            return True
        except Exception as ex:
            wx.MessageBox(f"Failed to load project:\n{ex}", "Load Error", wx.OK | wx.ICON_ERROR)
            return False

    def _save_to_path(self, path_value: Path) -> bool:
        try:
            target = path_value.resolve()
            self._store.save_to(target, self._snapshot_config_from_ui())
            self._project_path = target
            self._touch_recent_project(target)
            self._mark_dirty(False)
            return True
        except Exception as ex:
            wx.MessageBox(f"Failed to save project:\n{ex}", "Save Error", wx.OK | wx.ICON_ERROR)
            return False

    def _save_current_project(self) -> bool:
        if self._project_path:
            return self._save_to_path(self._project_path)
        return self._save_as_project_with_dialog()

    def _save_as_project_with_dialog(self) -> bool:
        default_name = self._project_label()
        with wx.FileDialog(
            self,
            "Save CmdBox Project",
            wildcard=PROJECT_WILDCARD,
            defaultFile=default_name,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            out_path = self._ensure_project_extension(Path(dlg.GetPath()))
            return self._save_to_path(out_path)

    def _save_config(self) -> None:
        self._snapshot_config_from_ui()
        if not self._project_path:
            return

        try:
            self._store.save_to(self._project_path, self._config)
        except Exception as ex:
            self._append_log(LEVEL_ERROR, "CONFIG", EMPTY_SOURCE, f"autosave failed: {ex}")
            wx.MessageBox(f"Failed to auto-save project:\n{ex}", "Save Error", wx.OK | wx.ICON_ERROR)

    def _append_log(self, level: str, source: str, run_id: str, message: str) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            run_id=run_id,
            source=source,
            level=level,
            message=message,
        )
        self._log_service.add(entry)
        self.log_panel.append_entry(entry)

    def _command_working_dir(self) -> Path:
        if self._project_path and self._project_path.exists():
            return self._project_path.parent
        return app_root()

    def _command_placeholders(self, command: str) -> list[str]:
        seen: set[str] = set()
        placeholders: list[str] = []
        for match in COMMAND_ARG_RE.finditer(command):
            name = match.group(1).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            placeholders.append(name)
        return placeholders

    def _resolve_command_arguments(self, command: str) -> str | None:
        placeholders = self._command_placeholders(command)
        if not placeholders:
            return command

        minimized = self.IsIconized()
        dlg_parent: wx.Window | None = None if minimized else self
        dlg = CommandArgumentsDialog(dlg_parent, placeholders)
        if minimized:
            # Keep the main frame minimized, but force the prompt visible.
            dlg.SetWindowStyleFlag(dlg.GetWindowStyleFlag() | wx.STAY_ON_TOP)
            dlg.CentreOnScreen()
            try:
                hwnd = int(dlg.GetHandle())
                if hwnd:
                    user32 = ctypes.windll.user32
                    SW_SHOW = 5
                    user32.ShowWindow(hwnd, SW_SHOW)
                    user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            dlg.Raise()
        else:
            dlg.CentreOnParent()
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return None
            values = dlg.get_value() or {}
        finally:
            dlg.Destroy()

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1).strip()
            return values.get(name, "")

        return COMMAND_ARG_RE.sub(_replace, command)

    def _on_run_button(self, button_cfg: CommandButtonConfig) -> None:
        source = button_cfg.label
        command = self._resolve_command_arguments(button_cfg.command)
        if command is None:
            return
        working_dir = self._command_working_dir()
        self._append_log("CMD", source, EMPTY_SOURCE, command)
        # self._append_log(LEVEL_INFO, source, EMPTY_SOURCE, f"cwd: {working_dir}")

        def on_line(run_id: str, stream_name: str, line: str) -> None:
            wx.CallAfter(self._append_log, stream_name, source, run_id, line)

        def on_done(run_id: str, return_code: int) -> None:
            level = LEVEL_INFO if return_code == 0 else LEVEL_ERROR
            wx.CallAfter(
                self._append_log,
                level,
                source,
                run_id,
                f"Process exited with code {return_code}.",
            )
            wx.CallAfter(self._on_command_finished, run_id)

        def on_error(run_id: str, message: str) -> None:
            wx.CallAfter(self._append_log, LEVEL_ERROR, source, run_id, f"launch failed: {message}")
            wx.CallAfter(self._on_command_finished, run_id)

        run_id = self._runner.run(
            source_label=source,
            command=command,
            working_dir=working_dir,
            on_line=on_line,
            on_done=on_done,
            on_error=on_error,
        )
        self._on_command_started(run_id, button_cfg)

    def _on_buttons_changed(self, buttons: list[CommandButtonConfig]) -> None:
        self._config.buttons = buttons
        try:
            self._save_config()
            self._refresh_hotkeys()
        except Exception as ex:
            self._append_log(LEVEL_ERROR, "BUTTONS", EMPTY_SOURCE, f"button update failed: {ex}")
            wx.MessageBox(f"Failed to apply button changes:\n{ex}", "Button Update Error", wx.OK | wx.ICON_ERROR)
        finally:
            self._mark_dirty(True)

    def _on_filters_changed(self, filters: list[FilterConfig]) -> None:
        self._config.filters = filters
        try:
            self._save_config()
        except Exception as ex:
            self._append_log(LEVEL_ERROR, "FILTERS", EMPTY_SOURCE, f"filter update failed: {ex}")
            wx.MessageBox(f"Failed to apply filter changes:\n{ex}", "Filter Update Error", wx.OK | wx.ICON_ERROR)
        finally:
            self._mark_dirty(True)

    def _on_clear_log(self) -> None:
        self._log_service.clear()
        self.log_panel.clear_entries()

    def _on_sash_changed(self, _evt: wx.SplitterEvent) -> None:
        try:
            self._save_config()
        except Exception as ex:
            self._append_log(LEVEL_ERROR, "CONFIG", EMPTY_SOURCE, f"sash update failed: {ex}")
        self._mark_dirty(True)

    def _on_new_project(self, _evt: wx.CommandEvent) -> None:
        if not self._can_discard_changes():
            return
        self._set_project(None, self._new_default_config())

    def _on_open_project(self, _evt: wx.CommandEvent) -> None:
        if not self._can_discard_changes():
            return
        with wx.FileDialog(
            self,
            "Open CmdBox Project",
            wildcard=PROJECT_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            self._load_project_from_path(Path(dlg.GetPath()))

    def _on_open_recent_project(self, evt: wx.CommandEvent) -> None:
        project_path = self._recent_menu_items.get(evt.GetId())
        if not project_path:
            return

        if not project_path.exists():
            self._recent_projects = [p for p in self._recent_projects if p != project_path]
            self._write_recent_projects()
            self._refresh_recent_menu()
            wx.MessageBox("Recent project file was not found.", "Open Recent", wx.OK | wx.ICON_WARNING)
            return

        if not self._can_discard_changes():
            return

        self._load_project_from_path(project_path)

    def _on_save_project(self, _evt: wx.CommandEvent) -> None:
        self._save_current_project()

    def _on_save_as_project(self, _evt: wx.CommandEvent) -> None:
        self._save_as_project_with_dialog()

    def _on_open_settings(self, _evt: wx.CommandEvent) -> None:
        dlg = SettingsDialog(self, self._app_settings)
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.get_value()
            if updated:
                self._app_settings = updated
                self.log_panel.set_log_display_settings(updated.log_display)
                try:
                    self._app_settings_store.save(updated)
                except Exception as ex:
                    wx.MessageBox(f"Failed to save settings:\n{ex}", "Settings Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def _on_exit(self, _evt: wx.CommandEvent) -> None:
        self.Close()

    def _on_add_button_menu(self, _evt: wx.CommandEvent) -> None:
        self.button_grid.add_button()

    def _on_add_filter_menu(self, _evt: wx.CommandEvent) -> None:
        self.log_panel.add_filter()

    def _on_close(self, evt: wx.CloseEvent) -> None:
        if not self._can_discard_changes():
            evt.Veto()
            return
        for hotkey_id in list(self._hotkey_bindings.keys()):
            self.UnregisterHotKey(hotkey_id)
        self._hotkey_bindings.clear()
        try:
            self._overlay_queue_timer.Stop()
        except Exception:
            pass
        try:
            self._overlay_queue.unregister(self._overlay_instance_id)
        except Exception:
            pass
        self._run_overlay.hide_overlay()
        self._run_overlay.Destroy()
        self._runner.shutdown()
        self.Destroy()


def run_app(project_path: Optional[Path] = None) -> None:
    app = wx.App(False)
    frame = MainFrame(project_path=project_path)
    frame.Show()
    app.MainLoop()
