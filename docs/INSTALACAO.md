# Guia de instalação (computador novo)

O English Teacher Local é portátil: não tem instalador. A pasta do projeto é o aplicativo.

## 1. Copie a pasta

Copie a pasta do projeto para o computador (ou clone o repositório). Escolha um lugar que você possa manter, por exemplo `C:\Apps\ia_teacher`.

## 2. Rode o script

Abra o PowerShell na pasta do projeto e execute:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

O script verifica e instala, nesta ordem:

| Item | Como é tratado |
|---|---|
| Python 3.11+ | Se faltar, oferece instalar com `winget` (Python 3.12) |
| Node.js 20+ | Se faltar, oferece instalar com `winget` (Node.js LTS) |
| Ollama | Oferece instalar com `winget`. Se você recusar, use um provedor na nuvem |
| Dependências Python (backend e voz) | Instala em `backend\.venv` e `ai-model\.venv` |
| Dependências do frontend | `npm install` em `frontend\node_modules` |
| Interface | Compila em `frontend\dist` quando estiver desatualizada |
| Vozes Piper (inglês e francês) | Sempre baixadas para `ai-model\voices` |
| Whisper `small` | Sempre baixado para `ai-model\models\whisper` |
| Modelo `qwen3:8b` (Ollama) | Oferece baixar agora; também dá para baixar em Ajustes |

Opções:

- `-Verificar`: só diagnostica. Não instala nem abre o app.
- `-Sim`: responde "sim" a todas as perguntas.

Requisitos de disco: cerca de 10 GB livres para as dependências, as vozes e o modelo principal. Em **Ajustes**, a seção "Espaço ocupado" mostra quanto cada parte está usando.

## 3. Modelos de IA

Você escolhe o motor do professor em **Ajustes**:

- **Ollama (padrão):** roda no seu computador, sem custo por token. Em **Modelos locais**, o app mostra se o Ollama está instalado e quais modelos faltam, com botão para baixar.
- **Provedores na nuvem (opcional):** Claude, Groq ou GPT. Cole a chave em **Provedores na nuvem**. Para aulas mais profundas, use um modelo na nuvem. Para o dia a dia, o Ollama economiza tokens.

As chaves ficam no arquivo `backend\.env`, que não vai para o Git.

## 4. Desinstalar

Apague a pasta do projeto. Os dados do aluno ficam em `data\` dentro dela. Para desinstalar o Ollama, use o próprio Windows (Configurações > Aplicativos).

## Problemas comuns

- **"winget não encontrado":** instale o "Instalador de Aplicativos" pela Microsoft Store e rode o script de novo.
- **Script bloqueado pelo PowerShell:** use o comando com `-ExecutionPolicy Bypass`, como acima.
- **Logs:** `%APPDATA%\English Teacher Local\logs`.
