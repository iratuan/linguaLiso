# Verifica os pré-requisitos e os serviços locais do English Teacher Local.
# Não altera nada e não acessa a internet.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot

function Show($ok, $label, $detail = "") {
    $mark = if ($ok) { "[OK]   " } else { "[FALHA]" }
    $color = if ($ok) { "Green" } else { "Red" }
    Write-Host "$mark $label $detail" -ForegroundColor $color
}

Write-Host "`n== Pré-requisitos ==" -ForegroundColor Cyan
$py = Get-Command python -ErrorAction SilentlyContinue
Show ($null -ne $py) "Python no PATH" $(if ($py) { (& python --version 2>&1) } else { "" })
$node = Get-Command node -ErrorAction SilentlyContinue
Show ($null -ne $node) "Node.js no PATH" $(if ($node) { (& node --version) } else { "" })
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
Show ($null -ne $ollama) "Ollama no PATH"
$gpu = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($gpu) {
    Show $true "Driver NVIDIA" ((& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader) -join "; ")
} else {
    Show $false "Driver NVIDIA (opcional: a execução é possível em CPU)"
}

Write-Host "`n== Ambientes virtuais ==" -ForegroundColor Cyan
Show (Test-Path "$root\backend\.venv\Scripts\python.exe") "backend\.venv"
Show (Test-Path "$root\ai-model\.venv\Scripts\python.exe") "ai-model\.venv"
Show (Test-Path "$root\frontend\node_modules") "frontend\node_modules"

Write-Host "`n== Modelos ==" -ForegroundColor Cyan
$voice = "$root\ai-model\voices\en_US-lessac-medium.onnx"
Show (Test-Path $voice) "Voz Piper en_US-lessac-medium"
$whisper = "$root\ai-model\models\whisper"
Show ((Test-Path $whisper) -and (@(Get-ChildItem $whisper -Filter "models--*" -ErrorAction SilentlyContinue).Count -gt 0)) "Whisper small.en em cache"

Write-Host "`n== Serviços em execução ==" -ForegroundColor Cyan
function Probe($url) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}
Show (Probe "http://127.0.0.1:11434/api/tags") "Ollama (127.0.0.1:11434)"
Show (Probe "http://127.0.0.1:8001/health") "Servidor de voz (127.0.0.1:8001)"
Show (Probe "http://127.0.0.1:8000/api/health") "Backend (127.0.0.1:8000)"

Write-Host ""
Write-Host "Para corrigir: scripts\instalar.ps1 (dependências) e ai-model\scripts\setup_models.ps1 (modelos)." -ForegroundColor Gray
