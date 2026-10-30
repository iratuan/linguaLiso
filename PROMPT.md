# PROMPT MESTRE: DESENVOLVIMENTO DO PROFESSOR PARTICULAR DE INGLÊS COM IA LOCAL

## 1. PAPEL DO AGENTE

Atue como arquiteto de software sênior, engenheiro de IA local, especialista em Python, PySide6, processamento de áudio, modelos de linguagem, reconhecimento de fala, síntese de voz e aplicações desktop para Windows.

Sua missão é projetar, implementar, testar e documentar um aplicativo desktop completo que funcione como um professor particular de inglês baseado em inteligência artificial local.

Não entregue apenas um protótipo visual, pseudocódigo, exemplos isolados ou instruções genéricas. Trabalhe diretamente no repositório disponibilizado, crie os arquivos necessários, implemente as funcionalidades, execute os testes possíveis e corrija os problemas encontrados.

Se o repositório estiver vazio, inicialize o projeto. Se já existir uma implementação, analise-a antes de modificá-la e preserve as funcionalidades válidas.

Não interrompa o trabalho para solicitar confirmação de decisões técnicas secundárias. Tome decisões fundamentadas, documente-as e prossiga.

---

## 2. OBJETIVO DO PRODUTO

Construir um aplicativo chamado provisoriamente **English Teacher Local**, capaz de atuar como professor particular de inglês, permitindo que o usuário converse por voz ou texto com uma IA que:

- Entenda frases faladas em inglês.
- Responda por texto e áudio.
- Corrija erros gramaticais e de vocabulário.
- Explique as correções em português brasileiro quando necessário.
- Conduza conversações naturais em inglês.
- Adapte as aulas ao nível do aluno.
- Simule situações reais de viagem, trabalho e cotidiano.
- Registre o histórico de aprendizagem.
- Identifique dificuldades recorrentes.
- Crie exercícios personalizados.
- Revise palavras e estruturas estudadas anteriormente.
- Funcione integralmente offline após a instalação e o download inicial dos componentes.

O sistema não deve depender de APIs pagas, serviços de IA em nuvem ou conexão com a internet durante o uso normal.

---

## 3. REQUISITOS DO AMBIENTE

Considere o seguinte ambiente de destino:

- Sistema operacional: Windows 10 ou Windows 11, 64 bits.
- Memória RAM: 32 GB.
- GPU: NVIDIA com 8 GB de VRAM.
- Linguagem principal: Python.
- Interface gráfica: PySide6.
- Banco de dados: SQLite.
- Modelo de linguagem: Ollama executando Qwen3 localmente.
- Reconhecimento de fala: faster-whisper.
- Síntese de voz: Piper.
- Microfone e dispositivo de reprodução de áudio disponíveis no Windows.

A GPU NVIDIA ainda não foi identificada pelo modelo exato. Portanto, não presuma que ela seja uma RTX específica.

Implemente detecção de hardware e configuração ajustável, com possibilidade de executar componentes na CPU quando necessário.

### Estratégia inicial dos modelos

LLM principal:
- Qwen3 8B, por meio do Ollama.
- Alternativa de contingência: Qwen3 4B.
- Modelo configurável nas preferências.
- Verificação de disponibilidade antes de iniciar uma sessão.

Reconhecimento de fala:
- faster-whisper.
- Modelo inicial `small.en`, com possibilidade de utilizar `base.en` ou `medium.en` quando apropriado.
- Execução inicial em CPU com INT8 para reduzir a disputa por VRAM.
- Opção de aceleração por GPU quando o hardware e as dependências forem compatíveis.

Síntese de voz:
- Piper.
- Voz inglesa americana inicial: `en_US-lessac-medium`.
- Possibilidade de selecionar outras vozes locais instaladas.
- Reprodução do áudio sem dependência de serviços externos.

Não trate esses modelos como requisitos imutáveis. Implemente uma camada de configuração que permita substituí-los sem refatorar o aplicativo inteiro.

Antes de escolher versões exatas de pacotes e modelos, verifique a compatibilidade entre Python, Windows, CUDA, cuDNN, Ollama e os componentes de áudio.

Não instale dependências desnecessárias nem recomende baixar o CUDA Toolkit sem demonstrar sua necessidade.

---

## 4. ARQUITETURA OBRIGATÓRIA

Adote uma arquitetura modular, separando interface, lógica pedagógica, serviços de IA, áudio, persistência e configuração.

Organize o projeto de forma semelhante à estrutura abaixo, adaptando-a quando houver justificativa técnica:

```text
EnglishTeacherLocal/
├── app.py
├── requirements.txt
├── pyproject.toml
├── README.md
├── .gitignore
├── config/
│   ├── settings.py
│   └── defaults.json
├── ui/
│   ├── main_window.py
│   ├── conversation_view.py
│   ├── lesson_view.py
│   ├── progress_view.py
│   ├── vocabulary_view.py
│   └── settings_view.py
├── services/
│   ├── llm_service.py
│   ├── speech_recognition_service.py
│   ├── speech_synthesis_service.py
│   ├── audio_capture_service.py
│   ├── conversation_service.py
│   ├── lesson_service.py
│   ├── pronunciation_service.py
│   └── model_manager.py
├── domain/
│   ├── learner.py
│   ├── lesson.py
│   ├── vocabulary.py
│   └── correction.py
├── repositories/
│   ├── database.py
│   ├── learner_repository.py
│   ├── lesson_repository.py
│   └── vocabulary_repository.py
├── prompts/
│   ├── system_teacher.txt
│   ├── conversation.txt
│   ├── correction.txt
│   └── roleplay.txt
├── migrations/
├── tests/
├── scripts/
└── data/
```

Os diretórios de modelos, áudio temporário e dados persistentes devem ser configuráveis.

Não misture lógica de interface com consultas SQL, inferência da LLM ou processamento de áudio.

Utilize classes, interfaces e tipagem sempre que contribuírem para legibilidade e manutenção.

---

## 5. INTERFACE GRÁFICA

Desenvolva uma interface moderna, limpa, profissional e adequada ao uso diário.

A aplicação deve funcionar em resoluções comuns de desktop, permitir redimensionamento e apresentar mensagens claras de erro e progresso.

### Tela principal

Deve conter:

1. Cabeçalho com o nome do professor.
2. Indicador de estado dos modelos locais.
3. Indicador de microfone e saída de áudio.
4. Histórico visual da conversa.
5. Campo de texto.
6. Botão para enviar mensagem.
7. Botão para iniciar e encerrar gravação.
8. Botão para reproduzir a última resposta.
9. Botão para interromper a reprodução de áudio.
10. Botão para repetir uma frase corrigida.
11. Seletor do nível do aluno.
12. Seletor do modo de aprendizagem.
13. Indicador de processamento.
14. Acesso ao histórico e progresso.
15. Acesso às configurações.

### Estados visuais

Diferencie claramente:

- Aguardando interação.
- Gravando áudio.
- Reconhecendo fala.
- Preparando resposta.
- Gerando áudio.
- Reproduzindo resposta.
- Modelo indisponível.
- Microfone indisponível.
- Erro de processamento.

A interface nunca deve congelar durante a inferência, gravação ou reprodução.

Utilize QThread, QRunnable ou uma estratégia equivalente compatível com Qt para operações demoradas. Atualize a interface somente pela comunicação segura entre threads.

Não use operações bloqueantes na thread principal.

---

## 6. MOTOR DE CONVERSAÇÃO COM IA

Implemente um serviço de conversação que se comunique com o Ollama local.

Requisitos:

- Endereço padrão local: `http://127.0.0.1:11434`.
- Modelo selecionável nas configurações.
- Verificação da API e do modelo antes de iniciar a conversa.
- Mensagens de erro úteis quando o Ollama não estiver disponível.
- Histórico limitado e configurável para controlar o consumo de memória.
- Prompt pedagógico centralizado em arquivos externos.
- Temperatura configurável.
- Timeout e tratamento de falhas.
- Cancelamento quando tecnicamente possível.
- Suporte a respostas progressivas por streaming.
- Não enviar conteúdo para APIs externas.
- Não tentar mudar automaticamente para um provedor em nuvem.

A aplicação deve continuar utilizável se o modelo configurado não estiver instalado. Nesse caso, explique como instalar um modelo local ou selecionar outro já disponível.

### Regras pedagógicas da LLM

O professor deve:

1. Usar inglês como idioma principal das conversações.
2. Reconhecer que o idioma nativo do aluno é português brasileiro.
3. Corrigir erros de maneira gentil.
4. Apresentar uma versão natural e correta da frase.
5. Explicar o erro de forma curta e clara.
6. Evitar interromper a fluência para corrigir detalhes irrelevantes.
7. Fazer uma pergunta por vez.
8. Adaptar vocabulário e complexidade ao nível do aluno.
9. Incentivar a produção ativa de frases.
10. Reaproveitar erros anteriores em exercícios.
11. Diferenciar erros gramaticais, de vocabulário e de adequação contextual.
12. Não afirmar que avaliou pronúncia quando recebeu apenas uma transcrição textual.
13. Evitar explicações longas quando o aluno estiver praticando conversação.
14. Permitir explicações em português mediante solicitação.
15. Nunca apresentar uma forma gramatical incorreta como regra correta.

### Formato interno de correção

Sempre que possível, represente correções com campos estruturados:

- `original_text`
- `corrected_text`
- `explanation_pt`
- `error_category`
- `severity`
- `example_sentence`
- `practice_prompt`

Valide a saída estruturada. Se a LLM retornar conteúdo inválido, aplique uma estratégia de recuperação sem encerrar a sessão.

Não dependa exclusivamente de JSON gerado pela LLM para manter o aplicativo funcional. Mensagens comuns devem continuar sendo exibidas mesmo quando a estrutura de correção não puder ser interpretada.

---

## 7. RECONHECIMENTO DE FALA

Implemente um serviço de reconhecimento de fala usando faster-whisper.

### Funcionalidades

- Captura do microfone padrão do Windows.
- Seleção de dispositivo de entrada.
- Gravação em memória ou arquivos temporários controlados.
- Conversão e validação da taxa de amostragem.
- Detecção de silêncio e atividade de voz.
- Filtragem de segmentos sem fala.
- Transcrição do áudio.
- Exibição do texto reconhecido antes do envio, quando o modo de confirmação estiver ativo.
- Opção de envio automático após detectar o fim da fala.
- Tratamento de gravações vazias.
- Tratamento de microfone desconectado.
- Mensagens de erro compreensíveis.
- Limpeza segura de arquivos temporários.

### Configuração inicial

Utilize `small.en` em CPU com INT8, mas permita mudar para modelos menores ou maiores.

Carregue o modelo apenas uma vez por sessão e reutilize a instância. Não recarregue o modelo a cada gravação.

Implemente gerenciamento explícito de memória e encerramento de recursos.

### Idiomas

A conversação pedagógica será prioritariamente em inglês.

Entretanto, o aplicativo deve permitir que o aluno solicite explicações em português. Projete a arquitetura para suportar futuramente um modelo multilíngue de reconhecimento de fala, selecionável nas configurações.

Não confunda idioma da interface, idioma de reconhecimento e idioma da conversa.

---

## 8. SÍNTESE DE VOZ

Implemente o Piper como serviço local de síntese de voz.

### Requisitos

- Voz inglesa configurável.
- Verificação dos arquivos de modelo e configuração.
- Geração de arquivos WAV em diretório temporário.
- Reprodução de áudio.
- Botão de interrupção imediata da reprodução.
- Tratamento de falhas.
- Controle de volume.
- Limpeza de arquivos temporários.
- Cache opcional de frases repetidas.
- Possibilidade de ouvir novamente uma correção.
- Nenhuma chamada a serviços de TTS externos.

Não execute um novo processo do Piper desnecessariamente para cada pequena operação se houver uma estratégia local mais eficiente e estável.

Separe o texto de aprendizagem da preparação do áudio. A interface deve exibir a resposta mesmo se a geração de voz falhar.

### Experiência conversacional

O aplicativo deve permitir conversar por turnos de voz:

1. O aluno inicia a gravação.
2. O aluno fala.
3. O sistema detecta o encerramento da fala ou recebe o comando para parar.
4. A fala é transcrita.
5. O texto é encaminhado à LLM.
6. A resposta aparece na interface.
7. O Piper gera a voz.
8. O áudio é reproduzido.
9. O aplicativo retorna ao estado de espera.

Não implemente detecção de silêncio excessivamente agressiva, pois ela pode cortar frases no meio.

A primeira versão deve priorizar estabilidade de conversação por turnos. Conversação contínua, com interrupções naturais e baixa latência, deve ser uma evolução posterior.

---

## 9. AVALIAÇÃO DE PRONÚNCIA

Crie uma arquitetura extensível para avaliação de pronúncia.

Não confunda reconhecimento de palavras com avaliação fonética.

Na primeira versão, ofereça:

- Comparação entre a frase esperada e a transcrição.
- Identificação de palavras omitidas, substituídas ou adicionadas.
- Exercícios de repetição.
- Feedback textual sobre diferenças identificadas.
- Aviso de que uma transcrição incorreta não comprova, por si só, um erro de pronúncia.

Prepare uma interface de serviço que permita implementar posteriormente análise fonética ou alinhamento de fonemas com ferramentas locais apropriadas.

Não apresente pontuações de pronúncia como medidas cientificamente precisas sem uma metodologia validada.

---

## 10. MODOS DE APRENDIZAGEM

Implemente os seguintes modos:

### A. Conversação livre

O professor conversa naturalmente e corrige os erros mais importantes.

### B. Aula guiada

O sistema define um objetivo, apresenta conteúdo, propõe exercícios, corrige respostas e encerra com um resumo.

### C. Gramática

Explicações curtas seguidas de exemplos e exercícios progressivos.

### D. Vocabulário

Apresentação de palavras com tradução, contexto, exemplos e revisão.

### E. Roleplay

Simulações de:

- Aeroporto.
- Hotel.
- Restaurante.
- Compras.
- Viagens.
- Entrevistas de emprego.
- Reuniões profissionais.
- Conversas cotidianas.
- Atendimento ao cliente.

O professor deve permanecer no papel selecionado até o aluno pedir para encerrar ou trocar de situação.

### F. Revisão de erros

Retomar erros frequentes registrados no histórico e produzir novos exercícios.

### G. Treino de escuta

Reproduzir frases e pequenos diálogos gerados localmente, fazer perguntas de compreensão e verificar as respostas.

---

## 11. PERFIL DO ALUNO E PROGRESSO

Implemente um perfil local com:

- Nível atual.
- Objetivos de aprendizagem.
- Preferência por inglês americano ou britânico.
- Idioma das explicações.
- Tempo de estudo desejado.
- Vocabulário conhecido.
- Erros recorrentes.
- Histórico de aulas.
- Exercícios concluídos.
- Itens para revisão.

Os níveis iniciais podem seguir uma progressão inspirada no CEFR:

- A1 — Iniciante.
- A2 — Básico.
- B1 — Intermediário.
- B2 — Intermediário superior.
- C1 — Avançado.

Não classifique automaticamente o aluno com precisão oficial a partir de poucas mensagens. Apresente avaliações como estimativas e permita correção manual.

Implemente revisão espaçada de vocabulário com intervalos configuráveis e um algoritmo simples, documentado e testável.

---

## 12. BANCO DE DADOS SQLITE

Utilize SQLite local, com migrações versionadas e transações.

Crie tabelas para:

- `learner_profile`
- `conversation_sessions`
- `messages`
- `corrections`
- `lessons`
- `lesson_exercises`
- `vocabulary_items`
- `vocabulary_reviews`
- `learning_goals`
- `app_settings`

Defina chaves primárias, chaves estrangeiras, índices e restrições apropriadas.

Armazene datas de forma consistente.

Não armazene gravações de áudio permanentemente por padrão. O comportamento deve privilegiar a privacidade, com opção explícita de salvar áudios para estudo.

Implemente:

- Inicialização automática do banco.
- Migrações.
- Recuperação de erros.
- Exportação de histórico em formato aberto.
- Limpeza de sessões e dados pelo usuário.
- Backup do banco antes de migrações destrutivas.
- Testes de persistência e integridade.

O banco deve continuar funcional sem conexão com a internet.

---

## 13. OPERAÇÃO TOTALMENTE OFFLINE

Este requisito é obrigatório.

Após a instalação inicial e o download dos modelos, todas as funções principais devem operar sem internet.

Implemente:

1. Modelos locais identificados por caminhos e configurações explícitas.
2. Verificação prévia da disponibilidade dos modelos.
3. Mensagens claras quando um modelo não estiver instalado.
4. Proibição de fallback automático para nuvem.
5. Nenhum uso de APIs externas para IA, voz, telemetria ou analytics.
6. Persistência local.
7. Funcionamento sem autenticação online.
8. Documentação do procedimento de instalação offline.
9. Teste de funcionamento com a rede desativada.
10. Registro local de erros, sem envio automático.

A aplicação não deve afirmar que está offline se algum componente estiver tentando acessar a rede.

Diferencie:

- Instalação online.
- Download dos modelos.
- Uso diário offline.
- Atualizações manuais.

Quando tecnicamente possível, permita apontar para modelos previamente baixados e verifique que os caminhos existem antes de iniciar o aplicativo.

Documente eventuais acessos de rede necessários ao próprio gerenciador de modelos durante a instalação. Não os utilize durante a operação normal.

---

## 14. SEGURANÇA E PRIVACIDADE

Implemente as seguintes proteções:

- Vincular a API local do Ollama apenas a `127.0.0.1`, salvo configuração explícita.
- Não expor portas para a rede local por padrão.
- Não executar comandos de sistema derivados de respostas da LLM.
- Não interpretar conteúdo gerado pela IA como código executável.
- Validar caminhos de arquivos.
- Limitar tamanho de mensagens e gravações.
- Tratar exceções sem revelar informações sensíveis.
- Não armazenar chaves ou credenciais desnecessárias.
- Não registrar áudio ou texto integral em logs de diagnóstico por padrão.
- Oferecer exclusão dos dados locais do aluno.
- Não usar serviços de telemetria.

O aplicativo deve continuar seguro mesmo diante de mensagens malformadas ou conteúdo inesperado gerado pelo modelo.

---

## 15. CONFIGURAÇÕES

Crie uma tela de preferências com:

- Modelo LLM selecionado.
- Modelo Whisper.
- Dispositivo de entrada.
- Dispositivo de saída.
- Voz Piper.
- Velocidade de reprodução.
- Volume.
- Nível do aluno.
- Idioma das explicações.
- Modo de correção.
- Envio automático ou manual da transcrição.
- Tamanho máximo do histórico enviado à LLM.
- Diretórios de dados e modelos.
- Opções de privacidade.
- Teste de microfone.
- Teste de voz.
- Diagnóstico dos componentes locais.

Salve as preferências localmente.

Valide todas as opções antes de aplicá-las. Não exija reiniciar a aplicação para mudanças que possam ser feitas com segurança durante a execução.

---

## 16. DESEMPENHO E GERENCIAMENTO DE RECURSOS

O aplicativo deve considerar os limites da GPU com 8 GB de VRAM.

- Não carregue várias cópias da mesma LLM.
- Evite executar Whisper e LLM simultaneamente na GPU por padrão.
- Comece com Whisper em CPU e INT8.
- Carregue a LLM por meio do Ollama.
- Permita ajustar o contexto da LLM.
- Evite histórico ilimitado.
- Reutilize modelos e serviços.
- Evite gravações de áudio desnecessariamente grandes.
- Execute tarefas pesadas fora da thread principal.
- Libere dispositivos de áudio e recursos durante o encerramento.
- Apresente mensagens úteis quando faltar memória.
- Registre latências de forma local e opcional.

Não prometa velocidade específica sem medições reais no hardware do usuário.

---

## 17. TESTES OBRIGATÓRIOS

Crie testes automatizados para:

- Inicialização do banco.
- Migrações.
- Salvamento e leitura do histórico.
- Perfil do aluno.
- Persistência de vocabulário.
- Formatação e validação de correções.
- Tratamento de respostas inválidas da LLM.
- Modelo local indisponível.
- Microfone indisponível.
- Arquivo de áudio inválido.
- Voz Piper ausente.
- Cancelamento da reprodução.
- Erros de processamento.
- Configurações inválidas.
- Ausência de conexão com a internet.
- Nenhuma chamada a serviços externos durante o fluxo normal.

Use mocks nos testes unitários para não exigir modelos pesados.

Crie testes de integração separados para Ollama, Whisper, Piper e dispositivos reais de áudio.

Quando o ambiente não tiver determinado hardware ou modelo, marque o teste como não executado por dependência ausente. Não declare sucesso sem ter executado a verificação.

Execute os testes disponíveis e corrija os defeitos encontrados.

---

## 18. INSTALAÇÃO E DISTRIBUIÇÃO

Crie scripts PowerShell para facilitar:

- Preparação do ambiente.
- Criação do ambiente virtual.
- Instalação das dependências.
- Verificação do Python.
- Verificação do driver NVIDIA.
- Verificação do Ollama.
- Download dos modelos.
- Download das vozes.
- Inicialização do aplicativo.
- Diagnóstico.
- Preparação de uma instalação offline.

Os scripts devem verificar pré-requisitos e apresentar mensagens claras.

Não apague arquivos do usuário nem reinstale drivers automaticamente.

Prepare também o empacotamento com PyInstaller, depois que o aplicativo estiver estável.

O pacote final deverá incluir os componentes próprios do aplicativo e instruções para os modelos locais. Não incorpore modelos gigantes no executável sem necessidade.

Documente separadamente as licenças de código, modelos de linguagem e vozes.

---

## 19. DOCUMENTAÇÃO

Entregue um README em português brasileiro com:

- Visão geral.
- Arquitetura.
- Requisitos mínimos.
- Instalação passo a passo no Windows.
- Configuração do Ollama.
- Download dos modelos.
- Configuração do Whisper.
- Configuração do Piper.
- Execução do aplicativo.
- Uso do microfone.
- Configuração da GPU.
- Funcionamento offline.
- Solução de problemas.
- Backup e restauração do banco.
- Testes.
- Empacotamento.
- Licenças.
- Limitações conhecidas.

Inclua comandos reais e compatíveis com a estrutura criada. Não deixe comandos fictícios ou referências a arquivos inexistentes.

---

## 20. FASES DE IMPLEMENTAÇÃO

Execute o desenvolvimento nesta sequência:

### Fase 1 — Inspeção e planejamento
Inspecione o repositório, identifique os arquivos existentes e apresente um plano técnico curto. Em seguida, prossiga para a implementação.

### Fase 2 — Fundação
Crie estrutura, configuração, logging local, banco SQLite, migrações e inicialização da interface.

### Fase 3 — LLM
Implemente a integração com Ollama, verificação de modelos, prompts pedagógicos e histórico.

### Fase 4 — Áudio
Implemente captura do microfone, reconhecimento de fala, síntese de voz, reprodução e cancelamento.

### Fase 5 — Experiência pedagógica
Implemente os modos de aprendizagem, correções, vocabulário, revisão e acompanhamento de progresso.

### Fase 6 — Robustez
Implemente tratamento de erros, gerenciamento de recursos, privacidade e funcionamento offline.

### Fase 7 — Testes
Execute testes unitários e de integração possíveis. Corrija os problemas identificados.

### Fase 8 — Distribuição
Crie scripts PowerShell, documentação e configuração do empacotamento.

Ao final de cada fase, verifique se os arquivos foram realmente criados e se os recursos básicos funcionam antes de avançar.

Não substitua uma funcionalidade real por um botão decorativo ou uma tela sem integração.

---

## 21. CRITÉRIOS DE ACEITAÇÃO

O projeto somente poderá ser considerado concluído quando:

1. O aplicativo abrir no Windows sem depender de uma IDE.
2. A interface permanecer responsiva durante o processamento.
3. O usuário conseguir conversar por texto com a LLM local.
4. O usuário conseguir gravar a própria voz.
5. A fala em inglês puder ser transcrita localmente.
6. A LLM puder corrigir e explicar erros.
7. O Piper puder reproduzir respostas faladas.
8. O usuário puder interromper a reprodução.
9. O histórico persistir após fechar e reabrir o aplicativo.
10. O perfil e o progresso forem armazenados no SQLite.
11. Os modos de aprendizagem estiverem integrados ao motor de conversação.
12. O aplicativo apresentar erros compreensíveis quando algum componente faltar.
13. O sistema funcionar sem internet após os downloads necessários.
14. Não houver fallback silencioso para serviços de nuvem.
15. Os testes executados estiverem documentados.
16. O README permitir que outra pessoa instale o sistema seguindo as instruções.
17. As limitações restantes estiverem documentadas honestamente.

---

## 22. RELATÓRIO FINAL DO AGENTE

Ao terminar, apresente:

- Arquitetura implementada.
- Principais arquivos criados ou modificados.
- Modelos e dependências selecionados.
- Comandos para instalar e executar.
- Testes executados e seus resultados reais.
- Testes que não puderam ser executados e o motivo.
- Procedimento para verificar o modo offline.
- Procedimento para gerar o executável.
- Limitações restantes.
- Próximas melhorias recomendadas.

Não declare que o sistema funciona integralmente sem internet, que utiliza a GPU ou que todos os testes passaram sem verificar essas condições.

**ORDEM FINAL:** comece inspecionando o repositório atual. Depois, implemente o sistema por fases, executando e corrigindo o código sempre que possível. Priorize um aplicativo realmente funcional, privado, estável e inteiramente local em vez de uma demonstração visual incompleta.