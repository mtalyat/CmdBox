from __future__ import annotations

import wx

OVERLAY_COLOR = wx.Colour(240, 240, 240)
TEXT_COLOR = wx.Colour(28, 28, 28)

class RunOverlay(wx.Frame):
    def __init__(self, parent: wx.Window | None):
        style = wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP | wx.BORDER_SIMPLE
        super().__init__(parent, title="", style=style)

        panel = wx.Panel(self)
        panel.SetBackgroundColour(OVERLAY_COLOR)
        root = wx.BoxSizer(wx.HORIZONTAL)

        self._icon = wx.StaticBitmap(panel, bitmap=wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_OTHER, (24, 24)))
        self._text = wx.StaticText(panel, label="Running")
        self._text.SetForegroundColour(TEXT_COLOR)

        root.Add(self._icon, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        root.Add(self._text, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        panel.SetSizer(root)
        self.SetClientSize((220, 44))
        self.SetBackgroundColour(OVERLAY_COLOR)

    def _place_top_right(self, slot_index: int = 0) -> None:
        parent = self.GetParent()
        display_index = wx.Display.GetFromWindow(parent) if parent else wx.NOT_FOUND
        if display_index == wx.NOT_FOUND:
            display_index = 0
        display_rect = wx.Display(display_index).GetClientArea()

        width, height = self.GetSize()
        x = display_rect.x + display_rect.width - width - 16
        y = display_rect.y + 16 + (slot_index * (height + 8))
        self.SetPosition((x, y))

    def show_running(self, bitmap: wx.Bitmap | None, label: str, running_count: int, slot_index: int = 0) -> None:
        if bitmap and bitmap.IsOk():
            self._icon.SetBitmap(bitmap)

        if running_count > 1:
            self._text.SetLabel(f"{label} (+{running_count - 1})")
        else:
            self._text.SetLabel(f"{label}")

        self.Fit()
        self._place_top_right(slot_index=slot_index)
        if hasattr(self, "ShowWithoutActivating"):
            self.ShowWithoutActivating()
        else:
            self.Show(True)

    def hide_overlay(self) -> None:
        self.Hide()
