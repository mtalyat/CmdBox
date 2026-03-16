from __future__ import annotations

import wx

from app.models.app_settings_models import AppSettings, LogDisplaySettings


class SettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, settings: AppSettings):
        super().__init__(parent, title="Settings", size=(460, 320))

        self._result: AppSettings | None = None
        current = settings

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        notebook = wx.Notebook(panel)
        log_page = wx.Panel(notebook)
        notebook.AddPage(log_page, "Log")

        log_root = wx.BoxSizer(wx.VERTICAL)
        help_text = wx.StaticText(
            log_page,
            label="Choose which metadata fields are shown for each log line.",
        )
        log_root.Add(help_text, 0, wx.ALL, 10)

        self.show_timestamp_chk = wx.CheckBox(log_page, label="Show timestamp")
        self.show_level_chk = wx.CheckBox(log_page, label="Show level")
        self.show_command_name_chk = wx.CheckBox(log_page, label="Show command name")
        self.show_source_chk = wx.CheckBox(log_page, label="Show source")

        self.show_timestamp_chk.SetValue(current.log_display.show_timestamp)
        self.show_level_chk.SetValue(current.log_display.show_level)
        self.show_command_name_chk.SetValue(current.log_display.show_command_name)
        self.show_source_chk.SetValue(current.log_display.show_source)

        log_root.Add(self.show_timestamp_chk, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        log_root.Add(self.show_level_chk, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        log_root.Add(self.show_command_name_chk, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        log_root.Add(self.show_source_chk, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        note = wx.StaticText(log_page, label="Source corresponds to the run/source ID shown in brackets.")
        log_root.Add(note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        log_page.SetSizer(log_root)

        root.Add(notebook, 1, wx.ALL | wx.EXPAND, 10)

        btns = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(panel, wx.ID_OK)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        btns.AddButton(ok_btn)
        btns.AddButton(cancel_btn)
        btns.Realize()
        root.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        panel.SetSizer(root)

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        log_display = LogDisplaySettings(
            show_timestamp=self.show_timestamp_chk.GetValue(),
            show_level=self.show_level_chk.GetValue(),
            show_command_name=self.show_command_name_chk.GetValue(),
            show_source=self.show_source_chk.GetValue(),
        )
        self._result = AppSettings(log_display=log_display)
        self.EndModal(wx.ID_OK)

    def get_value(self) -> AppSettings | None:
        return self._result
