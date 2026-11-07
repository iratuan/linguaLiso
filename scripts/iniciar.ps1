# English Teacher Local: script único (versão portátil, sem instalador).
#
# Copie a pasta do projeto (ou clone o repositório) e rode este script.
# Ele verifica o que falta, instala o que for preciso e abre o aplicativo.
# Ao fechar a janela, encerra os processos que iniciou.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1            verifica, instala o que falta e abre
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1 -Verificar  só diagnostica; não instala nem abre
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1 -Sim        responde "sim" a todas as perguntas
#
# O que o script instala (com winget, se faltar e você confirmar):
#   Python 3.11+, Node.js 20+ e Ollama (opcional: sem ele, use um provedor na nuvem em Ajustes).
# O que ele baixa sempre: dependências Python e do frontend, vozes Piper (en/fr) e o Whisper.
param(
    [switch]$Sim,
    [switch]$Verificar
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$aiDir = Join-Path $root "ai-model"
$frontendDir = Join-Path $root "frontend"
$ollamaUrl = "http://127.0.0.1:11434"
$catalog = Get-Content (Join-Path $aiDir "models.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$modeloPrincipal = $catalog.llm.primary
$script:ollamaIniciadoAqui = $null
$script:avisos = @()

function Write-Step($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Write-Ok($t) { Write-Host "    OK: $t" -ForegroundColor Green }
function Write-Aviso($t) { Write-Host "    AVISO: $t" -ForegroundColor Yellow; $script:avisos += $t }
function Stop-Script($t) { Write-Host "    FALHA: $t" -ForegroundColor Red; throw $t }

function Ask($pergunta, [bool]$padrao = $true) {
    if ($Sim) { return $true }
    $sufixo = if ($padrao) { "[S/n]" } else { "[s/N]" }
    $resp = Read-Host "    $pergunta $sufixo"
    if ([string]::IsNullOrWhiteSpace($resp)) { return $padrao }
    return $resp.Trim().ToLower().StartsWith("s")
}

function Update-Path {
    # O winget não atualiza o PATH desta janela: relê o PATH do sistema e do usuário.
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-WithWinget($id, $nome) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Stop-Script "winget não encontrado. Ele vem com o Windows 10/11 (ou instale o 'Instalador de Aplicativos' pela Microsoft Store). Depois rode o script de novo."
    }
    Write-Host "    winget install $nome (pode pedir permissão de administrador)..."
    & winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements | Out-Null
    Update-Path
}

function Test-Http($url) {
    try { Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}

# ----- Python ----------------------------------------------------------------

function Find-Python {
    foreach ($tentativa in @(@("py", "-3"), @("python"))) {
        if (-not (Get-Command $tentativa[0] -ErrorAction SilentlyContinue)) { continue }
        $extra = @($tentativa | Select-Object -Skip 1)
        $saida = & $tentativa[0] @extra -c "import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $saida) { return @($saida)[0] }
    }
    return $null
}

# ----- Node.js ---------------------------------------------------------------

function Get-NodeMajor {
    $v = & node --version 2>$null
    if ($LASTEXITCODE -eq 0 -and "$v" -match "v(\d+)") { return [int]$matches[1] }
    return 0
}

# ----- Ollama ----------------------------------------------------------------

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $local = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
    if (Test-Path $local) { return $local }
    return $null
}

function Get-OllamaModels {
    $tags = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 5
    return @($tags.models | ForEach-Object { $_.name })
}

function Start-OllamaServe($exe) {
    # Mesmo ajuste de paralelismo do aplicativo (duas requisições ao mesmo tempo).
    $env:OLLAMA_NUM_PARALLEL = "2"
    $script:ollamaIniciadoAqui = Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 30; $i++) {
        if (Test-Http "$ollamaUrl/api/version") { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

# ----- Ambientes Python e frontend -------------------------------------------

function Sync-Venv($dir, $nome, $pyBase) {
    $py = Join-Path $dir ".venv\Scripts\python.exe"
    $req = Join-Path $dir "requirements.txt"
    $stamp = Join-Path $dir ".venv\requisitos.sha256"
    $hash = (Get-FileHash $req -Algorithm SHA256).Hash
    $emDia = (Test-Path $py) -and (Test-Path $stamp) -and ((Get-Content $stamp -Raw).Trim() -eq $hash)
    if ($emDia) { Write-Ok "${nome}: dependências em dia"; return }
    if ($Verificar) { Write-Aviso "${nome}: dependências faltando ou desatualizadas (rode sem -Verificar)"; return }

    Write-Host "    instalando dependências de $nome (pode demorar)..."
    if (-not (Test-Path $py)) { & $pyBase -m venv (Join-Path $dir ".venv"); if ($LASTEXITCODE -ne 0) { Stop-Script "não consegui criar o ambiente de $nome." } }
    & $py -m pip install -q -r $req
    if ($LASTEXITCODE -ne 0) { Stop-Script "falha ao instalar as dependências de $nome. Veja a mensagem acima." }
    Set-Content -Path $stamp -Value $hash -Encoding ASCII
    Write-Ok "$nome instalado"
}

function Sync-Frontend {
    # Só instala quando falta o Electron. Reinstalar por rotina remove arquivos e pode esbarrar em permissões.
    $electron = Join-Path $frontendDir "node_modules\electron\dist\electron.exe"
    if (Test-Path $electron) {
        Write-Ok "frontend: dependências instaladas"
    } elseif ($Verificar) {
        Write-Aviso "frontend: dependências faltando (rode sem -Verificar)"
    } else {
        Write-Host "    instalando dependências do frontend (npm install, pode demorar)..."
        Push-Location $frontendDir
        try { & npm install; if ($LASTEXITCODE -ne 0) { Stop-Script "falha no npm install." } } finally { Pop-Location }
        if (-not (Test-Path $electron)) { Stop-Script "o Electron não foi instalado. Veja o erro do npm acima." }
        Write-Ok "dependências do frontend instaladas"
    }

    # A interface é compilada para dist/ (o app abre o build, sem servidor Vite).
    $indexHtml = Join-Path $frontendDir "dist\index.html"
    $ultimaFonte = (Get-ChildItem -Path (Join-Path $frontendDir "src"), (Join-Path $frontendDir "index.html") -Recurse -File |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    $precisaCompilar = (-not (Test-Path $indexHtml)) -or ((Get-Item $indexHtml).LastWriteTime -lt $ultimaFonte)
    if ($precisaCompilar -and -not $Verificar) {
        Write-Host "    compilando a interface (npm run build)..."
        Push-Location $frontendDir
        try { & npm run build; if ($LASTEXITCODE -ne 0) { Stop-Script "falha ao compilar a interface." } } finally { Pop-Location }
        Write-Ok "interface compilada"
    } elseif ($precisaCompilar) { Write-Aviso "interface não compilada (rode sem -Verificar)" }
    else { Write-Ok "interface compilada" }
}

# ----- Vozes e Whisper (sempre baixados) --------------------------------------

function Sync-Voices {
    $voicesDir = Join-Path $aiDir $catalog.tts.voices_dir
    New-Item -ItemType Directory -Force -Path $voicesDir | Out-Null
    foreach ($voz in $catalog.tts.downloads.PSObject.Properties) {
        foreach ($arquivo in $voz.Value.files) {
            $destino = Join-Path $voicesDir $arquivo
            if ((Test-Path $destino) -and ((Get-Item $destino).Length -gt 1KB)) { continue }
            if ($Verificar) { Write-Aviso "voz não encontrada: $arquivo"; continue }
            Write-Host "    baixando voz $arquivo..."
            Invoke-WebRequest -UseBasicParsing -Uri "$($voz.Value.base_url)/$arquivo" -OutFile $destino
            if ((Get-Item $destino).Length -lt 1KB) { Stop-Script "arquivo de voz inválido: $arquivo" }
        }
    }
    Write-Ok "vozes do professor (en/fr) prontas"
}

function Sync-Whisper($aiPy) {
    $whisperDir = Join-Path $aiDir "models\whisper"
    $pronto = (Test-Path $whisperDir) -and (@(Get-ChildItem $whisperDir -Filter "models--*" -ErrorAction SilentlyContinue).Count -gt 0)
    if ($pronto) { Write-Ok "reconhecimento de fala ($($catalog.stt.model)) pronto"; return }
    if ($Verificar -or -not $aiPy) { Write-Aviso "reconhecimento de fala não baixado (rode sem -Verificar)"; return }
    New-Item -ItemType Directory -Force -Path $whisperDir | Out-Null
    Write-Host "    baixando reconhecimento de fala ($($catalog.stt.model))..."
    & $aiPy -c "import sys; from faster_whisper import WhisperModel; WhisperModel(sys.argv[1], device='cpu', compute_type=sys.argv[2], download_root=sys.argv[3]); print('ok')" $catalog.stt.model $catalog.stt.compute_type $whisperDir
    if ($LASTEXITCODE -ne 0) { Stop-Script "falha ao baixar o reconhecimento de fala." }
    Write-Ok "reconhecimento de fala ($($catalog.stt.model)) pronto"
}

# ----- Modelo do Ollama -------------------------------------------------------

function Sync-OllamaModel($ollama) {
    if (-not $ollama) {
        Write-Aviso "Ollama não instalado. Sem ele, use um provedor na nuvem em Ajustes > Provedores (Groq, Claude, GPT)."
        return
    }
    if (-not (Test-Http "$ollamaUrl/api/version")) {
        if ($Verificar) { Write-Aviso "Ollama instalado, mas parado (o app o inicia ao abrir)"; return }
        Write-Host "    iniciando o Ollama para verificar os modelos..."
        if (-not (Start-OllamaServe $ollama)) { Write-Aviso "o Ollama não respondeu. Abra-o manualmente ou use um provedor na nuvem."; return }
    }
    $instalados = Get-OllamaModels
    if ($instalados -contains $modeloPrincipal -or $instalados -contains "$($modeloPrincipal):latest") {
        Write-Ok "modelo $modeloPrincipal instalado"
        return
    }
    if ($Verificar) { Write-Aviso "modelo $modeloPrincipal não instalado (baixe em Ajustes ou rode sem -Verificar)"; return }
    if (Ask "Baixar o modelo $modeloPrincipal agora? (é grande, vários GB)") {
        & $ollama pull $modeloPrincipal
        if ($LASTEXITCODE -ne 0) { Write-Aviso "falha ao baixar $modeloPrincipal. Tente de novo em Ajustes." }
        else { Write-Ok "modelo $modeloPrincipal baixado" }
    } else {
        Write-Aviso "modelo $modeloPrincipal não baixado. Baixe em Ajustes quando quiser."
    }
}

function Stop-Leftovers {
    # O Electron encerra o backend e a voz ao fechar. Aqui só se limpa o que sobrou nas portas do projeto.
    foreach ($porta in 8000, 8001) {
        foreach ($c in @(Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue)) {
            $p = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
            if ($p -and $p.Path -and $p.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                Write-Ok "encerrado processo que sobrou na porta $porta"
            }
        }
    }
    if ($script:ollamaIniciadoAqui -and -not $script:ollamaIniciadoAqui.HasExited) {
        Stop-Process -Id $script:ollamaIniciadoAqui.Id -Force -ErrorAction SilentlyContinue
        Write-Ok "Ollama iniciado por este script foi encerrado"
    }
}

# =============================================================================
#  Fluxo principal
# =============================================================================

Write-Host "English Teacher Local" -ForegroundColor Magenta
if ($Verificar) { Write-Host "(modo verificação: nada será instalado nem aberto)" -ForegroundColor Gray }

Write-Step "Pré-requisitos"
$pyBase = Find-Python
if (-not $pyBase -and -not $Verificar) {
    Write-Aviso "Python 3.11+ não encontrado."
    if (Ask "Instalar o Python 3.12 com winget?") { Install-WithWinget "Python.Python.3.12" "Python 3.12"; $pyBase = Find-Python }
    if (-not $pyBase) { Stop-Script "Python 3.11+ indisponível. Instale em python.org e rode o script de novo." }
}
if ($pyBase) { Write-Ok "Python: $pyBase" } else { Write-Aviso "Python 3.11+ não encontrado" }

$nodeMajor = Get-NodeMajor
if ($nodeMajor -lt 20 -and -not $Verificar) {
    Write-Aviso "Node.js 20+ não encontrado (versão atual: $nodeMajor)."
    if (Ask "Instalar o Node.js LTS com winget?") { Install-WithWinget "OpenJS.NodeJS.LTS" "Node.js LTS"; $nodeMajor = Get-NodeMajor }
    if ($nodeMajor -lt 20) { Stop-Script "Node.js 20+ indisponível. Instale em nodejs.org e rode o script de novo." }
}
if ($nodeMajor -ge 20) { Write-Ok "Node.js v$nodeMajor" } else { Write-Aviso "Node.js 20+ não encontrado" }

$ollama = Find-Ollama
if (-not $ollama -and -not $Verificar) {
    Write-Aviso "Ollama não encontrado (roda o modelo no seu computador, de graça)."
    if (Ask "Instalar o Ollama com winget? (não: você pode usar um provedor na nuvem)") {
        Install-WithWinget "Ollama.Ollama" "Ollama"
        $ollama = Find-Ollama
    }
}
if ($ollama) { Write-Ok "Ollama: $ollama" }

Write-Step "Dependências Python"
if ($pyBase) {
    Sync-Venv $backendDir "backend" $pyBase
    Sync-Venv $aiDir "ai-model (voz)" $pyBase
} else { Write-Aviso "sem Python, as dependências do backend e da voz não foram verificadas" }

Write-Step "Interface (frontend)"
if ($nodeMajor -ge 20 -or $Verificar) { Sync-Frontend } else { Write-Aviso "sem Node.js, a interface não foi verificada" }

Write-Step "Vozes e reconhecimento de fala"
Sync-Voices
$aiPy = Join-Path $aiDir ".venv\Scripts\python.exe"
Sync-Whisper $(if (Test-Path $aiPy) { $aiPy } else { $null })

Write-Step "Modelo de conversa (Ollama)"
Sync-OllamaModel $ollama

Write-Step "Resumo"
if ($script:avisos.Count -eq 0) { Write-Ok "tudo pronto" }
else { Write-Host "    $($script:avisos.Count) ponto(s) de atenção (veja acima). O app abre mesmo assim e guia você em Ajustes." -ForegroundColor Yellow }

if ($Verificar) { return }

Write-Step "Abrindo o English Teacher Local"
Write-Host "    feche a janela do aplicativo para encerrar tudo."
$electron = Join-Path $frontendDir "node_modules\electron\dist\electron.exe"
$env:ETL_USE_DIST = "1"
try {
    # electron.exe é aplicativo gráfico: o "&" do PowerShell NÃO espera por ele. Por isso usamos Start-Process -Wait.
    # O processo principal do Electron sobe o backend e a voz, e os encerra ao fechar a janela.
    $app = Start-Process -FilePath $electron -ArgumentList "`"$frontendDir`"" -WorkingDirectory $frontendDir -PassThru
    $app.WaitForExit()
} finally {
    Stop-Leftovers
    Write-Host "`nAté a próxima aula!" -ForegroundColor Magenta
}
