# Gera o instalador do English Teacher Local para Windows (executar na máquina de desenvolvimento).
#
# Etapas:
#  1. compila o frontend;
#  2. monta build\staging com o Python embutido, o backend, a voz e o script de preparação;
#  3. empacota tudo com electron-builder num Setup.exe em build\installer.
#
# O Ollama e o modelo de linguagem NÃO entram no instalador: são preparados na primeira execução.

param(
  [switch]$SkipNpm
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
$PythonVersion = "3.14.3"
$Root = Split-Path -Parent $PSScriptRoot
$Staging = Join-Path $Root "build\staging"
$Cache = Join-Path $Root "build\cache"
$Frontend = Join-Path $Root "frontend"

function Step($text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }

# 1. Frontend --------------------------------------------------------------------
Step "Compilando o frontend"
Push-Location $Frontend
try {
  if (-not $SkipNpm) { npm install }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "Falha ao compilar o frontend." }
} finally { Pop-Location }

# 2. Staging --------------------------------------------------------------------
Step "Montando o pacote (staging)"
if (Test-Path $Staging) { Remove-Item -Recurse -Force $Staging }
New-Item -ItemType Directory -Force -Path $Staging, $Cache | Out-Null

# 2a. Python embutido
$Runtime = Join-Path $Staging "runtime"
$PyZip = Join-Path $Cache "python-$PythonVersion-embed-amd64.zip"
if (-not (Test-Path $PyZip)) {
  Write-Host "Baixando o Python $PythonVersion (embeddable) do python.org..."
  Invoke-WebRequest -Uri "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip" -OutFile $PyZip -UseBasicParsing
}
Expand-Archive -Path $PyZip -DestinationPath $Runtime -Force
$major = ($PythonVersion -split '\.')[0..1] -join ''
$pth = Join-Path $Runtime "python$major._pth"
# O modo embutido ignora o diretório atual: incluímos o backend e a voz no caminho de busca.
@(
  "python$major.zip",
  ".",
  "Lib\site-packages",
  "..\backend",
  "..\ai-model",
  "import site"
) | Set-Content -Path $pth -Encoding ASCII

Write-Host "Instalando o pip e as bibliotecas (pode demorar)..."
$GetPip = Join-Path $Cache "get-pip.py"
if (-not (Test-Path $GetPip)) { Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPip -UseBasicParsing }
& (Join-Path $Runtime "python.exe") $GetPip --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o pip." }
$py = Join-Path $Runtime "python.exe"
& $py -m pip install --no-warn-script-location -r (Join-Path $Root "backend\requirements.txt") -r (Join-Path $Root "ai-model\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as bibliotecas." }

# 2b. Backend (sem ambiente virtual, dados, testes nem caches)
Write-Host "Copiando o backend..."
$Backend = Join-Path $Staging "backend"
robocopy (Join-Path $Root "backend") $Backend /E /NFL /NDL /NJH /NJS /NP `
  /XD .venv data tests __pycache__ .pytest_cache backups | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Falha ao copiar o backend (robocopy $LASTEXITCODE)." }

# 2c. Voz: modelos de voz (en, fr) e o reconhecimento de voz 'small' (multilíngue). O 'small.en' não é usado.
Write-Host "Copiando a voz e o reconhecimento de voz..."
$AiModel = Join-Path $Staging "ai-model"
robocopy (Join-Path $Root "ai-model") $AiModel /E /NFL /NDL /NJH /NJS /NP `
  /XD .venv tests scripts __pycache__ models /XF *.pyc | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Falha ao copiar a voz (robocopy $LASTEXITCODE)." }
Copy-Item (Join-Path $Root "ai-model\models.json") $AiModel
$WhisperSrc = Join-Path $Root "ai-model\models\whisper"
$WhisperDst = Join-Path $AiModel "models\whisper"
New-Item -ItemType Directory -Force -Path $WhisperDst | Out-Null
Get-ChildItem $WhisperSrc -Directory | Where-Object { $_.Name -like "*faster-whisper-small" } |
  ForEach-Object { Copy-Item $_.FullName $WhisperDst -Recurse -Force }
if (-not (Test-Path (Join-Path $WhisperDst "models--Systran--faster-whisper-small"))) {
  throw "Modelo de reconhecimento 'small' não encontrado em ai-model\models\whisper. Execute scripts\setup_models.ps1."
}

# 2d. Script de preparação da primeira execução
New-Item -ItemType Directory -Force -Path (Join-Path $Staging "scripts") | Out-Null
Copy-Item (Join-Path $PSScriptRoot "preparar.ps1") (Join-Path $Staging "scripts\preparar.ps1") -Force

# 3. Instalador --------------------------------------------------------------------
Step "Gerando o instalador"
Push-Location $Frontend
try {
  npx electron-builder --win --x64
  if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o instalador." }
} finally { Pop-Location }

$Out = Join-Path $Root "build\installer"
Write-Host ""
Write-Host "Pronto. Instalador em: $Out" -ForegroundColor Green
Get-ChildItem $Out -Filter "*.exe" | ForEach-Object { "{0}  ({1:N0} MB)" -f $_.FullName, ($_.Length / 1MB) }
