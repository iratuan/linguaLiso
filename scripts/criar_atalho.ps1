# Cria um atalho "English Teacher" na área de trabalho que roda scripts\iniciar.ps1.
# Uso: powershell -ExecutionPolicy Bypass -File scripts\criar_atalho.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root "scripts\iniciar.ps1"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "English Teacher.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = (Join-Path $root "frontend\electron\assets\icon.ico") + ",0"
$shortcut.Description = "Abre o English Teacher Local (verifica o Ollama e o modelo antes)"
$shortcut.Save()

Write-Host "Atalho criado em: $shortcutPath" -ForegroundColor Green
