from __future__ import annotations

from copy import deepcopy
import re
from typing import Callable

import wx

from app.models.app_settings_models import LogDisplaySettings
from app.models.config_models import FilterConfig
from app.services.log_service import LogEntry
from app.widgets.filter_edit_dialog import FilterEditDialog


FiltersChangedHandler = Callable[[list[FilterConfig]], None]
ClearHandler = Callable[[], None]
DEFAULT_LOG_FG = wx.Colour(255, 255, 255)
DEFAULT_LOG_BG = wx.Colour(0, 0, 0)


class LogPanel(wx.Panel):
    def __init__(
        self,
        parent: wx.Window,
        filters: list[FilterConfig],
        on_filters_changed: FiltersChangedHandler,
        on_clear: ClearHandler,
        log_display_settings: LogDisplaySettings | None = None,
    ):
        super().__init__(parent)
        self._filters = deepcopy(filters)
        self._entries: list[LogEntry] = []
        self._on_filters_changed = on_filters_changed
        self._on_clear = on_clear
        self._log_display_settings = log_display_settings or LogDisplaySettings()
        self._ansi_re = re.compile(r"\x1b\[([0-9;]*)m")

        root = wx.BoxSizer(wx.VERTICAL)

        top_row = wx.BoxSizer(wx.HORIZONTAL)
        top_row.Add(wx.StaticText(self, label="Filters:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.filter_row = wx.BoxSizer(wx.HORIZONTAL)
        top_row.Add(self.filter_row, 1, wx.EXPAND)

        clear_btn = wx.Button(self, label="Clear Log")
        clear_btn.Bind(wx.EVT_BUTTON, self._clear_clicked)
        top_row.Add(clear_btn, 0, wx.LEFT, 8)

        root.Add(top_row, 0, wx.ALL | wx.EXPAND, 6)

        self.log_txt = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL,
        )
        self.log_txt.SetBackgroundColour(DEFAULT_LOG_BG)
        self.log_txt.SetForegroundColour(DEFAULT_LOG_FG)
        base_font = self.log_txt.GetFont()
        log_font = wx.Font(
            base_font.GetPointSize(),
            wx.FONTFAMILY_TELETYPE,
            base_font.GetStyle(),
            base_font.GetWeight(),
            faceName="Consolas",
        )
        if log_font.IsOk():
            self.log_txt.SetFont(log_font)
        root.Add(self.log_txt, 1, wx.ALL | wx.EXPAND, 6)

        self.SetSizer(root)
        self._rebuild_filter_row()

    def set_entries(self, entries: list[LogEntry]) -> None:
        self._entries = list(entries)
        self._render()

    def append_entry(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        if self._entry_visible(entry):
            self._append_styled_entry(entry)

    def clear_entries(self) -> None:
        self._entries.clear()
        self.log_txt.Clear()

    def get_filters(self) -> list[FilterConfig]:
        return deepcopy(self._filters)

    def set_filters(self, filters: list[FilterConfig]) -> None:
        self._filters = deepcopy(filters)
        self._rebuild_filter_row()
        self._render()

    def get_log_display_settings(self) -> LogDisplaySettings:
        s = self._log_display_settings
        return LogDisplaySettings(
            show_timestamp=s.show_timestamp,
            show_level=s.show_level,
            show_command_name=s.show_command_name,
            show_source=s.show_source,
        )

    def set_log_display_settings(self, settings: LogDisplaySettings) -> None:
        self._log_display_settings = LogDisplaySettings(
            show_timestamp=settings.show_timestamp,
            show_level=settings.show_level,
            show_command_name=settings.show_command_name,
            show_source=settings.show_source,
        )
        self._render()

    def _entry_text(self, entry: LogEntry) -> str:
        parts: list[str] = []
        settings = self._log_display_settings

        if settings.show_timestamp:
            parts.append(f"[{entry.timestamp.strftime('%H:%M:%S')}]")
        if settings.show_level:
            parts.append(f"[{entry.level}]")
        if settings.show_command_name:
            parts.append(f"[{entry.source}]")
        if settings.show_source:
            parts.append(f"[{entry.run_id}]")

        prefix = " ".join(parts)
        if prefix:
            return f"{prefix} {entry.message}"
        return entry.message

    def _entry_visible(self, entry: LogEntry) -> bool:
        active = [f for f in self._filters if f.enabled and f.pattern.strip()]
        if not active:
            return True

        haystack = f"{entry.level} {entry.source} {self._strip_ansi(entry.message)}"
        return any(self._filter_matches(flt, haystack) for flt in active)

    def _strip_ansi(self, text: str) -> str:
        return self._ansi_re.sub("", text)

    def _filter_matches(self, flt: FilterConfig, haystack: str) -> bool:
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

    def _find_matching_filter(self, entry: LogEntry) -> FilterConfig | None:
        active = [f for f in self._filters if f.enabled and f.pattern.strip()]
        if not active:
            return None

        haystack = f"{entry.level} {entry.source} {self._strip_ansi(entry.message)}"
        for flt in active:
            if self._filter_matches(flt, haystack):
                return flt
        return None

    def _color_for_filter(self, flt: FilterConfig | None) -> wx.Colour | None:
        if flt is None:
            return None

        palette = [
            wx.Colour(180, 40, 40),
            wx.Colour(30, 95, 170),
            wx.Colour(28, 125, 70),
            wx.Colour(140, 70, 20),
            wx.Colour(110, 55, 145),
            wx.Colour(20, 120, 120),
            wx.Colour(155, 50, 90),
            wx.Colour(90, 90, 90),
        ]
        idx = sum(ord(ch) for ch in flt.id) % len(palette)
        return palette[idx]

    def _background_for_filter(self, flt: FilterConfig | None) -> wx.Colour | None:
        if flt is None:
            return None

        palette = [
            wx.Colour(255, 235, 235),
            wx.Colour(234, 242, 255),
            wx.Colour(232, 248, 236),
            wx.Colour(252, 243, 228),
            wx.Colour(242, 234, 250),
            wx.Colour(231, 247, 247),
            wx.Colour(248, 232, 240),
            wx.Colour(238, 238, 238),
        ]
        idx = sum(ord(ch) for ch in flt.id) % len(palette)
        return palette[idx]

    def _ansi_to_color(self, code: int) -> wx.Colour | None:
        color_map = {
            30: wx.Colour(0, 0, 0),
            31: wx.Colour(205, 49, 49),
            32: wx.Colour(13, 188, 121),
            33: wx.Colour(229, 229, 16),
            34: wx.Colour(36, 114, 200),
            35: wx.Colour(188, 63, 188),
            36: wx.Colour(17, 168, 205),
            37: wx.Colour(229, 229, 229),
            90: wx.Colour(102, 102, 102),
            91: wx.Colour(241, 76, 76),
            92: wx.Colour(35, 209, 139),
            93: wx.Colour(245, 245, 67),
            94: wx.Colour(59, 142, 234),
            95: wx.Colour(214, 112, 214),
            96: wx.Colour(41, 184, 219),
            97: wx.Colour(255, 255, 255),
        }
        return color_map.get(code)

    def _ansi_to_background_color(self, code: int) -> wx.Colour | None:
        color_map = {
            40: wx.Colour(0, 0, 0),
            41: wx.Colour(205, 49, 49),
            42: wx.Colour(13, 188, 121),
            43: wx.Colour(229, 229, 16),
            44: wx.Colour(36, 114, 200),
            45: wx.Colour(188, 63, 188),
            46: wx.Colour(17, 168, 205),
            47: wx.Colour(229, 229, 229),
            100: wx.Colour(102, 102, 102),
            101: wx.Colour(241, 76, 76),
            102: wx.Colour(35, 209, 139),
            103: wx.Colour(245, 245, 67),
            104: wx.Colour(59, 142, 234),
            105: wx.Colour(214, 112, 214),
            106: wx.Colour(41, 184, 219),
            107: wx.Colour(255, 255, 255),
        }
        return color_map.get(code)

    def _parse_ansi_segments(self, text: str) -> list[tuple[str, wx.Colour | None, wx.Colour | None]]:
        segments: list[tuple[str, wx.Colour | None, wx.Colour | None]] = []
        cursor = 0
        current_color: wx.Colour | None = None
        current_background: wx.Colour | None = None

        for match in self._ansi_re.finditer(text):
            start, end = match.span()
            if start > cursor:
                segments.append((text[cursor:start], current_color, current_background))

            raw_codes = match.group(1)
            codes = [0] if raw_codes == "" else [int(c) for c in raw_codes.split(";") if c.isdigit()]
            for code in codes:
                if code == 0:
                    current_color = None
                    current_background = None
                elif code == 39:
                    current_color = None
                elif code == 49:
                    current_background = None
                else:
                    maybe = self._ansi_to_color(code)
                    if maybe is not None:
                        current_color = maybe
                        continue

                    maybe_bg = self._ansi_to_background_color(code)
                    if maybe_bg is not None:
                        current_background = maybe_bg

            cursor = end

        if cursor < len(text):
            segments.append((text[cursor:], current_color, current_background))

        return segments

    def _set_text_style(self, color: wx.Colour | None, background: wx.Colour | None) -> None:
        self.log_txt.SetDefaultStyle(
            wx.TextAttr(
                colText=color or DEFAULT_LOG_FG,
                colBack=background or DEFAULT_LOG_BG,
            )
        )

    def _append_styled_entry(self, entry: LogEntry) -> None:
        line = self._entry_text(entry) + "\n"
        match_filter = self._find_matching_filter(entry)
        base_color = self._color_for_filter(match_filter)
        base_background = self._background_for_filter(match_filter)
        segments = self._parse_ansi_segments(line)

        for text, ansi_color, ansi_background in segments:
            if not text:
                continue
            self._set_text_style(ansi_color or base_color, ansi_background or base_background)
            self.log_txt.AppendText(text)

        self._set_text_style(None, None)

    def _render(self) -> None:
        self.log_txt.Freeze()
        self.log_txt.Clear()
        for entry in self._entries:
            if self._entry_visible(entry):
                self._append_styled_entry(entry)
        self.log_txt.Thaw()

    def _emit_filters_changed(self) -> None:
        self._on_filters_changed(self.get_filters())

    def add_filter(self) -> None:
        self._add_filter(None)

    def _add_filter(self, _evt: wx.CommandEvent | None) -> None:
        dlg = FilterEditDialog(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            value = dlg.get_value()
            if value:
                self._filters.append(value)
                self._rebuild_filter_row()
                self._emit_filters_changed()
                self._render()
        dlg.Destroy()

    def _clear_clicked(self, _evt: wx.CommandEvent) -> None:
        self._on_clear()

    def _toggle_filter(self, filter_id: str, enabled: bool) -> None:
        for flt in self._filters:
            if flt.id == filter_id:
                flt.enabled = enabled
                break
        self._emit_filters_changed()
        self._render()

    def _edit_filter(self, filter_id: str) -> None:
        target = next((f for f in self._filters if f.id == filter_id), None)
        if not target:
            return

        dlg = FilterEditDialog(self, target)
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.get_value()
            if updated:
                for i, flt in enumerate(self._filters):
                    if flt.id == filter_id:
                        self._filters[i] = updated
                        break
                self._rebuild_filter_row()
                self._emit_filters_changed()
                self._render()
        dlg.Destroy()

    def _delete_filter(self, filter_id: str) -> None:
        target = next((f for f in self._filters if f.id == filter_id), None)
        if not target:
            return

        res = wx.MessageBox(
            f"Delete filter '{target.name}'?",
            "Confirm Delete",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if res != wx.YES:
            return

        self._filters = [f for f in self._filters if f.id != filter_id]
        self._rebuild_filter_row()
        self._emit_filters_changed()
        self._render()

    def _filter_context_menu(self, evt: wx.ContextMenuEvent, filter_id: str) -> None:
        menu = wx.Menu()
        edit_item = menu.Append(wx.ID_ANY, "Edit")
        del_item = menu.Append(wx.ID_ANY, "Delete")

        def _safe_action(action: Callable[[], None]) -> None:
            try:
                action()
            except Exception as ex:
                wx.MessageBox(
                    f"Filter action failed:\n{ex}",
                    "Filter Error",
                    wx.OK | wx.ICON_ERROR,
                )

        menu.Bind(wx.EVT_MENU, lambda _e: _safe_action(lambda: self._edit_filter(filter_id)), edit_item)
        menu.Bind(wx.EVT_MENU, lambda _e: _safe_action(lambda: self._delete_filter(filter_id)), del_item)

        self.PopupMenu(menu)
        menu.Destroy()

    def _rebuild_filter_row(self) -> None:
        self.filter_row.Clear(delete_windows=True)

        for flt in self._filters:
            toggle = wx.ToggleButton(self, label=flt.name)
            toggle.SetValue(flt.enabled)
            mode_tags = []
            if flt.use_regex:
                mode_tags.append("regex")
            if flt.case_sensitive:
                mode_tags.append("case-sensitive")
            tip = flt.pattern
            if mode_tags:
                tip = f"{tip}  [{', '.join(mode_tags)}]"
            toggle.SetToolTip(tip)
            toggle.Bind(
                wx.EVT_TOGGLEBUTTON,
                lambda evt, fid=flt.id: self._toggle_filter(fid, evt.IsChecked()),
            )
            toggle.Bind(
                wx.EVT_CONTEXT_MENU,
                lambda evt, fid=flt.id: self._filter_context_menu(evt, fid),
            )
            self.filter_row.Add(toggle, 0, wx.RIGHT, 6)

        self.filter_row.Layout()
        self.Layout()
