from __future__ import annotations

import wx

from app.models.config_models import CommandButtonConfig, ProjectConfig


class ProjectSettingsDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, project: ProjectConfig, buttons: list[CommandButtonConfig]):
        super().__init__(parent, title="Profile Settings", size=(720, 560))

        self._buttons = buttons
        self._result: ProjectConfig | None = None
        self._project_id = project.id

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=10)
        form.AddGrowableCol(1, 1)

        self.name_txt = wx.TextCtrl(panel, value=project.name, style=wx.TE_PROCESS_ENTER)
        form.Add(wx.StaticText(panel, label="Project name"), 0, wx.ALIGN_CENTER_VERTICAL)
        form.Add(self.name_txt, 1, wx.EXPAND)

        root.Add(form, 0, wx.ALL | wx.EXPAND, 12)

        vars_label = wx.StaticText(panel, label="Variables (one per line: NAME=VALUE)")
        root.Add(vars_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        vars_text = "\n".join(f"{k}={v}" for k, v in project.variables.items())
        self.variables_txt = wx.TextCtrl(panel, value=vars_text, style=wx.TE_MULTILINE)
        self.variables_txt.SetMinSize((-1, 180))
        root.Add(self.variables_txt, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        btn_filter_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_filter_row.Add(wx.StaticText(panel, label="Available buttons for this profile"), 0, wx.ALIGN_CENTER_VERTICAL)

        select_all = wx.Button(panel, label="Select all")
        select_all.Bind(wx.EVT_BUTTON, self._on_select_all)
        btn_filter_row.AddStretchSpacer(1)
        btn_filter_row.Add(select_all, 0, wx.RIGHT, 6)

        clear_all = wx.Button(panel, label="Clear all")
        clear_all.Bind(wx.EVT_BUTTON, self._on_clear_all)
        btn_filter_row.Add(clear_all, 0)

        root.Add(btn_filter_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        choices = [f"{btn.label} ({btn.id})" for btn in buttons]
        self.buttons_list = wx.CheckListBox(panel, choices=choices)
        allowed = set(project.allowed_button_ids)
        if allowed:
            for i, btn in enumerate(buttons):
                self.buttons_list.Check(i, btn.id in allowed)
        else:
            for i in range(len(buttons)):
                self.buttons_list.Check(i, True)
        root.Add(self.buttons_list, 1, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

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

    def _on_select_all(self, _evt: wx.CommandEvent) -> None:
        for i in range(self.buttons_list.GetCount()):
            self.buttons_list.Check(i, True)

    def _on_clear_all(self, _evt: wx.CommandEvent) -> None:
        for i in range(self.buttons_list.GetCount()):
            self.buttons_list.Check(i, False)

    def _parse_variables(self) -> dict[str, str] | None:
        variables: dict[str, str] = {}
        for i, line in enumerate(self.variables_txt.GetValue().splitlines(), start=1):
            raw = line.strip()
            if not raw:
                continue
            if "=" not in raw:
                wx.MessageBox(
                    f"Invalid variable on line {i}. Use NAME=VALUE.",
                    "Validation",
                    wx.OK | wx.ICON_WARNING,
                )
                return None
            key, value = raw.split("=", 1)
            key = key.strip()
            if not key:
                wx.MessageBox(
                    f"Variable name cannot be blank (line {i}).",
                    "Validation",
                    wx.OK | wx.ICON_WARNING,
                )
                return None
            variables[key] = value
        return variables

    def _on_ok(self, _evt: wx.CommandEvent) -> None:
        name = self.name_txt.GetValue().strip()
        if not name:
            wx.MessageBox("Project name is required.", "Validation", wx.OK | wx.ICON_WARNING)
            return

        variables = self._parse_variables()
        if variables is None:
            return

        allowed_button_ids = [
            btn.id for i, btn in enumerate(self._buttons) if self.buttons_list.IsChecked(i)
        ]
        if len(allowed_button_ids) == len(self._buttons):
            allowed_button_ids = []

        self._result = ProjectConfig(
            id=self._project_id,
            name=name,
            variables=variables,
            allowed_button_ids=allowed_button_ids,
        )
        self.EndModal(wx.ID_OK)

    def get_value(self) -> ProjectConfig | None:
        return self._result
