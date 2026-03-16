@echo off
setlocal

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
set "EXE_PATH=%REPO_ROOT%\dist\CmdBox\CmdBox.exe"

if not exist "%EXE_PATH%" (
    echo Could not find built executable at: %EXE_PATH%
    exit /b 1
)

reg add "HKCU\Software\Classes\.cmdbox" /ve /d "CmdBox.Project" /f >nul
reg add "HKCU\Software\Classes\CmdBox.Project" /ve /d "CmdBox Project File" /f >nul
reg add "HKCU\Software\Classes\CmdBox.Project\DefaultIcon" /ve /d "\"%EXE_PATH%\",0" /f >nul
set "COMMAND_VALUE=\"%EXE_PATH%\" \"%%1\""
reg add "HKCU\Software\Classes\CmdBox.Project\shell\open\command" /ve /d "%COMMAND_VALUE%" /f >nul

echo Registered .cmdbox file association for current user.
echo You may need to restart Explorer or sign out/in to refresh file icons and associations.
