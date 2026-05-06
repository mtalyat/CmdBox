from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import wx


@dataclass(frozen=True)
class CommandArgumentSpec:
    name: str
    arg_type: str = "text"
    args: tuple[str, ...] = ()


class CommandArgumentsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, command_name: str, placeholders: list[CommandArgumentSpec]):
        rows = max(1, len(placeholders))
        height = min(640, 160 + (rows * 42))
        title = command_name if command_name else "Command Arguments"
        super().__init__(parent, title=title, size=(560, height))
        self.SetMinSize((500, 240))

        self._result: dict[str, str] | None = None
        self._value_getters: dict[str, callable[[], str]] = {}
        first_input: wx.Window | None = None

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        help_text = wx.StaticText(panel, label="Provide values for the command arguments.")
        root.Add(help_text, 0, wx.ALL, 12)

        scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scroll.SetScrollRate(0, 12)
        form_host = wx.Panel(scroll)
        form_sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)

        for placeholder in placeholders:
            label = wx.StaticText(form_host, label=f"{placeholder.name}:")
            field, get_value, focus_target = self._build_input_field(form_host, placeholder)
            self._value_getters[placeholder.name] = get_value
            if first_input is None and focus_target is not None:
                first_input = focus_target
            form.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            form.Add(field, 1, wx.EXPAND)

        form_sizer.Add(form, 1, wx.EXPAND | wx.ALL, 4)
        form_host.SetSizer(form_sizer)
        scroll.SetSizer(wx.BoxSizer(wx.VERTICAL))
        scroll.GetSizer().Add(form_host, 1, wx.EXPAND | wx.ALL, 8)
        form_host.Layout()
        form_host.Fit()
        scroll.FitInside()

        root.Add(scroll, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        btns = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.SetDefault()
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        btns.AddButton(ok_btn)
        btns.AddButton(cancel_btn)
        btns.Realize()
        root.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 12)

        panel.SetSizer(root)
        self.Layout()

        if first_input is not None:
            first_input.SetFocus()

    def _build_input_field(
        self,
        parent: wx.Window,
        spec: CommandArgumentSpec,
    ) -> tuple[wx.Window, callable[[], str], wx.Window | None]:
        arg_type = (spec.arg_type or "text").strip().lower()

        if arg_type == "int":
            start = self._parse_int(spec.args[0], 0) if spec.args else 0
            step = self._parse_int(spec.args[1], 1) if len(spec.args) > 1 else 1
            ctrl = wx.SpinCtrlDouble(
                parent,
                min=-1_000_000_000,
                max=1_000_000_000,
                inc=max(1, step),
                initial=float(start),
            )
            ctrl.SetDigits(0)

            def _get_int() -> str:
                return str(int(round(ctrl.GetValue())))

            return ctrl, _get_int, ctrl

        if arg_type == "dec":
            start = self._parse_decimal(spec.args[0], Decimal("0")) if spec.args else Decimal("0")
            step = self._parse_decimal(spec.args[1], Decimal("0.1")) if len(spec.args) > 1 else Decimal("0.1")
            digits = self._decimal_digits(step)
            ctrl = wx.SpinCtrlDouble(
                parent,
                min=-1_000_000_000,
                max=1_000_000_000,
                inc=float(step),
                initial=float(start),
            )
            ctrl.SetDigits(digits)

            def _get_dec() -> str:
                return f"{ctrl.GetValue():g}"

            return ctrl, _get_dec, ctrl

        if arg_type == "list":
            options = [item for item in spec.args]
            if not options:
                text = wx.TextCtrl(parent)
                return text, text.GetValue, text
            choice = wx.ComboBox(parent, choices=options, style=wx.CB_READONLY)
            choice.SetSelection(0)
            choice.Bind(wx.EVT_CHAR_HOOK, self._on_list_key)

            def _get_choice() -> str:
                selection = choice.GetSelection()
                if selection == wx.NOT_FOUND:
                    return ""
                return choice.GetString(selection)

            return choice, _get_choice, choice

        if arg_type == "check":
            checkbox = wx.CheckBox(parent)
            flags = {arg.strip().lower() for arg in spec.args}
            starts_checked = "checked" in flags
            returns_int = "int" in flags
            checkbox.SetValue(starts_checked)
            checkbox.Bind(wx.EVT_CHAR_HOOK, self._on_checkbox_key)

            def _get_checkbox() -> str:
                if returns_int:
                    return "1" if checkbox.GetValue() else "0"
                return "true" if checkbox.GetValue() else "false"

            return checkbox, _get_checkbox, checkbox

        if arg_type == "path":
            flags = {arg.strip().lower() for arg in spec.args}
            mode = "directory" if "directory" in flags else "file"
            allow_multiple = "multiple" in flags
            wildcard = self._path_wildcard(spec.args)

            host = wx.Panel(parent)
            row = wx.BoxSizer(wx.HORIZONTAL)
            text = wx.TextCtrl(host)
            browse = wx.Button(host, label="...")
            browse.SetMinSize((36, -1))
            row.Add(text, 1, wx.RIGHT | wx.EXPAND, 8)
            row.Add(browse, 0)
            host.SetSizer(row)

            browse.Bind(
                wx.EVT_BUTTON,
                lambda _evt: self._browse_for_path(text, wildcard, mode, allow_multiple),
            )

            return host, text.GetValue, text

        text = wx.TextCtrl(parent)
        return text, text.GetValue, text

    def _path_wildcard(self, args: tuple[str, ...]) -> str:
        for arg in args:
            token = arg.strip()
            if not token:
                continue
            token_lower = token.lower()
            if token_lower in {"file", "directory", "multiple"}:
                continue
            return token
        return "All files (*.*)|*.*"

    def _browse_for_path(self, text: wx.TextCtrl, wildcard: str, mode: str, allow_multiple: bool) -> None:
        current_value = text.GetValue().strip().strip('"')
        start_path = Path(current_value) if current_value else None

        if mode == "directory":
            style = wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
            if allow_multiple and hasattr(wx, "DD_MULTIPLE"):
                style |= wx.DD_MULTIPLE
            default_path = str(start_path if start_path and start_path.exists() else Path.home())
            with wx.DirDialog(self, "Select directory", defaultPath=default_path, style=style) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                if allow_multiple and hasattr(dlg, "GetPaths"):
                    paths = dlg.GetPaths()
                else:
                    paths = [dlg.GetPath()]
        else:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            if allow_multiple:
                style |= wx.FD_MULTIPLE
            default_dir = ""
            default_file = ""
            if start_path:
                if start_path.exists() and start_path.is_dir():
                    default_dir = str(start_path)
                else:
                    default_dir = str(start_path.parent) if start_path.parent else ""
                    default_file = start_path.name
            with wx.FileDialog(
                self,
                "Select file",
                defaultDir=default_dir,
                defaultFile=default_file,
                wildcard=wildcard,
                style=style,
            ) as dlg:
                if dlg.ShowModal() != wx.ID_OK:
                    return
                paths = dlg.GetPaths() if allow_multiple else [dlg.GetPath()]

        text.SetValue(self._format_selected_paths(paths))

    def _format_selected_paths(self, paths: list[str]) -> str:
        if not paths:
            return ""
        if len(paths) == 1:
            return self._quote_path(paths[0])
        return " ".join(self._quote_path(path) for path in paths)

    def _quote_path(self, path: str) -> str:
        if not path:
            return ""
        if any(ch.isspace() for ch in path):
            return f'"{path}"'
        return path

    def _parse_int(self, raw: str, fallback: int) -> int:
        try:
            value = int(raw.strip())
        except (TypeError, ValueError):
            return fallback
        return value if value > 0 else fallback

    def _parse_decimal(self, raw: str, fallback: Decimal) -> Decimal:
        try:
            value = Decimal(raw.strip())
        except (InvalidOperation, ValueError, AttributeError):
            return fallback
        return value if value > 0 else fallback

    def _decimal_digits(self, value: Decimal) -> int:
        normalized = value.normalize()
        exponent = normalized.as_tuple().exponent
        return max(1, min(8, -exponent))

    def _on_checkbox_key(self, evt: wx.KeyEvent) -> None:
        if evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            checkbox = evt.GetEventObject()
            if isinstance(checkbox, wx.CheckBox):
                checkbox.SetValue(not checkbox.GetValue())
            return
        evt.Skip()

    def _on_list_key(self, evt: wx.KeyEvent) -> None:
        if evt.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            combo = evt.GetEventObject()
            if isinstance(combo, wx.ComboBox) and hasattr(combo, "Popup"):
                combo.Popup()
                return
        evt.Skip()

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        self._result = {name: get_value() for name, get_value in self._value_getters.items()}
        self.EndModal(wx.ID_OK)

    def get_value(self) -> dict[str, str] | None:
        return self._result