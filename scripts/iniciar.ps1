# Inicia o English Teacher Local do zero.
#
# 1. Garante que o Ollama está instalado e rodando (sobe o serviço se estiver parado).
# 2. Garante que o modelo de conversa está baixado (baixa se faltar).
# 3. Confere os arquivos de voz.
# 4. Abre o aplicativo (Vite + Electron, que sobe backend e servidor de voz).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1 -SomenteVerificar
param(
    [switch]$SomenteVerificar
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$root = Split-Path -Parent $PSScriptRoot
$catalog = Get-Content (Join-Path $root "ai-model\models.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$model = $catalog.llm.primary
$ollamaUrl = "http://127.0.0.1:11434"

function Write-Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Write-Ok($text) { Write-Host "    OK: $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "    AVISO: $text" -ForegroundColor Yellow }

function Test-Ollama {
    try {
        Invoke-RestMethod -Uri "$ollamaUrl/api/version" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-Vite {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173/" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Find-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $local = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $local) { return $local }
    return $null
}

function Get-InstalledModels {
    $tags = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 10
    return @($tags.models | ForEach-Object { $_.name })
}

# ----- 1) Ollama -------------------------------------------------------------

Write-Step "Ollama"
$ollama = Find-OllamaExe
if (-not $ollama) {
    throw "Ollama não encontrado. Instale em https://ollama.com e rode este script de novo."
}

if (Test-Ollama) {
    Write-Ok "já está rodando"
} else {
    Write-Host "    Iniciando o serviço do Ollama..."
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    $ready = $false
    for ($i = 0; $i -lt 30 -and -not $ready; $i++) {
        Start-Sleep -Seconds 1
        $ready = Test-Ollama
    }
    if (-not $ready) { throw "O Ollama não respondeu em 30 segundos. Abra o aplicativo Ollama manualmente e tente de novo." }
    Write-Ok "serviço iniciado"
}

# ----- 2) Modelo -------------------------------------------------------------

Write-Step "Modelo de conversa ($model)"
$installed = Get-InstalledModels
if ($installed -contains $model -or $installed -contains "$($model):latest") {
    Write-Ok "instalado"
} else {
    Write-Host "    Não encontrado. Baixando agora (é um download grande, pode levar vários minutos)..."
    & $ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar o modelo $model. Verifique sua conexão e tente de novo." }
    Write-Ok "modelo baixado"
}

# ----- 3) Voz ----------------------------------------------------------------

Write-Step "Vozes do professor"
$missingVoices = @()
foreach ($voice in $catalog.tts.downloads.PSObject.Properties) {
    if (-not (Test-Path (Join-Path $root "ai-model\voices\$($voice.Name).onnx"))) { $missingVoices += $voice.Name }
}
if ($missingVoices.Count -eq 0) {
    Write-Ok "vozes encontradas"
} else {
    Write-Warn "voz não encontrada: $($missingVoices -join ', '). Rode ai-model\scripts\setup_models.ps1 -SkipLlm para baixá-las."
}

# ----- 4) Aplicativo ---------------------------------------------------------

if ($SomenteVerificar) {
    Write-Step "Verificação concluída"
    Write-Host "Para abrir o aplicativo, rode este script sem o parâmetro -SomenteVerificar."
    return
}

Write-Step "Abrindo o aplicativo"
Set-Location (Join-Path $root "frontend")
if (Test-Vite) {
    # O servidor da interface já está de pé (outra janela ou execução anterior): abre só o Electron.
    Write-Ok "servidor da interface já estava rodando"
    npx electron .
} else {
    npm run electron:dev
}
