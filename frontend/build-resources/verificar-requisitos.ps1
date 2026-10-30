param(
  # Usado pelo instalador em modo silencioso: sem caixas de diálogo, só o código de saída.
  [switch]$Silencioso,
  # Valores simulados, só para testes (-1 = medir de verdade).
  [double]$RamSimulada = -1,
  [double]$DiscoSimulado = -1
)

# Requisitos do English Teacher Local, verificados antes de copiar os arquivos.
# Saída: 0 = pode instalar (ou o usuário aceitou os avisos); 1 = instalação cancelada.

Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()

$titulo = "English Teacher Local"
$bloqueios = @()
$avisos = @()

# Windows e arquitetura -------------------------------------------------------
$versao = [Environment]::OSVersion.Version
if (-not [Environment]::Is64BitOperatingSystem) {
  $bloqueios += "O Windows deste computador é de 32 bits. O English Teacher precisa de Windows de 64 bits."
}
if ($versao.Major -lt 10) {
  $bloqueios += "O English Teacher precisa do Windows 10 ou 11."
}

# Memória RAM -----------------------------------------------------------------
if ($RamSimulada -ge 0) {
  $ramGb = $RamSimulada
} else {
  $ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
}
if ($ramGb -lt 4) {
  $bloqueios += "Memória RAM: $ramGb GB. O mínimo é 4 GB."
} elseif ($ramGb -lt 8) {
  $avisos += "Memória RAM: $ramGb GB. Recomendamos 8 GB ou mais; as respostas do professor podem demorar."
}

# Espaço livre em disco (no disco onde ficam os dados do aplicativo) -----------
$pastaDados = $env:APPDATA
$unidade = [System.IO.Path]::GetPathRoot($pastaDados)
if ($DiscoSimulado -ge 0) {
  $livreGb = $DiscoSimulado
} else {
  $info = New-Object System.IO.DriveInfo($unidade)
  $livreGb = [math]::Round($info.AvailableFreeSpace / 1GB, 1)
}
if ($livreGb -lt 6) {
  $bloqueios += "Espaço livre em $unidade $livreGb GB. O mínimo é 6 GB."
} elseif ($livreGb -lt 10) {
  $avisos += "Espaço livre em $unidade $livreGb GB. Recomendamos 10 GB: o modelo de linguagem ocupa de 2 a 5 GB."
}

# Internet (só a primeira abertura precisa dela) --------------------------------
$temInternet = $false
try {
  $req = [System.Net.WebRequest]::Create("https://ollama.com")
  $req.Timeout = 5000
  $resp = $req.GetResponse()
  $resp.Close()
  $temInternet = $true
} catch {
  # Qualquer resposta do servidor, mesmo de erro, mostra que a rede funciona.
  if ($_.Exception.Response) { $temInternet = $true }
}
if (-not $temInternet) {
  $avisos += "Sem acesso à internet. A primeira abertura precisa dela para instalar o Ollama e baixar o modelo."
}

# Decisão ---------------------------------------------------------------------
if ($bloqueios.Count -gt 0) {
  $texto = "Este computador não atende aos requisitos mínimos:`n`n- " + ($bloqueios -join "`n- ") + "`n`nA instalação será cancelada."
  if (-not $Silencioso) {
    [System.Windows.Forms.MessageBox]::Show($texto, $titulo, "OK", "Error") | Out-Null
  }
  exit 1
}

if ($avisos.Count -gt 0) {
  if ($Silencioso) { exit 0 }
  $texto = "Atenção:`n`n- " + ($avisos -join "`n- ") + "`n`nDeseja continuar a instalação mesmo assim?"
  $resposta = [System.Windows.Forms.MessageBox]::Show($texto, $titulo, "YesNo", "Warning")
  if ($resposta -eq [System.Windows.Forms.DialogResult]::Yes) { exit 0 }
  exit 1
}

exit 0
