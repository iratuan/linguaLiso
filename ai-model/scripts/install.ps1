# Cria o ambiente virtual do componente ai-model e instala as dependências.
# Uso (a partir da pasta ai-model): powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = "Stop"
$aiModelDir = Split-Path -Parent $PSScriptRoot
Set-Location $aiModelDir

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências do ai-model." }
Write-Host "ai-model instalado. Próximo passo: scripts\setup_models.ps1" -ForegroundColor Green
