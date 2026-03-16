@echo off
setlocal

set "REPO_ROOT=%~dp0.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"
pushd "%REPO_ROOT%" >nul

set "PYTHON_CMD="
call :try_python "%REPO_ROOT%\.venv\Scripts\python.exe"
if defined PYTHON_CMD goto build

call :try_python "C:\Users\mitch\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if defined PYTHON_CMD goto build

call :try_python python
if defined PYTHON_CMD goto build

echo Could not find a Python interpreter with PyInstaller installed.
popd >nul
exit /b 1

:build
call %PYTHON_CMD% -m PyInstaller --noconfirm --clean packaging\CmdBox.spec
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%

:try_python
set "CANDIDATE=%~1"
if /I not "%CANDIDATE%"=="python" if not exist "%CANDIDATE%" goto :eof
call %CANDIDATE% -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PYTHON_CMD=%CANDIDATE%"
goto :eof
