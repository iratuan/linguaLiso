# Preparação da primeira execução do English Teacher Local (instalado).

# Instala o Ollama (se faltar), escolhe o modelo de linguagem pela memória do PC e baixa o modelo.

# Os modelos de voz e de reconhecimento já vêm dentro do instalador.

param(

  [Parameter(Mandatory = $true)][string]$DataDir

)



[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

$OllamaUrl = "https://ollama.com/download/OllamaSetup.exe"

$OllamaApi = "http://127.0.0.1:11434/api/tags"



function Say($text) { Write-Host $text }



function Find-Ollama {

  $candidates = @(

    (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),

    (Join-Path $env:ProgramFiles "Ollama\ollama.exe")

  )

  foreach ($c in $candidates) { if (Test-Path $c) { return $c } }

  $cmd = Get-Command ollama -ErrorAction SilentlyContinue

  if ($cmd) { return $cmd.Source }

  return $null

}



function Test-OllamaRunning {

  try { Invoke-RestMethod -Uri $OllamaApi -TimeoutSec 3 | Out-Null; return $true } catch { return $false }

}



Say ""

Say "=== English Teacher Local: preparação ==="

Say ""

Say "Esta etapa vai:"

Say "  1. verificar se o Ollama (motor do professor) está instalado; se não estiver, baixá-lo do site oficial;"

Say "  2. escolher o modelo de linguagem de acordo com a memória deste computador;"

Say "  3. baixar esse modelo (de 2 a 5 GB). É preciso internet só nesta etapa."

Say ""

$answer = Read-Host "Continuar? (S/N)"

if ($answer -notmatch '^[sSyY]') {

  Say "Preparação cancelada. Abra o app de novo quando quiser concluir."

  exit 1

}



# 1. Perfil da máquina ---------------------------------------------------------

$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$drive = (Get-Item $DataDir).PSDrive.Name

$freeGb = [math]::Round((Get-PSDrive $drive).Free / 1GB, 1)

$model = if ($ramGb -ge 12) { "qwen3:8b" } else { "qwen3:4b" }

Say ""

Say "Memória: $ramGb GB  |  Espaço livre no disco $drive`: $freeGb GB"

Say "Modelo escolhido para esta máquina: $model"

if ($freeGb -lt 8) { Say "Atenção: pouco espaço livre. O modelo pode não caber." }



# 2. Ollama -------------------------------------------------------------------

$ollama = Find-Ollama

if (-not $ollama) {

  Say ""

  Say "Baixando o Ollama do site oficial..."

  $setup = Join-Path $env:TEMP "OllamaSetup.exe"

  Invoke-WebRequest -Uri $OllamaUrl -OutFile $setup -UseBasicParsing

  $sig = Get-AuthenticodeSignature $setup

  if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Ollama") {

    throw "A assinatura do instalador do Ollama não é válida. Instalação cancelada por segurança."

  }

  Say "Instalando o Ollama (pode levar um minuto)..."

  $p = Start-Process -FilePath $setup -ArgumentList "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES" -Wait -PassThru

  if ($p.ExitCode -ne 0) { throw "O instalador do Ollama terminou com código $($p.ExitCode)." }

  $ollama = Find-Ollama

  if (-not $ollama) { throw "O Ollama foi instalado, mas não foi encontrado." }

}

Say "Ollama encontrado: $ollama"



# 3. Servidor do Ollama -----------------------------------------------------------

if (-not (Test-OllamaRunning)) {

  Say "Iniciando o Ollama..."

  Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden

  for ($i = 0; $i -lt 60 -and -not (Test-OllamaRunning); $i++) { Start-Sleep -Seconds 1 }

  if (-not (Test-OllamaRunning)) { throw "O Ollama não respondeu em 60 segundos." }

}



# 4. Modelo de linguagem ----------------------------------------------------------

Say ""

Say "Baixando o modelo $model (pode levar vários minutos)..."

& $ollama pull $model

if ($LASTEXITCODE -ne 0) { throw "Não foi possível baixar o modelo $model." }



# 5. Registro da instalação -----------------------------------------------------------

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$profile = [ordered]@{ llm_model = $model; ram_gb = $ramGb; prepared_at = (Get-Date).ToString("s") }

$profile | ConvertTo-Json | Set-Content -Path (Join-Path $DataDir "perfil-maquina.json") -Encoding UTF8

$done = [ordered]@{ ok = $true; prepared_at = (Get-Date).ToString("s") }

$done | ConvertTo-Json | Set-Content -Path (Join-Path $DataDir "instalacao-concluida.json") -Encoding UTF8



Say ""

Say "Preparação concluída. O professor já pode ser usado."

Start-Sleep -Seconds 3

exit 0

