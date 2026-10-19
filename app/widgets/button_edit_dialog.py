from __future__ import annotations

from pathlib import Path

import wx

from app.models.config_models import CommandButtonConfig
from app.services.icon_service import (
    configured_icon_default_color,
    discover_icons,
    normalize_hex_color,
    resolve_button_bitmap,
)

class BuiltinArtPickerDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, current_art: str = ""):
        super().__init__(parent, title="Pick Icon", size=(760, 480))
        self.selected_art: str | None = None

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        helper = wx.StaticText(panel, label="Icons are loaded from ./icons. Click a tile to select it.")
        root.Add(helper, 0, wx.ALL, 10)

        scroll = wx.ScrolledWindow(panel, style=wx.VSCROLL)
        scroll.SetScrollRate(10, 10)
        grid = wx.WrapSizer(wx.HORIZONTAL)

        icon_items = discover_icons()
        for icon_name, icon_path in icon_items:
            preview_cfg = CommandButtonConfig(icon_value=icon_name)
            bmp = resolve_button_bitmap(preview_cfg, size=(32, 32), art_client=wx.ART_BUTTON)
            tile = wx.Button(scroll, label=icon_name, size=(132, 72))
            if bmp and bmp.IsOk():
                tile.SetBitmap(bmp)

            if icon_name == current_art or str(icon_path) == current_art:
                font = tile.GetFont()
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                tile.SetFont(font)

            tile.Bind(wx.EVT_BUTTON, lambda _e, name=icon_name: self._on_pick(name))
            grid.Add(tile, 0, wx.ALL, 4)

        if not icon_items:
            missing = wx.StaticText(scroll, label="No icon files found in ./icons")
            grid.Add(missing, 0, wx.ALL, 8)

        scroll.SetSizer(grid)
        root.Add(scroll, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        cancel_row = wx.StdDialogButtonSizer()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        cancel_row.AddButton(cancel_btn)
        cancel_row.Realize()
        root.Add(cancel_row, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        panel.SetSizer(root)

    def _on_pick(self, icon_name: str) -> None:
        self.selected_art = icon_name
        self.EndModal(wx.ID_OK)


class ButtonEditDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, button: CommandButtonConfig | None = None):
        super().__init__(parent, title="Edit Button", size=(680, 460))

        self._id = button.id if button else None
        self._result: CommandButtonConfig | None = None
        current = button or CommandButtonConfig()

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)
        form.AddGrowableRow(4, 1)

        self.label_txt = wx.TextCtrl(panel, value=current.label, style=wx.TE_PROCESS_ENTER)
        self.show_name_chk = wx.CheckBox(panel, label="Show name")
        self.show_name_chk.SetValue(current.show_name)
        self.show_errors_chk = wx.CheckBox(panel, label="Show errors")
        self.show_errors_chk.SetValue(current.show_errors)
        self.success_value_lbl = wx.StaticText(panel, label="Success value")
        self.success_value_txt = wx.TextCtrl(panel, value=str(current.success_value), style=wx.TE_PROCESS_ENTER)
        self.success_value_txt.SetMinSize((56, -1))
        self.show_gui_on_run_chk = wx.CheckBox(panel, label="Show CmdBox when run")
        self.show_gui_on_run_chk.SetValue(current.show_gui_on_run)
        self.command_txt = wx.TextCtrl(panel, value=current.command, style=wx.TE_MULTILINE)
        self.command_txt.SetMinSize((-1, 120))
        self.icon_value_txt = wx.TextCtrl(panel, value=current.icon_value, style=wx.TE_PROCESS_ENTER)
        self.shortcut_txt = wx.TextCtrl(panel, value=current.shortcut, style=wx.TE_PROCESS_ENTER)
        self.icon_use_custom_chk = wx.CheckBox(panel, label="Use custom icon color")
        self.icon_use_custom_chk.SetValue(bool(current.icon_custom_color.strip()))
        custom_seed_color = current.icon_custom_color or configured_icon_default_color(current.icon_value) or "#FFFFFF"
        self.icon_custom_color_picker = wx.ColourPickerCtrl(
            panel,
            colour=wx.Colour(normalize_hex_color(custom_seed_color, "#FFFFFF")),
        )
        self.icon_preview = wx.StaticBitmap(panel, bitmap=wx.Bitmap(32, 32))

        self.label_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.success_value_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.icon_value_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.icon_value_txt.Bind(wx.EVT_TEXT, self._on_icon_config_changed)
        self.shortcut_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.show_errors_chk.Bind(wx.EVT_CHECKBOX, self._on_show_errors_toggle)
        self.icon_use_custom_chk.Bind(wx.EVT_CHECKBOX, self._on_icon_config_changed)
        self.icon_custom_color_picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self._on_icon_config_changed)

        browse_btn = wx.Button(panel, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)

        builtin_btn = wx.Button(panel, label="Built-in...")
        builtin_btn.Bind(wx.EVT_BUTTON, self._on_pick_builtin)

        form.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.label_txt, 1, wx.EXPAND)

        form.Add((0, 0))
        form.Add(self.show_name_chk, 0)

        form.Add((0, 0))
        show_errors_row = wx.BoxSizer(wx.HORIZONTAL)
        show_errors_row.Add(self.show_errors_chk, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 12)
        show_errors_row.Add(self.success_value_lbl, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        show_errors_row.Add(self.success_value_txt, 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(show_errors_row, 0, wx.EXPAND)

        form.Add((0, 0))
        form.Add(self.show_gui_on_run_chk, 0)

        form.Add(wx.StaticText(panel, label="Command"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.command_txt, 1, wx.EXPAND)

        form.Add(wx.StaticText(panel, label="Shortcut (example: Ctrl+Alt+1)"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.shortcut_txt, 1, wx.EXPAND)

        icon_row = wx.BoxSizer(wx.HORIZONTAL)
        icon_row.Add(self.icon_value_txt, 1, wx.RIGHT | wx.EXPAND, 8)
        icon_row.Add(builtin_btn, 0, wx.RIGHT, 6)
        icon_row.Add(browse_btn, 0)

        form.Add(wx.StaticText(panel, label="Icon"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(icon_row, 1, wx.EXPAND)

        custom_color_row = wx.BoxSizer(wx.HORIZONTAL)
        custom_color_row.Add(self.icon_use_custom_chk, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)
        custom_color_row.Add(self.icon_custom_color_picker, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)
        custom_color_row.Add(wx.StaticText(panel, label="Preview"), 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)
        custom_color_row.Add(self.icon_preview, 0, wx.ALIGN_CENTER_VERTICAL)
        custom_color_row.AddStretchSpacer(1)

        form.Add(wx.StaticText(panel, label="Icon color"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(custom_color_row, 1, wx.EXPAND)

        root.Add(form, 1, wx.ALL | wx.EXPAND, 12)

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
        self._sync_show_errors_ui()
        self._sync_icon_color_ui()
        self._refresh_icon_preview()

    def _on_show_errors_toggle(self, _evt: wx.CommandEvent) -> None:
        self._sync_show_errors_ui()

    def _sync_show_errors_ui(self) -> None:
        enabled = self.show_errors_chk.GetValue()
        self.success_value_lbl.Show(enabled)
        self.success_value_txt.Show(enabled)
        self.success_value_lbl.Enable(enabled)
        self.success_value_txt.Enable(enabled)
        self.Layout()

    def _on_icon_config_changed(self, _evt: wx.CommandEvent) -> None:
        self._sync_icon_color_ui()
        self._refresh_icon_preview()

    def _sync_icon_color_ui(self) -> None:
        use_custom = self.icon_use_custom_chk.GetValue()
        self.icon_custom_color_picker.Enable(use_custom)
        self.Layout()

    def _refresh_icon_preview(self) -> None:
        preview_cfg = self._build_value(show_messages=False)
        if preview_cfg is None:
            self.icon_preview.SetBitmap(wx.Bitmap(32, 32))
            return
        bitmap = resolve_button_bitmap(preview_cfg, size=(32, 32), art_client=wx.ART_OTHER)
        if bitmap and bitmap.IsOk():
            self.icon_preview.SetBitmap(bitmap)
        else:
            self.icon_preview.SetBitmap(wx.Bitmap(32, 32))

    def _on_browse(self, _evt: wx.CommandEvent) -> None:
        with wx.FileDialog(
            self,
            "Pick icon file",
            wildcard="Image files (*.png;*.jpg;*.bmp)|*.png;*.jpg;*.bmp|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._apply_icon_selection(dlg.GetPath())

    def _on_pick_builtin(self, _evt: wx.CommandEvent) -> None:
        current = self.icon_value_txt.GetValue().strip()
        dlg = BuiltinArtPickerDialog(self, current_art=current)
        if dlg.ShowModal() == wx.ID_OK and dlg.selected_art:
            self._apply_icon_selection(dlg.selected_art)
        dlg.Destroy()

    def _apply_icon_selection(self, icon_value: str) -> None:
        self.icon_value_txt.SetValue(icon_value)
        self.icon_use_custom_chk.SetValue(False)
        default_color = configured_icon_default_color(icon_value) or "#FFFFFF"
        self.icon_custom_color_picker.SetColour(wx.Colour(normalize_hex_color(default_color, "#FFFFFF")))
        self._sync_icon_color_ui()
        self._refresh_icon_preview()

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        value = self._build_value(show_messages=True)
        if value is None:
            return
        self._result = value
        self.EndModal(wx.ID_OK)

    def _build_value(self, show_messages: bool) -> CommandButtonConfig | None:
        label = self.label_txt.GetValue().strip()
        command = self.command_txt.GetValue().strip()
        icon_value = self.icon_value_txt.GetValue().strip()
        success_value_raw = self.success_value_txt.GetValue().strip()
        shortcut = "+".join(part.strip().upper() for part in self.shortcut_txt.GetValue().split("+") if part.strip())
        default_color = configured_icon_default_color(icon_value) or "#FFFFFF"
        custom_color = ""
        if self.icon_use_custom_chk.GetValue():
            custom_color = self.icon_custom_color_picker.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)

        if not label:
            if show_messages:
                wx.MessageBox("Label is required.", "Validation", wx.OK | wx.ICON_WARNING)
            return None

        if icon_value and ("\\" in icon_value or "/" in icon_value or "." in Path(icon_value).name):
            icon_path = Path(icon_value)
            if not icon_path.exists():
                if not show_messages:
                    return None
                res = wx.MessageBox(
                    "Icon file does not exist. Save anyway?",
                    "Missing File",
                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                )
                if res != wx.YES:
                    return None

        try:
            success_value = int(success_value_raw or "0")
        except ValueError:
            if show_messages:
                wx.MessageBox("Success value must be an integer.", "Validation", wx.OK | wx.ICON_WARNING)
            return None

        out = CommandButtonConfig(
            label=label,
            enabled=True,
            show_name=self.show_name_chk.GetValue(),
            show_errors=self.show_errors_chk.GetValue(),
            success_value=success_value,
            show_gui_on_run=self.show_gui_on_run_chk.GetValue(),
            command=command,
            icon_value=icon_value,
            icon_default_color=default_color,
            icon_custom_color=custom_color,
            shortcut=shortcut,
        )
        if self._id:
            out.id = self._id
        return out

    def get_value(self) -> CommandButtonConfig | None:
        if self._result is not None:
            return self._result
        return self._build_value(show_messages=False)
