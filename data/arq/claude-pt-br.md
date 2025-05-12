# CLAUDE.md

Este arquivo fornece orientação para o Claude Code (claude.ai/code) ao trabalhar com código neste repositório.

## Visão Geral do Projeto

Super-Bot-Cleyton é um chatbot assistente para Telegram focado em gerenciamento de engenharia, com integração LLM (OpenAI/Gemini), persistência de memória (ChromaDB + SQLite) e processamento de documentos. O bot mantém o contexto da conversa através de busca semântica e auxilia em tarefas relacionadas a fluxos de trabalho de engenharia.

## Executando o Bot

```bash
# Ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt

# Iniciar o bot
python run.py
```

## Testes

Execute testes individuais com:
```bash
# Executar testes específicos
python -m tests.test_llm_agent
python -m tests.test_chroma_mem
python -m tests.test_memory_manager
python -m tests.test_database

# Executar testes de integração
python -m tests.test_integrations
```

## Manutenção do Sistema de Memória

Existem dois scripts para corrigir problemas de memória:

```bash
# Correção simples (modifica o código do agente LLM)
python fix_memory.py

# Reparo completo (reconstrói o ChromaDB a partir do SQLite)
python repair_memory.py
```

## Componentes Principais

1.  **Agente LLM** (`src/bot/agents/llm_agent.py`): Interface abstrata para os provedores OpenAI e Google Gemini
2.  **Gerenciador de Memória** (`src/bot/memory/memory_manager.py`): Lida com a recuperação de contexto e persistência de mensagens
3.  **Bot Principal** (`src/bot/main.py`): Configuração e manipuladores do bot Telegram
4.  **Gerenciador ChromaDB** (`src/bot/memory/chroma_manager.py`): Banco de dados vetorial para busca semântica

## Configuração

A configuração é gerenciada através de:
1.  Variáveis de ambiente (`.env`)
2.  Configuração de tempo de execução (`config/runtime_config.json`)
3.  Classe de configuração (`src/config/config.py`)

Parâmetros chave de configuração:
-   `llm_provider`: 'openai' ou 'gemini'
-   `model`: O modelo LLM a ser usado
-   `temperature`: Criatividade da resposta (0-1)
-   `max_tokens`: Máximo de tokens para o contexto

## Problemas Comuns

1.  **Divergência de Memória**: Se o ChromaDB e o SQLite ficarem dessincronizados, use `repair_memory.py`
2.  **Problemas de Contexto**: Se a recuperação de contexto parecer quebrada, use `fix_memory.py`
3.  **Uso de Tokens**: Monitore o uso de tokens no diretório `data/usage/`

## Fluxo de Trabalho de Desenvolvimento

1.  Faça alterações no código
2.  Execute os testes relevantes
3.  Teste com o bot em execução
4.  Monitore o uso da memória e o desempenho