Você: file data\docs\tree-histories\bot-project-2025-02-08-00-22-55.txt

Processando arquivo: data\docs\tree-histories\bot-project-2025-02-08-00-22-55.txt
Tipo MIME: text/plain

Fazendo upload...
Arquivo 'bot-project-2025-02-08-00-22-55.txt' enviado com URI: https://generativelanguage.googleapis.com/v1beta/files/ph3itwomn1hy
Aguardando processamento do arquivo...
Aguardando o processamento do arquivo: bot-project-2025-02-08-00-22-55.txt

Arquivo processado e ativo!

Qual instrução você quer dar para o processamento do arquivo?
(Ex: 'Faça um resumo', 'Extraia os principais pontos', etc)
Instrução: Analise a estrutura do projeto e sugira uma documentação inicial, focando na organização dos módulos e suas responsabilidades

Iniciando análise...

Resultado da análise:
----------------------------------------------------------------------------------------------------
```markdown
# Projeto Super Bot Eng Cleyton 1.0

Cognitive Logic Engineered for Yield-driven Technology and Operational Networks

## Visão Geral

Este projeto visa criar um chatbot para auxiliar em tarefas de engenharia, como diário de obra, controle financeiro, acompanhamento de cronogramas e gerenciamento de documentos.  O bot utiliza o modelo de linguagem grande (LLM) da OpenAI (ou Gemini, configurável) e integra com o Telegram para interação com o usuário. A memória de conversas é gerenciada usando ChromaDB e um banco de dados SQLite, permitindo contexto e recuperação de informações.  Adicionalmente, há integração com o Notion para sincronização de dados.


## Arquitetura do Projeto

O projeto é organizado em módulos principais com responsabilidades bem definidas:

### 1. `src/bot`:  Módulo principal do Bot

- **`main.py`**: Ponto de entrada da aplicação. Inicializa o bot do Telegram, configura logging, carrega variáveis de ambiente e registra os handlers.
- **`agents`**: Contém os agentes de IA.
    - **`llm_agent.py`**: Responsável pela interação com a API do LLM (OpenAI/Gemini), gerenciando contexto, tokens e chamadas à API. Implementa a personalidade e as regras do chatbot.
    - **`gemini`**:  Módulo para integração com o Google Gemini.
        - `client.py`: Implementa a comunicação com a API Gemini.
        - `config.py`: Define as configurações do Gemini (temperatura, top_p, etc.).
- **`database`**: Gerencia a persistência de dados.
    - **`db_conection.py`**: Gerencia a conexão com o banco de dados SQLite, garantindo segurança e thread-safety.
    - **`db_init.py`**: Inicializa o banco de dados, cria as tabelas e índices.
- **`google_auth_helper`**:  Lida com a autenticação em serviços Google.
    - **`auth.py`**: Gerencia credenciais, tokens e oferece métodos para autenticação OAuth2 e Service Account.
- **`handlers`**: Contém os handlers para o Telegram.
    - **`telegram_llm_handler.py`**: Processa as mensagens do Telegram, encaminhando para o agente LLM e retornando as respostas. Inclui manipulação de mensagens de texto e voz.
- **`memory`**: Gerencia a memória de longo prazo usando ChromaDB.
    - **`memory_manager.py`**:  Responsável por adicionar, buscar e gerenciar mensagens na memória, integrando com o ChromaDB e SQLite para otimização.
    - **`document_manager.py`**: Gerencia documentos, dividindo-os em chunks e armazenando no ChromaDB, com metadados no SQLite.
- **`models`**: Define modelos de dados.
    - **`authorization_data.py`**: Modelo para os dados de Autorização de Pagamento.
- **`processors`**: Processa documentos para extração de informações.
    - **`ap_processor.py`**: Processa dados de NFSe e gera dados para Autorização de Pagamento.
    - **`document_processor.py`**: Classe base para processadores de documentos, oferecendo métodos utilitários para extração de texto, datas e valores. Define as classes `NFSeData` e `APData`.
- **`utils`**: Módulo com utilitários diversos.
    - **`audio_utils.py`**:  Utilitários para transcrição de áudio usando a API do OpenAI Whisper.
    - **`data_utils.py`**:  Utilitários para normalização da mensagem para o Notion
    - **`image_processor.py`**: Utilitários para pré-processamento de imagens antes do OCR.
    - **`notion_sync.py`**: Sincronização com o Notion, enviando dados do SQLite para um banco de dados Notion.

### 2. `src/config`: Configurações

- **`config.py`**: Define as configurações gerais do projeto, incluindo chaves de API, nome do modelo LLM, parâmetros do ChromaDB.

### 3. `scripts`: Scripts auxiliares

- **`gemini_config.py`**:  Script para configurar o cliente Gemini. (Não está sendo usado diretamente pelo bot.)

### 4. `tests`: Testes unitários

- Contém testes para os principais módulos do bot. É crucial para garantir a qualidade e a funcionalidade do código.

### 5. Outras pastas e arquivos:

- **`chroma_db`**: Diretório onde o ChromaDB persiste seus dados.
- **`credentials`**: Pasta para armazenar arquivos de credenciais (Google).
- **`data`**:  Pasta que armazena arquivos de documentação da empresa e os dados das NFs.
- **`.env`**: Arquivo para armazenar variáveis de ambiente.
- **`requirements.txt`**:  Lista as dependências do projeto.
- **`setup.py`**:  Script para instalação do projeto.



## Fluxo de Execução

1. O usuário envia uma mensagem de texto ou voz via Telegram.
2. `telegram_llm_handler` recebe a mensagem.
3. Se for áudio, `audio_utils` transcreve para texto.
4. O texto da mensagem é enviado ao `llm_agent`.
5. `llm_agent` recupera o contexto relevante do `memory_manager`.
6. `llm_agent` interage com a API OpenAI/Gemini, enviando a mensagem e o contexto.
7. A resposta do LLM é retornada ao `telegram_llm_handler`.
8. O handler envia a resposta de volta ao usuário no Telegram.
9. As mensagens (pergunta e resposta) são armazenadas na memória pelo `memory_manager`, que usa ChromaDB e SQLite.
10. Opcionalmente, as mensagens podem ser sincronizadas com o Notion usando `notion_sync`.

## Próximos passos

- Implementar testes unitários mais completos.
- Melhorar o processamento de documentos (NFSe, etc.)
- Refinar a personalidade e as habilidades do chatbot.
- Adicionar mais recursos e integrações conforme necessário.

```


Esta documentação oferece uma visão geral da estrutura do projeto, destacando os módulos principais e suas responsabilidades. Ela serve como um guia inicial para entender o funcionamento do Super Bot Eng Cleyton.  A clareza na organização do código e a documentação adequada facilitarão a manutenção e a expansão do projeto no futuro.
----------------------------------------------------------------------------------------------------

Você: