from __future__ import annotations

import wx


class CommandArgumentsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, placeholders: list[str]):
        super().__init__(parent, title="Command Arguments", size=(440, 180))

        self._result: dict[str, str] | None = None
        self._fields: dict[str, wx.TextCtrl] = {}

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        help_text = wx.StaticText(panel, label="Provide values for the command placeholders.")
        root.Add(help_text, 0, wx.ALL, 12)

        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)

        for placeholder in placeholders:
            label = wx.StaticText(panel, label=f"{placeholder}:")
            field = wx.TextCtrl(panel)
            self._fields[placeholder] = field
            form.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
            form.Add(field, 1, wx.EXPAND)

        root.Add(form, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

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

        if placeholders:
            self._fields[placeholders[0]].SetFocus()

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        self._result = {name: field.GetValue() for name, field in self._fields.items()}
        self.EndModal(wx.ID_OK)

    def get_value(self) -> dict[str, str] | None:
        return self._result