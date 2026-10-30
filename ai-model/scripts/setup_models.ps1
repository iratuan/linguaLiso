# Prepara os modelos locais do English Teacher Local.
#
# Esta é a ÚNICA etapa que acessa a internet (além da instalação do Ollama e das
# dependências Python). Depois de executada, o uso diário funciona offline.
#
# Uso (a partir da pasta ai-model):
#   powershell -ExecutionPolicy Bypass -File scripts\setup_models.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\setup_models.ps1 -SkipLlm -SkipWhisper
param(
    [switch]$SkipLlm,
    [switch]$SkipWhisper,
    [switch]$SkipVoice,
    [switch]$WithFallbackLlm = $true
)

$ErrorActionPreference = "Stop"
$aiModelDir = Split-Path -Parent $PSScriptRoot
$catalog = Get-Content (Join-Path $aiModelDir "models.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$python = Join-Path $aiModelDir ".venv\Scripts\python.exe"
$voicesDir = Join-Path $aiModelDir $catalog.tts.voices_dir
$whisperDir = Join-Path $aiModelDir "models\whisper"

function Write-Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Write-Ok($text) { Write-Host "    OK: $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "    AVISO: $text" -ForegroundColor Yellow }

# 1) LLM via Ollama ---------------------------------------------------------
if (-not $SkipLlm) {
    Write-Step "LLM (Ollama)"
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollama) {
        throw "Ollama não encontrado no PATH. Instale em https://ollama.com e abra o aplicativo antes de rodar este script."
    }
    $models = @($catalog.llm.primary)
    if ($WithFallbackLlm) { $models += $catalog.llm.fallback }
    foreach ($model in $models) {
        Write-Host "    ollama pull $model"
        & ollama pull $model
        if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar $model." }
        Write-Ok "$model disponível"
    }
}

# 2) Voz Piper ----------------------------------------------------------------
if (-not $SkipVoice) {
    New-Item -ItemType Directory -Force -Path $voicesDir | Out-Null
    # Uma voz por idioma (ver ai-model/models.json, bloco tts.downloads).
    foreach ($voice in $catalog.tts.downloads.PSObject.Properties) {
        Write-Step "Voz Piper ($($voice.Name))"
        foreach ($file in $voice.Value.files) {
            $target = Join-Path $voicesDir $file
            if ((Test-Path $target) -and ((Get-Item $target).Length -gt 1KB)) {
                Write-Ok "$file já existe"
                continue
            }
            $url = "$($voice.Value.base_url)/$file"
            Write-Host "    baixando $url"
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target
            if ((Get-Item $target).Length -lt 1KB) { throw "Arquivo de voz inválido: $file" }
            Write-Ok "$file salvo em $voicesDir"
        }
    }
}

# 3) Whisper (faster-whisper) ------------------------------------------------
if (-not $SkipWhisper) {
    Write-Step "Reconhecimento de fala ($($catalog.stt.model))"
    if (-not (Test-Path $python)) {
        throw "Ambiente virtual não encontrado. Rode primeiro scripts\install.ps1 dentro de ai-model."
    }
    New-Item -ItemType Directory -Force -Path $whisperDir | Out-Null
    $code = @"
from faster_whisper import WhisperModel
WhisperModel('$($catalog.stt.model)', device='cpu', compute_type='$($catalog.stt.compute_type)', download_root=r'$whisperDir')
print('whisper ok')
"@
    & $python -c $code
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar o modelo Whisper." }
    Write-Ok "Whisper $($catalog.stt.model) em $whisperDir"
}

Write-Step "Concluído"
Write-Host "Os modelos estão prontos. Você pode desconectar a internet e usar o aplicativo."
