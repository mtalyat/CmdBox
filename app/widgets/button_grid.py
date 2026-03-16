from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Callable

import wx

from app.models.config_models import CommandButtonConfig
from app.services.runtime_paths import icons_dir
from app.widgets.button_edit_dialog import ButtonEditDialog


ButtonsChangedHandler = Callable[[list[CommandButtonConfig]], None]
ButtonRunHandler = Callable[[CommandButtonConfig], None]
ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".ico", ".gif")


class ButtonGridPanel(wx.Panel):
    def __init__(
        self,
        parent: wx.Window,
        buttons: list[CommandButtonConfig],
        on_buttons_changed: ButtonsChangedHandler,
        on_run_button: ButtonRunHandler,
    ):
        super().__init__(parent)
        self._buttons: list[CommandButtonConfig] = deepcopy(buttons)
        self._on_buttons_changed = on_buttons_changed
        self._on_run_button = on_run_button

        root = wx.BoxSizer(wx.VERTICAL)

        self.scroll = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self.scroll.SetScrollRate(10, 10)
        self.grid_sizer = wx.WrapSizer(wx.HORIZONTAL)
        self.scroll.SetSizer(self.grid_sizer)
        self.scroll.Bind(wx.EVT_RIGHT_DOWN, self._on_blank_right_click)

        root.Add(self.scroll, 1, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(root)
        self._rebuild_grid()

    def get_buttons(self) -> list[CommandButtonConfig]:
        return deepcopy(self._buttons)

    def set_buttons(self, buttons: list[CommandButtonConfig]) -> None:
        self._buttons = deepcopy(buttons)
        self._rebuild_grid()

    def _emit_changed(self) -> None:
        self._on_buttons_changed(self.get_buttons())

    def add_button(self) -> None:
        self._on_add(None)

    def _on_add(self, _evt: wx.CommandEvent | None) -> None:
        dlg = ButtonEditDialog(self, None)
        if dlg.ShowModal() == wx.ID_OK:
            button = dlg.get_value()
            if button:
                self._buttons.append(button)
                self._rebuild_grid()
                self._emit_changed()
        dlg.Destroy()

    def _on_blank_right_click(self, evt: wx.MouseEvent) -> None:
        menu = wx.Menu()
        add_item = menu.Append(wx.ID_ANY, "Add Button")
        menu.Bind(wx.EVT_MENU, self._on_add, add_item)
        self.PopupMenu(menu, evt.GetPosition())
        menu.Destroy()

    def _on_button_click(self, button: CommandButtonConfig) -> None:
        self._on_run_button(button)

    def _on_button_context(self, evt: wx.ContextMenuEvent, button_id: str) -> None:
        menu = wx.Menu()
        edit_item = menu.Append(wx.ID_ANY, "Edit")
        dup_item = menu.Append(wx.ID_ANY, "Duplicate")
        del_item = menu.Append(wx.ID_ANY, "Delete")

        def _safe_action(action: Callable[[], None]) -> None:
            try:
                action()
            except Exception as ex:
                wx.MessageBox(
                    f"Button action failed:\n{ex}",
                    "Button Error",
                    wx.OK | wx.ICON_ERROR,
                )

        menu.Bind(wx.EVT_MENU, lambda _e: _safe_action(lambda: self._edit_button(button_id)), edit_item)
        menu.Bind(wx.EVT_MENU, lambda _e: _safe_action(lambda: self._duplicate_button(button_id)), dup_item)
        menu.Bind(wx.EVT_MENU, lambda _e: _safe_action(lambda: self._delete_button(button_id)), del_item)

        self.PopupMenu(menu)
        menu.Destroy()

    def _edit_button(self, button_id: str) -> None:
        index = self._find_index(button_id)
        if index < 0:
            return

        dlg = ButtonEditDialog(self, self._buttons[index])
        if dlg.ShowModal() == wx.ID_OK:
            updated = dlg.get_value()
            if updated:
                self._buttons[index] = updated
                self._rebuild_grid()
                self._emit_changed()
        dlg.Destroy()

    def _duplicate_button(self, button_id: str) -> None:
        index = self._find_index(button_id)
        if index < 0:
            return

        original = self._buttons[index]
        clone = CommandButtonConfig(
            label=f"{original.label} Copy",
            show_name=original.show_name,
            command=original.command,
            icon_value=original.icon_value,
            shortcut="",
        )
        self._buttons.insert(index + 1, clone)
        self._rebuild_grid()
        self._emit_changed()

    def _delete_button(self, button_id: str) -> None:
        index = self._find_index(button_id)
        if index < 0:
            return

        res = wx.MessageBox(
            f"Delete '{self._buttons[index].label}'?",
            "Confirm Delete",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        if res != wx.YES:
            return

        self._buttons.pop(index)
        self._rebuild_grid()
        self._emit_changed()

    def _find_index(self, button_id: str) -> int:
        for i, item in enumerate(self._buttons):
            if item.id == button_id:
                return i
        return -1

    def _resolve_bitmap(self, btn_cfg: CommandButtonConfig, size: tuple[int, int] = (16, 16)) -> wx.Bitmap | None:
        icon_value = btn_cfg.icon_value.strip()
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
            bmp = wx.ArtProvider.GetBitmap(art_id, wx.ART_BUTTON, size)
            if bmp and bmp.IsOk():
                return bmp

        return None

    def _rebuild_grid(self) -> None:
        self.scroll.Freeze()
        self.grid_sizer.Clear(delete_windows=True)

        for btn_cfg in self._buttons:
            label = btn_cfg.label
            show_name = btn_cfg.show_name
            icon_size = (56, 56) if show_name else (96, 96)

            bitmap = self._resolve_bitmap(btn_cfg, size=icon_size)
            if not show_name and bitmap:
                ctrl = wx.BitmapButton(self.scroll, bitmap=bitmap, size=(100, 100))
            else:
                ctrl = wx.Button(self.scroll, label=label if show_name else "")
                if bitmap:
                    ctrl.SetBitmap(bitmap)
                    # Place icon above text for a bigger, more readable tile layout.
                    if hasattr(ctrl, "SetBitmapPosition"):
                        ctrl.SetBitmapPosition(wx.TOP)
                    if hasattr(ctrl, "SetBitmapMargins"):
                        ctrl.SetBitmapMargins((0, 4))

            tooltip = btn_cfg.command
            if btn_cfg.shortcut:
                tooltip = f"{tooltip}\nShortcut: {btn_cfg.shortcut}"
            ctrl.SetToolTip(tooltip)
            ctrl.SetMinSize((100, 100))
            ctrl.SetMaxSize((100, 100))

            ctrl.Bind(wx.EVT_BUTTON, lambda _e, b=btn_cfg: self._on_button_click(b))
            ctrl.Bind(
                wx.EVT_CONTEXT_MENU,
                lambda evt, button_id=btn_cfg.id: self._on_button_context(evt, button_id),
            )
            self.grid_sizer.Add(ctrl, 0, wx.RIGHT | wx.BOTTOM, 2)

        self.scroll.Layout()
        self.scroll.FitInside()
        self.scroll.Thaw()
        self.Layout()
