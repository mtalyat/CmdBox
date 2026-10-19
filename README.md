# CmdBox

CmdBox is a wxPython desktop app for running shell commands from an editable grid of buttons, with live output logging and toggleable filters.

## Features

- Editable command button grid.
- Drag-and-drop button reordering.
- Right-click actions: add, edit, duplicate, delete.
- Button editor supports:
  - Label text
  - Shell command
  - Icon value: file path or built-in wx ART_ name
  - Dynamic grayscale icon recolor with app-configured per-icon default color and optional custom override
  - Optional shortcut (for example: `Ctrl+Alt+1`, `Ctrl+Shift+R`, `Alt+F2`)
- Live log panel for command output:
  - Captures stdout and stderr
  - Supports concurrent command execution
  - Filter row with add/edit/delete and click-to-toggle filters
  - OR matching across enabled filters
  - Clear log button
- Project file workflow with custom `.cmdbox` extension:
  - New and Open from the File menu
  - Automatic save for all project edits (manual save actions removed)
  - Profile switching with `Ctrl+<` and `Ctrl+>` while the CmdBox window is focused
  - If auto-save fails, CmdBox warns before potentially discarding unsaved changes
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
- Use the File menu to create/open CmdBox settings files.
- CmdBox auto-saves all edits to the active project file.
- If you launch CmdBox without a file argument, it reopens the most recently used project file (if it still exists).
- You can launch directly into a project with:

```powershell
python main.py .\my-project.cmdbox
```

- If you register a Windows file association for `.cmdbox`, double-clicking a project file can open it directly.

## Icon Default Colors

- Configure shipped icon defaults in `icons/icon-default-colors.json`.
- Keys can be an icon stem (for example `play`), file name, or full icon value.
- Values must be hex colors like `#22C55E`.
- Users can still choose a custom override color per button in the editor.

To register the association for your current user on Windows:

```bat
scripts\register-file-association.bat
```

To build the Windows executable bundle:

```bat
scripts\build.bat
```

## Notes

- Filters are case-insensitive substring matches against level, source, and message text.
- If no filters are enabled, all log lines are shown.
- Registered shortcuts are global while CmdBox is running, so they can trigger commands even when the app window is not focused.
