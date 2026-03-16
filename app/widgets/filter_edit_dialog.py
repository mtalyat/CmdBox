from __future__ import annotations

import wx

from app.models.config_models import FilterConfig


class FilterEditDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, flt: FilterConfig | None = None):
        super().__init__(parent, title="Edit Filter", size=(420, 260))

        self._id = flt.id if flt else None
        self._result: FilterConfig | None = None
        current = flt or FilterConfig()

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)

        self.name_txt = wx.TextCtrl(panel, value=current.name, style=wx.TE_PROCESS_ENTER)
        self.pattern_txt = wx.TextCtrl(panel, value=current.pattern, style=wx.TE_PROCESS_ENTER)
        self.name_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.pattern_txt.Bind(wx.EVT_TEXT_ENTER, self._on_ok)
        self.enabled_chk = wx.CheckBox(panel, label="Enabled")
        self.enabled_chk.SetValue(current.enabled)
        self.case_sensitive_chk = wx.CheckBox(panel, label="Case sensitive")
        self.case_sensitive_chk.SetValue(current.case_sensitive)
        self.use_regex_chk = wx.CheckBox(panel, label="Use regex")
        self.use_regex_chk.SetValue(current.use_regex)

        form.Add(wx.StaticText(panel, label="Name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.name_txt, 1, wx.EXPAND)

        form.Add(wx.StaticText(panel, label="Pattern"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.pattern_txt, 1, wx.EXPAND)

        form.Add((0, 0))
        form.Add(self.enabled_chk, 0)

        form.Add((0, 0))
        options_row = wx.BoxSizer(wx.HORIZONTAL)
        options_row.Add(self.case_sensitive_chk, 0, wx.RIGHT, 16)
        options_row.Add(self.use_regex_chk, 0)
        form.Add(options_row, 0)

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

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        value = self._build_value(show_messages=True)
        if value is None:
            return
        self._result = value
        self.EndModal(wx.ID_OK)

    def _build_value(self, show_messages: bool) -> FilterConfig | None:
        name = self.name_txt.GetValue().strip()
        pattern = self.pattern_txt.GetValue().strip()

        if not name:
            if show_messages:
                wx.MessageBox("Filter name is required.", "Validation", wx.OK | wx.ICON_WARNING)
            return None
        if not pattern:
            if show_messages:
                wx.MessageBox("Filter pattern is required.", "Validation", wx.OK | wx.ICON_WARNING)
            return None

        if self.use_regex_chk.GetValue():
            import re
            try:
                re.compile(pattern)
            except re.error as exc:
                if show_messages:
                    wx.MessageBox(f"Invalid regex pattern:\n{exc}", "Validation", wx.OK | wx.ICON_WARNING)
                return None

        out = FilterConfig(
            name=name,
            pattern=pattern,
            enabled=self.enabled_chk.GetValue(),
            case_sensitive=self.case_sensitive_chk.GetValue(),
            use_regex=self.use_regex_chk.GetValue(),
        )
        if self._id:
            out.id = self._id
        return out

    def get_value(self) -> FilterConfig | None:
        if self._result is not None:
            return self._result
        return self._build_value(show_messages=False)
