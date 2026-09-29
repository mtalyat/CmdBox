@echo off
setlocal

set "REPO_ROOT=%~dp0.."

if exist "%REPO_ROOT%\build" (
	echo Removing build
	rmdir /s /q "%REPO_ROOT%\build"
)

if exist "%REPO_ROOT%\dist" (
	echo Removing dist
	rmdir /s /q "%REPO_ROOT%\dist"
)

echo Done.
