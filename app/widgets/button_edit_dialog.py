from __future__ import annotations

from pathlib import Path

import wx

from app.models.config_models import CommandButtonConfig
from app.services.runtime_paths import icons_dir


ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".ico", ".gif")


def _icons_dir() -> Path:
    return icons_dir()


def _discover_icons() -> list[tuple[str, Path]]:
    root = _icons_dir()
    if not root.exists() or not root.is_dir():
        return []

    out: list[tuple[str, Path]] = []
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_file() and p.suffix.lower() in ICON_EXTENSIONS:
            out.append((p.stem, p))
    return out


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

        icon_items = _discover_icons()
        for icon_name, icon_path in icon_items:
            img = wx.Image(str(icon_path))
            if not img.IsOk():
                continue

            bmp = wx.Bitmap(img.Scale(32, 32, wx.IMAGE_QUALITY_HIGH))
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
        super().__init__(parent, title="Edit Button", size=(520, 280))

        self._id = button.id if button else None
        self._result: CommandButtonConfig | None = None
        current = button or CommandButtonConfig()

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)

        self.label_txt = wx.TextCtrl(panel, value=current.label)
        self.show_name_chk = wx.CheckBox(panel, label="Show name")
        self.show_name_chk.SetValue(current.show_name)
        self.command_txt = wx.TextCtrl(panel, value=current.command)
        self.icon_value_txt = wx.TextCtrl(panel, value=current.icon_value)
        self.shortcut_txt = wx.TextCtrl(panel, value=current.shortcut)

        browse_btn = wx.Button(panel, label="Browse...")
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)

        builtin_btn = wx.Button(panel, label="Built-in...")
        builtin_btn.Bind(wx.EVT_BUTTON, self._on_pick_builtin)

        form.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.label_txt, 1, wx.EXPAND)

        form.Add((0, 0))
        form.Add(self.show_name_chk, 0)

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

        root.Add(form, 1, wx.ALL | wx.EXPAND, 12)

        btns = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        btns.AddButton(ok_btn)
        btns.AddButton(cancel_btn)
        btns.Realize()
        root.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 12)

        panel.SetSizer(root)

    def _on_browse(self, _evt: wx.CommandEvent) -> None:
        with wx.FileDialog(
            self,
            "Pick icon file",
            wildcard="Image files (*.png;*.jpg;*.bmp)|*.png;*.jpg;*.bmp|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.icon_value_txt.SetValue(dlg.GetPath())

    def _on_pick_builtin(self, _evt: wx.CommandEvent) -> None:
        current = self.icon_value_txt.GetValue().strip()
        dlg = BuiltinArtPickerDialog(self, current_art=current)
        if dlg.ShowModal() == wx.ID_OK and dlg.selected_art:
            self.icon_value_txt.SetValue(dlg.selected_art)
        dlg.Destroy()

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
        shortcut = "+".join(part.strip().upper() for part in self.shortcut_txt.GetValue().split("+") if part.strip())

        if not label:
            if show_messages:
                wx.MessageBox("Label is required.", "Validation", wx.OK | wx.ICON_WARNING)
            return None
        if not command:
            if show_messages:
                wx.MessageBox("Command is required.", "Validation", wx.OK | wx.ICON_WARNING)
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

        out = CommandButtonConfig(
            label=label,
            show_name=self.show_name_chk.GetValue(),
            command=command,
            icon_value=icon_value,
            shortcut=shortcut,
        )
        if self._id:
            out.id = self._id
        return out

    def get_value(self) -> CommandButtonConfig | None:
        if self._result is not None:
            return self._result
        return self._build_value(show_messages=False)
