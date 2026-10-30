# English Teacher Local — Arquitetura

O projeto é dividido em três componentes independentes que se comunicam por HTTP local (`127.0.0.1`).

```
┌──────────────────────────┐      HTTP 127.0.0.1:8000       ┌────────────────────────────┐
│  frontend/               │  ───────────────────────────►  │  backend/                  │
│  React + Vite + Electron │                                │  FastAPI + SQLite          │
│  (interface desktop)     │ ◄───────────────────────────   │  (APIs, pedagogia, dados)  │
└──────────────────────────┘                                └──────┬──────────────┬──────┘
                                                                   │              │
                                                 HTTP 127.0.0.1:11434│              │HTTP 127.0.0.1:8001
                                                                   ▼              ▼
                                                    ┌──────────────────┐  ┌────────────────────────┐
                                                    │ Ollama           │  │ ai-model/speech_server │
                                                    │ Qwen3 8B / 4B    │  │ faster-whisper + Piper │
                                                    └──────────────────┘  └────────────────────────┘
```

## Componentes

| Componente | Pasta | Responsabilidade | Stack |
|---|---|---|---|
| Modelo de IA | `ai-model/` | Scripts para baixar modelos, configuração de modelos e servidor de voz (STT + TTS) | Ollama, faster-whisper, Piper, FastAPI |
| Backend | `backend/` | APIs REST, regras pedagógicas, prompts, persistência SQLite, migrações | Python, FastAPI, sqlite3, httpx |
| Frontend | `frontend/` | Interface desktop, captura de microfone, reprodução de áudio, telas | React, Vite, Tailwind CSS, Electron |

## Decisões

1. **Interface em React + Electron** substitui PySide6 do PROMPT.md. Mantém os requisitos de responsividade (a inferência fica no backend, a UI só consome HTTP).
2. **LLM via Ollama** com saída estruturada (`format` com JSON Schema). O backend ainda valida e recupera respostas inválidas, como exige o PROMPT.md: a mensagem sempre aparece, mesmo que a correção não seja interpretada.
3. **Voz fora do backend principal.** O servidor de voz roda separado para isolar carga de memória do Whisper/Piper e permitir trocar o motor sem mexer nas APIs.
4. **SQLite com migrações versionadas** (`PRAGMA user_version`). Antes de aplicar migrações sobre um banco existente, o backend copia o arquivo para `data/backups/`.
5. **Sem nuvem.** Não há chamadas a serviços externos em uso normal. Os endereços dos serviços são configuráveis, mas o padrão é loopback.
6. **Revisão espaçada** usa um esquema de caixas (Leitner) com intervalos fixos: 1, 3, 7, 14, 30 e 60 dias. A implementação está em `backend/app/services/srs.py` e é coberta por testes.

## Fluxo de um turno de voz

1. Frontend grava o microfone (`MediaRecorder`, WebM/Opus) e envia para `POST /api/speech/transcribe`.
2. Backend repassa ao servidor de voz, que transcreve com faster-whisper (modelo carregado uma vez).
3. Frontend envia o texto para `POST /api/sessions/{id}/messages` com `input_source = voice`.
4. Backend monta o prompt (sistema + modo + nível + histórico limitado), chama o Ollama e recebe JSON validado.
5. Resposta e correção são gravadas no SQLite e devolvidas.
6. Frontend exibe a resposta e, se o usuário pedir, chama `POST /api/speech/synthesize` para tocar o áudio.

## Limitações conhecidas desta versão

- Respostas não são transmitidas token a token: a saída estruturada precisa estar completa para ser validada. A interface mostra o estado "Preparando resposta".
- Avaliação de pronúncia é apenas textual (comparação de palavras), conforme o PROMPT.md.
- Estimativa de nível é sempre manual.
