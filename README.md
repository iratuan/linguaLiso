# English Teacher Local 🎓🇬🇧🇫🇷

Oi! Este é um **professor particular de inglês e francês** que mora no seu computador. Você conversa por texto ou por voz, ele corrige seus erros, explica em português quando você pede, monta aulas, treina vocabulário com revisão espaçada e ainda imprime um material de apoio com a sua própria conversa.

Nada de assinatura, nada de nuvem: **a IA roda localmente** (Ollama + Qwen3) e a voz também (Whisper e Piper). Depois que os modelos estão baixados, o uso do dia a dia funciona até sem internet. 📴

> Este é um projeto pessoal que cresce a cada conversa. Se algo estiver estranho, abra uma issue e a gente conversa. 😉

---

## ✨ O que ele faz

- 💬 **Conversa livre** por texto ou voz, com correção de erros na hora e explicação em português quando você pedir.
- 🎤 **Voz nos dois sentidos**: você fala (Whisper), ele responde falando (Piper). Dá para escolher **Só texto** se preferir.
- 📚 **Trilha de estudo do A1 ao C1**, com lições sequenciais e seis tipos de exercício. Tradução e resposta aberta são avaliadas pelo professor (IA); os outros quatro são corrigidos na hora, localmente.
- 🗣️ **Trilha de conversa**: lições pensadas para treinar situações do dia a dia, em paralelo à trilha principal.
- 🧠 **Vocabulário com revisão espaçada** (caixas Leitner: 1, 3, 7, 14, 30 e 60 dias).
- 📈 **Progresso e análise de nível** da conversa.
- 🖨️ **Material de apoio para imprimir**, feito a partir da conversa: explicação, lacunas, pontos de correção, exercícios de fixação e um rodapé com as palavras para revisar.
- 💾 **Seus dados ficam com você**: banco SQLite local, backups automáticos antes de migrações e exportação em JSON.

---

## 🧭 Como as peças se encaixam

O projeto tem três pastas independentes (o desenho completo está em [docs/ARQUITETURA.md](docs/ARQUITETURA.md)):

| Pasta | O que faz | Tecnologia |
|---|---|---|
| `ai-model/` | Servidor de voz (reconhecimento e síntese) e scripts para baixar modelos | faster-whisper, Piper, FastAPI |
| `backend/` | APIs, regras pedagógicas, prompts, currículo e banco de dados | FastAPI, SQLite com migrações |
| `frontend/` | A janela do aplicativo | React, Vite, Tailwind CSS, Electron |

A IA de conversa fala com o backend pelo Ollama em `127.0.0.1:11434`. O [PROMPT.md](PROMPT.md) é o documento de requisitos original. A interface ficou em React + Electron no lugar do PySide6 que ele sugeria.

---

## 🧪 Provas: o que foi testado

Nada de "funciona na minha máquina" sem prova. Estes são os números da última rodada, com a saída real dos comandos:

| Parte | Comando | Resultado |
|---|---|---|
| Backend (API, banco, migrações, correção, material de apoio, SRS) | `pytest -q` em `backend/` | ✅ **176 passed** |
| Servidor de voz (validação e caminhos de falha, sem modelos) | `pytest -q` em `ai-model/` | ✅ **8 passed** |
| Frontend (utilitários, gráficos, tela de lição) | `npm test` em `frontend/` | ✅ **25 passed** em 4 arquivos |
| Tipos do frontend | `npm run typecheck` | ✅ sem erros |

Saída real do backend:

```
176 passed, 1 warning in 24.23s
```

Saída real do frontend:

```
 Test Files  4 passed (4)
      Tests  25 passed (25)
```

### 📊 O currículo, contado nos arquivos

Os números abaixo saíram da leitura dos JSON em `backend/app/curriculum/`, não de estimativa:

| Idioma | Trilha principal | Trilha de conversa | Total de lições | Total de exercícios |
|---|---|---|---|---|
| 🇬🇧 Inglês | 60 lições · 240 exercícios | 12 lições · 48 exercícios | 72 | 288 |
| 🇫🇷 Francês | 60 lições · 240 exercícios | 12 lições · 48 exercícios | 72 | 288 |

Cada nível (A1 a C1) tem 4 unidades de 3 lições na trilha principal e 2 unidades de 3 lições na trilha de conversa. Cada lição tem 4 exercícios.

Tipos de exercício encontrados nos arquivos de inglês:

| Tipo | Quantidade | Como é corrigido |
|---|---|---|
| Múltipla escolha | 89 | Local |
| Completar lacuna | 60 | Local |
| Tradução | 60 | Professor (IA), que aceita variações equivalentes |
| Ordenar palavras | 44 | Local |
| Ditado (ouvir e escrever) | 17 | Local, com o áudio gerado pela voz Piper |
| Resposta aberta | 90 | Professor (IA) |

O francês segue a mesma estrutura, com pequenas diferenças na distribuição dos tipos.

### 🔎 Onde olhar

- Regras do material de apoio: [backend/app/services/study_material.py](backend/app/services/study_material.py)
- Prompt do material: [backend/prompts/material/exercicio_lacunas.txt](backend/prompts/material/exercicio_lacunas.txt)
- Testes do material: [backend/tests/test_study_material.py](backend/tests/test_study_material.py)
- Folha de impressão: [frontend/src/components/StudyMaterialSheet.tsx](frontend/src/components/StudyMaterialSheet.tsx)

---

## 🚀 Instalação

Para um computador novo, passo a passo, veja o **[Guia de instalação](docs/INSTALACAO.md)**. Aqui vai o resumo para quem já tem tudo pronto. Rode na pasta do projeto, em um PowerShell:

```powershell
# 1. Dependências dos três componentes
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1

# 2. Modelos locais (Qwen3 8B e 4B via Ollama, voz Piper, Whisper small)
powershell -ExecutionPolicy Bypass -File ai-model\scripts\setup_models.ps1

# 3. Verificação
powershell -ExecutionPolicy Bypass -File scripts\diagnostico.ps1
```

O passo 2 é o único que acessa a internet (além da instalação do Ollama e das dependências). Depois dele, o uso diário é offline.

### Requisitos

- Windows 10 ou 11, 64 bits
- Python 3.11 ou superior
- Node.js 20 ou superior
- [Ollama](https://ollama.com) instalado
- Microfone e saída de áudio
- Recomendado: GPU NVIDIA com 8 GB de VRAM (funciona em CPU também, só que mais devagar)
- Cerca de 10 GB livres em disco para os modelos

---

## ▶️ Como usar

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

O script confere o Ollama (sobe o serviço se estiver parado), baixa o modelo de conversa se faltar, verifica a voz e abre o app. O Electron também sobe o backend (porta 8000) e o servidor de voz (porta 8001) quando eles ainda não estão rodando. Os logs ficam em `%APPDATA%\english-teacher-frontend\logs`.

- Só verificar, sem abrir o app: `scripts\iniciar.ps1 -SomenteVerificar`
- Atalho na área de trabalho: rode uma vez `scripts\criar_atalho.ps1` e pronto, é só dar dois cliques em "English Teacher".

Para rodar cada parte à mão, em quatro terminais:

```powershell
# Ollama (se não estiver rodando como serviço)
ollama serve

# Servidor de voz
cd ai-model
.\.venv\Scripts\python.exe -m uvicorn speech_server:app --host 127.0.0.1 --port 8001

# Backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Interface
cd frontend
npm run electron:dev
```

### 🎤 Microfone e voz

- Clique no microfone para gravar e clique de novo para parar. A gravação para sozinha em 60 segundos.
- Com **Revisar a transcrição antes de enviar** ligado (padrão), o texto reconhecido aparece para você corrigir antes de mandar.
- Se o microfone falhar, a tela diz o motivo: permissão negada, dispositivo ausente ou em uso.
- Por padrão, o professor lê as respostas em voz alta. Na barra da conversa, ou em **Configurações → Resposta do professor**, você escolhe **Só texto**. O texto aparece sempre, mesmo se a voz estiver desligada ou falhar.

---

## 🖨️ Material de apoio

Ao final de uma conversa, clique em **Material de apoio**. O app gera uma folha pronta para imprimir com:

1. **Explicação da conversa**: o que foi praticado, em frases curtas em português (feito pela IA).
2. **Preencha as lacunas**: frases da própria conversa com palavras para completar, com banco de palavras nos níveis A1 e A2.
3. **Pontos de correção**: cada erro seu, com a forma errada, a certa e a explicação completa do professor. Esta parte vem direto das correções salvas, sem depender da IA.
4. **Exercícios de fixação**: de 3 a 5 exercícios novos (tradução e múltipla escolha), criados pela IA com base na conversa. O app descarta qualquer exercício em que a resposta não esteja entre as alternativas.
5. **Palavras para revisar**: um rodapé com até 6 dicas.

Quem decide o que entra é o app, não o modelo: tudo que a IA devolve passa por validação antes de chegar à folha, e seções vazias simplesmente não aparecem.

---

## 📚 Idiomas e trilhas

- **Idiomas:** inglês e francês, do A1 ao C1. Cada idioma tem trilha, voz, reconhecimento de fala e progresso próprios.
- **Trocar de idioma:** na barra da conversa ou em **Ajustes → Conversa → Idioma que você estuda**. Cada idioma começa uma conversa nova.
- **Conteúdo:** `backend\app\curriculum\en\` e `backend\app\curriculum\fr\`. Os prompts do professor ficam em `backend\prompts\en\` e `backend\prompts\fr\`.
- **Novo idioma:** cadastre em `backend\app\languages.py` (voz e código de reconhecimento) e crie as pastas de currículo e de prompts.

### Como a trilha funciona

- As lições são sequenciais: a próxima libera quando a anterior fica com pelo menos 70% de acertos.
- Os arquivos de currículo são validados na inicialização. Exercício mal formado impede o backend de subir, e a mensagem diz qual exercício precisa de ajuste. Assim, erro de conteúdo não chega ao aluno.
- Para editar o conteúdo, altere os JSON e reinicie o backend.

---

## 🛠️ Configurações

### Modelo de IA (Ollama)

```powershell
ollama pull qwen3:8b
ollama pull qwen3:4b
```

Para trocar o modelo, use **Configurações → Modelo LLM**. O modelo precisa estar instalado; o diagnóstico mostra quais estão disponíveis. Para guardar os modelos em outro disco, defina `OLLAMA_MODELS` antes de iniciar o Ollama.

### Reconhecimento de voz (Whisper)

Usa o modelo multilíngue `small` em CPU com INT8, carregado uma vez e reaproveitado. Para trocar:

```powershell
$env:ETL_STT_MODEL = "base"    # ou "medium" para mais precisão
```

Os modelos ficam em `ai-model\models\whisper`. Nada é baixado durante o uso: se faltar algum, o servidor de voz mostra o comando para instalar.

### Voz do professor (Piper)

As vozes padrão são `en_US-lessac-medium` (inglês) e `fr_FR-siwis-medium` (francês), em `ai-model\voices`. A voz troca sozinha com o idioma. Para usar outra, coloque os arquivos `.onnx` e `.onnx.json` nessa pasta e escolha em **Configurações → Voz**.

### GPU

O Ollama usa a GPU para o modelo de linguagem. O Whisper fica em CPU por padrão, para não disputar a VRAM. O diagnóstico mostra se o driver NVIDIA está presente. Não precisa instalar o CUDA Toolkit.

---

## 🔒 Privacidade e modo offline

- **Uso diário:** nenhuma chamada externa. Backend e servidor de voz recusam baixar modelos durante a operação (`local_files_only`).
- **Instalação e download de modelos:** exigem internet, feitos uma vez pelos scripts.
- **Atualizações:** manuais, substituindo as pastas do projeto.
- O backend só escuta em `127.0.0.1`. **Não exponha a porta 11434 na rede.**

Para testar o modo offline: depois do `setup_models.ps1`, desligue o Wi-Fi e o cabo e use o app normalmente.

---

## 💾 Seus dados

O banco fica em `data\english_teacher.sqlite3`. Ele **não vai para o GitHub** (está no `.gitignore`), então seu histórico fica só na sua máquina.

- **Backup automático:** antes de qualquer migração com dados, uma cópia vai para `data\backups\`.
- **Backup manual:** feche o app e copie o `english_teacher.sqlite3` (e os arquivos `-wal` e `-shm`, se existirem).
- **Exportação em JSON:** **Configurações → Exportar histórico**. É o formato recomendado para guardar.
- **Restauração:** feche o app, troque o arquivo pelo backup e abra de novo.

---

## 🧰 Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| "Não consegui me conectar ao backend" | O backend não subiu | Veja `%APPDATA%\<app>\logs\backend.log` |
| "O modelo 'qwen3:8b' não está instalado" | Modelo não baixado | `ollama pull qwen3:8b` |
| "Ollama não está respondendo" | Serviço parado | Abra o Ollama |
| "Servidor de voz indisponível" | O `ai-model` não subiu | Veja `logs\speech.log` |
| "Nenhum microfone foi encontrado" | Sem dispositivo de entrada | Conecte o microfone e tente de novo |
| Resposta do professor sem correção | O modelo devolveu texto fora do formato | Normal e tratado: a resposta aparece mesmo assim |
| Erro ao abrir o banco | Arquivo corrompido | Restaure um backup de `data\backups` |

---

## 🧑‍💻 Para quem quer mexer no código

```powershell
# Backend
cd backend ; .\.venv\Scripts\python.exe -m pytest -q

# Servidor de voz
cd ai-model ; .\.venv\Scripts\python.exe -m pytest -q

# Frontend
cd frontend ; npm test ; npm run typecheck
```

Os testes unitários usam um Ollama simulado, então não precisam de modelo instalado. Os testes com modelos reais (Ollama, Whisper, Piper e microfone) são manuais e estão descritos em `scripts\diagnostico.ps1`.

**Empacotamento:** ainda não configurado. A ideia é que o executável inclua backend, servidor de voz e interface, com os modelos baixados à parte em `data\models`.

---

## ⚠️ Limitações conhecidas

- As respostas aparecem de uma vez, não palavra por palavra: a saída estruturada precisa estar completa para ser validada antes de mostrar a correção.
- A avaliação de pronúncia compara palavras transcritas; não mede pronúncia fonética.
- O nível do aluno é definido manualmente.
- A interface foi validada com build e testes unitários. A execução com Electron e a gravação com microfone real precisam ser conferidas na sua máquina.
- O material de apoio foi testado com o Ollama simulado; a qualidade dos exercícios gerados depende do modelo local escolhido.

---

## 📜 Licenças

- **Código deste projeto:** a definir pelo autor.
- **Qwen3:** licença do Qwen (Apache 2.0 nas versões de interesse; confirme na página do modelo no Ollama).
- **faster-whisper e Whisper:** MIT.
- **Piper e a voz `en_US-lessac-medium`:** confira a licença da voz na página do projeto piper-voices no Hugging Face antes de distribuir.
- **Ollama:** MIT.
