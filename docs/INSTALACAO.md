# Guia de instalação — English Teacher Local

Este guia leva um computador Windows do zero até o aplicativo funcionando. Siga as etapas na ordem.

> Os comandos são para o **PowerShell** (procure "PowerShell" no menu Iniciar). Não precisa de permissão de administrador.

---

## 1. Requisitos

| Item | Mínimo | Recomendado |
|---|---|---|
| Sistema | Windows 10 ou 11, 64 bits | Windows 11 |
| Memória RAM | 16 GB | 32 GB |
| Placa de vídeo | Não é obrigatória (roda em CPU, mais devagar) | NVIDIA com 8 GB de VRAM |
| Disco livre | 12 GB | 20 GB |
| Microfone e alto-falante | Para usar a voz | — |
| Internet | Só na instalação e no primeiro download dos modelos | — |

Depois da instalação, o uso diário funciona **sem internet**.

---

## 2. Instalar as ferramentas básicas

Você precisa de três programas. Se já tiver algum deles, confira a versão e pule.

### 2.1 Python 3.11 ou superior

1. Acesse https://www.python.org/downloads/ e baixe a versão mais recente (3.11 ou superior).
2. Na primeira tela do instalador, **marque a opção "Add python.exe to PATH"**. Esse passo é essencial.
3. Clique em "Install Now".

Confira no PowerShell:

```powershell
python --version
```

Deve aparecer algo como `Python 3.12.x`. Se aparecer "não é reconhecido", feche e abra o PowerShell; se persistir, reinstale o Python marcando a opção do PATH.

### 2.2 Node.js 20 ou superior

1. Acesse https://nodejs.org e baixe a versão **LTS**.
2. Instale com as opções padrão.

```powershell
node --version
npm --version
```

### 2.3 Ollama (o motor do modelo de linguagem)

1. Acesse https://ollama.com/download e baixe o instalador do Windows.
2. Instale com as opções padrão.
3. Ao final, o Ollama deve aparecer na bandeja do sistema (perto do relógio).

Confira no PowerShell:

```powershell
ollama --version
```

> O Ollama é instalado **à parte** (não vem no projeto). O script `iniciar.ps1` verifica se ele está rodando e o inicia quando necessário.

---

## 3. Obter o projeto

Copie a pasta `ia_teacher` para o computador novo. Pode ser por pendrive, nuvem ou repositório Git. O caminho usado neste guia é:

```
E:\SANDBOX_CLAUDE\ia_teacher
```

Use o caminho que você preferir; os comandos abaixo partem da pasta do projeto. Se a pasta estiver em outro lugar, ajuste o caminho nos comandos.

```powershell
cd E:\SANDBOX_CLAUDE\ia_teacher
```

> **Não copie** as pastas `backend\.venv`, `ai-model\.venv`, `frontend\node_modules`, `data` e `ai-model\models`. Elas são criadas ou baixadas na instalação. Se você copiou o projeto de outro computador, apague essas pastas antes de continuar.

---

## 4. Instalar as dependências

Este comando cria os ambientes Python, instala as bibliotecas e prepara a interface:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
```

O que ele faz, na ordem:

1. **backend:** cria `backend\.venv` e instala FastAPI, SQLite (via Python), httpx e as demais dependências.
2. **ai-model:** cria `ai-model\.venv` e instala faster-whisper (reconhecimento de voz), piper-tts (voz do professor) e o servidor de voz.
3. **frontend:** roda `npm install` e baixa as dependências da interface (React, Vite, Electron).

Pode levar de 5 a 15 minutos, dependendo da internet. Ao final aparece a mensagem "Dependências instaladas".

Se alguma etapa falhar, veja a seção de [problemas comuns](#problemas-comuns).

---

## 5. Baixar os modelos

Os modelos são grandes e não vêm no projeto. Este comando baixa o modelo de conversa, a voz e o modelo de reconhecimento de fala:

```powershell
powershell -ExecutionPolicy Bypass -File ai-model\scripts\setup_models.ps1
```

| Modelo | Tamanho aproximado | Para que serve |
|---|---|---|
| `qwen3:8b` | 5,2 GB | Conversa e correções (principal) |
| `qwen3:4b` | 2,5 GB | Alternativa mais leve |
| Vozes `en_US-lessac-medium` e `fr_FR-siwis-medium` | 65 MB cada | Voz do professor (inglês e francês) |
| Whisper `small` (multilíngue) | cerca de 500 MB | Reconhecimento da sua fala em inglês e francês |

O comando baixa o `qwen3:4b` também. Se quiser pular um grupo:

```powershell
# Só a voz e o reconhecimento de fala (o modelo de conversa vem depois, pelo iniciar.ps1)
powershell -ExecutionPolicy Bypass -File ai-model\scripts\setup_models.ps1 -SkipLlm

# Só o modelo de conversa principal (sem o qwen3:4b)
powershell -ExecutionPolicy Bypass -File ai-model\scripts\setup_models.ps1 -SkipVoice -SkipWhisper -WithFallbackLlm:$false
```

> O download do modelo de conversa é feito pelo Ollama, que precisa estar instalado (passo 2.3).

---

## 6. Verificar a instalação

```powershell
powershell -ExecutionPolicy Bypass -File scripts\diagnostico.ps1
```

Você deve ver `[OK]` em todas as linhas. Os itens de "Serviços em execução" aparecem como `[FALHA]` enquanto o aplicativo não estiver aberto, e isso é normal nesse momento.

Para verificar também o modelo e a voz, sem abrir o aplicativo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1 -SomenteVerificar
```

Saída esperada:

```
==> Ollama          OK: já está rodando
==> Modelo          OK: instalado
==> Voz             OK: arquivos de voz encontrados
==> Verificação concluída
```

---

## 7. Abrir o aplicativo

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

O script:

1. Verifica se o Ollama está rodando e o inicia se preciso.
2. Verifica se o modelo está instalado e o baixa se faltar.
3. Confere os arquivos da voz.
4. Abre a janela do aplicativo. A janela sobe o backend e o servidor de voz automaticamente.

Deixe a janela do PowerShell aberta enquanto usa o app. Para encerrar, feche a janela do aplicativo e, se necessário, pressione `Ctrl+C` no PowerShell.

### Criar atalho na área de trabalho

```powershell
powershell -ExecutionPolicy Bypass -File scripts\criar_atalho.ps1
```

Depois disso, basta dar dois cliques em **English Teacher** na área de trabalho.

---

## 8. Primeiro uso

1. **Permita o microfone** quando o Windows pedir. Se você negou antes, vá em *Configurações → Privacidade e segurança → Microfone* e ative para aplicativos de área de trabalho.
2. Abra **Ajustes** no menu lateral e preencha seu **perfil** (nome e nível). O nível define a dificuldade das conversas e das trilhas.
3. Comece pela **Trilha** (lição 1) ou converse com o professor em **Conversa**.

---

## 9. Dados e backup

Todos os seus dados ficam em `data\` dentro do projeto:

- `data\english_teacher.sqlite3`: banco com perfil, conversas, correções, progresso e vocabulário.
- `data\backups\`: cópias automáticas feitas antes de atualizações do banco.

**Para fazer backup**, feche o aplicativo e copie a pasta `data` inteira. Também é possível exportar tudo em JSON, em **Ajustes → Seus dados → Exportar**.

**Para usar em outro computador**, copie a pasta `data` junto com o projeto e siga os passos 4 a 7 (sem precisar baixar os modelos de novo, desde que a pasta `ai-model\models` também seja copiada).

Os logs técnicos ficam em `%APPDATA%\english-teacher-frontend\logs`.

---

## Problemas comuns

### "python não é reconhecido como comando"
O Python não está no PATH. Reinstale marcando **Add python.exe to PATH**, ou adicione a pasta do Python manualmente às variáveis de ambiente.

### "Não é possível carregar o arquivo … porque a execução de scripts está desabilitada"
Use sempre o comando com `-ExecutionPolicy Bypass`, como mostrado neste guia. Não é preciso alterar a política do Windows.

### "Ollama não encontrado"
Instale o Ollama (passo 2.3) e abra o aplicativo uma vez. Depois rode `iniciar.ps1` de novo.

### "O modelo 'qwen3:8b' não está instalado"
Baixe com:
```powershell
ollama pull qwen3:8b
```
Ou simplesmente rode `scripts\iniciar.ps1`, que faz isso automaticamente.

### Porta 5173, 8000 ou 8001 já em uso
Outro programa (ou outra janela do aplicativo) está usando a porta. Feche a janela anterior do aplicativo e os terminais que estiverem rodando `iniciar.ps1` ou `npm run electron:dev`. Se não souber qual programa, reinicie o computador.

### A janela do aplicativo não abre (erro sobre o Electron)
Em geral, o binário do Electron não foi baixado na instalação. Rode:
```powershell
cd frontend
node node_modules\electron\install.js
cd ..
```

### Erro ao instalar `av` ou faster-whisper
Confira que o `ai-model\requirements.txt` contém `av>=11,<17`. Se você atualizou manualmente alguma biblioteca, reinstale com:
```powershell
ai-model\.venv\Scripts\python.exe -m pip install "av>=11,<17"
```

### Microfone não funciona
- Confirme que há um microfone conectado e reconhecido no Windows (*Configurações → Som*).
- Confirme a permissão em *Configurações → Privacidade e segurança → Microfone*.
- Feche outros programas que possam estar usando o microfone (Teams, Discord, Zoom).

### O professor não fala
Verifique se a saída de áudio está correta e se a resposta não está configurada como "Só texto" (em *Ajustes → Voz*). Em *Ajustes → Diagnóstico*, a linha "Voz do professor" mostra o estado.

### Resposta muito lenta
A primeira resposta de cada sessão é mais demorada, porque o modelo é carregado na memória. Se continuar lenta, feche outros programas pesados e prefira o modelo `qwen3:4b` em *Ajustes → Conversa → Modelo*.

### Quero reinstalar do zero
Apague `backend\.venv`, `ai-model\.venv` e `frontend\node_modules`, depois repita os passos 4 e 5. **Não apague a pasta `data`** se quiser manter seu histórico.

---

## Resumo rápido (computador novo)

```powershell
# 1. Instale Python 3.11+ (com PATH), Node.js 20+ e Ollama. Depois:
cd E:\SANDBOX_CLAUDE\ia_teacher

# 2. Dependências
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1

# 3. Modelos de voz e reconhecimento (o modelo de conversa é baixado no passo 4)
powershell -ExecutionPolicy Bypass -File ai-model\scripts\setup_models.ps1

# 4. Abrir o aplicativo (baixa o modelo de conversa se faltar)
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1

# 5. (Opcional) Atalho na área de trabalho
powershell -ExecutionPolicy Bypass -File scripts\criar_atalho.ps1
```
