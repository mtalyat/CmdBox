# CmdBox

CmdBox is a wxPython desktop app for running shell commands from an editable grid of buttons, with live output logging and toggleable filters.

## Features

- Editable command button grid.
- Right-click actions: add, edit, duplicate, delete.
- Button editor supports:
  - Label text
  - Shell command
  - Icon value: file path or built-in wx ART_ name
  - Optional shortcut (for example: `Ctrl+Alt+1`, `Ctrl+Shift+R`, `Alt+F2`)
- Live log panel for command output:
  - Captures stdout and stderr
  - Supports concurrent command execution
  - Filter row with add/edit/delete and click-to-toggle filters
  - OR matching across enabled filters
  - Clear log button
- Project file workflow with custom `.cmdbox` extension:
  - New, Open, Save, Save As from the File menu
  - Unsaved-change prompt on close/open/new
  - Open a project file from command line argument

## Setup

1. Install dependencies.
2. Run the app.

```powershell
pip install -r requirements.txt
python main.py
```

## Project Files

- CmdBox project files use the `.cmdbox` extension.
- Use the File menu to create/open/save project settings.
- If you launch CmdBox without a file argument, it reopens the most recently used project file (if it still exists).
- You can launch directly into a project with:

```powershell
python main.py .\my-project.cmdbox
```

- If you register a Windows file association for `.cmdbox` to run `cmdbox.bat`, double-clicking a project file can open it directly.

To register the association for your current user on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register-file-association.ps1
```

## Notes

- Filters are case-insensitive substring matches against level, source, and message text.
- If no filters are enabled, all log lines are shown.
- Registered shortcuts are global while CmdBox is running, so they can trigger commands even when the app window is not focused.
