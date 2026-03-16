$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$batPath = Join-Path $repoRoot "cmdbox.bat"

if (-not (Test-Path $batPath)) {
    throw "Could not find cmdbox.bat at: $batPath"
}

$extKey = "HKCU:\Software\Classes\.cmdbox"
$typeKey = "HKCU:\Software\Classes\CmdBox.Project"
$commandKey = "HKCU:\Software\Classes\CmdBox.Project\shell\open\command"

New-Item -Path $extKey -Force | Out-Null
Set-ItemProperty -Path $extKey -Name "(default)" -Value "CmdBox.Project"

New-Item -Path $typeKey -Force | Out-Null
Set-ItemProperty -Path $typeKey -Name "(default)" -Value "CmdBox Project File"

New-Item -Path $commandKey -Force | Out-Null
$commandValue = "cmd.exe /c \"\"$batPath\" \"%1\"\""
Set-ItemProperty -Path $commandKey -Name "(default)" -Value $commandValue

Write-Host "Registered .cmdbox file association for current user."
Write-Host "You may need to restart Explorer or sign out/in to refresh file icons and associations."
