# Instala as dependências dos três componentes (backend, ai-model e frontend).
# Pré-requisitos: Python 3.11+, Node.js 20+. O Ollama é instalado à parte (https://ollama.com).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "==> backend" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

Write-Host "==> ai-model" -ForegroundColor Cyan
Set-Location "$root\ai-model"
powershell -ExecutionPolicy Bypass -File "scripts\install.ps1"

Write-Host "==> frontend" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install
if ($LASTEXITCODE -ne 0) { throw "Falha no npm install." }

Set-Location $root
Write-Host "`nDependências instaladas. Próximos passos:" -ForegroundColor Green
Write-Host "  1. ai-model\scripts\setup_models.ps1   (baixa Qwen3, voz Piper e Whisper)"
Write-Host "  2. scripts\diagnostico.ps1             (verifica tudo)"
Write-Host "  3. scripts\iniciar.ps1                 (abre o aplicativo)"
