# Reinicia o Ollama com paralelismo 2, para atender o English Teacher e outro app ao mesmo tempo.
#
# Use só quando nenhum outro app estiver no meio de um trabalho com o Ollama:
# o reinício interrompe as requisições em andamento.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\iniciar_ollama.ps1

$ErrorActionPreference = "Stop"

$exe = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (-not (Test-Path $exe)) { throw "Ollama não encontrado em $exe" }

Write-Host "Encerrando o Ollama atual..." -ForegroundColor Cyan
Get-Process -Name "ollama app", "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

$env:OLLAMA_NUM_PARALLEL = "2"
Write-Host "Iniciando o Ollama com OLLAMA_NUM_PARALLEL=2..." -ForegroundColor Cyan
Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 2 | Out-Null
    Write-Host "OK: Ollama no ar." -ForegroundColor Green
    $log = Join-Path $env:LOCALAPPDATA "Ollama\server.log"
    $line = Select-String -Path $log -Pattern "OLLAMA_NUM_PARALLEL:\d+" -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($line) { Write-Host ("Configuração efetiva: " + $line.Matches[0].Value) }
    exit 0
  } catch {
    Start-Sleep -Milliseconds 500
  }
}
throw "O Ollama não respondeu em 30 segundos."
