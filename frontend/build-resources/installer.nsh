; Verificação de requisitos antes de copiar os arquivos (o electron-builder chama customInit em .onInit).
; A lógica e as mensagens ficam em verificar-requisitos.ps1, que mostra as caixas de diálogo com acentos corretos.

!macro customInit
  InitPluginsDir
  File "/oname=$PLUGINSDIR\verificar-requisitos.ps1" "${BUILD_RESOURCES_DIR}\verificar-requisitos.ps1"

  StrCpy $0 ""
  IfSilent 0 +2
    StrCpy $0 "-Silencioso"

  nsExec::ExecToStack 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$PLUGINSDIR\verificar-requisitos.ps1" $0'
  Pop $0 ; código de saída: 0 = pode instalar, 1 = cancelar
  Pop $1 ; saída (não usada)

  ${If} $0 != 0
    Abort
  ${EndIf}
!macroend
