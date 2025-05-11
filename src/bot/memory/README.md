# Sistema de Memória do Bot

## Visão Geral

O sistema de memória combina um banco de dados SQLite com o ChromaDB (banco de vetores) para fornecer:

1. **Armazenamento persistente** de todas as mensagens
2. **Busca semântica** para recuperar contexto relevante
3. **Categorização** de mensagens por importância e tópico

## Componentes

- **ChromaManager**: Gerencia conexão com o banco de dados vetorial
- **MemoryManager**: Coordena operações entre SQLite e ChromaDB
- **DocumentManager**: Gerencia textos longos e documentos

## Fluxo de Dados

1. **Adição de Mensagem**:
   ```
   SQLite (primeiro) → ChromaDB (segundo)
   ```

2. **Busca de Contexto**:
   ```
   ChromaDB (busca vetorial) → SQLite (recupera dados completos)
   ```

## Como Usar

### Adição de Mensagem

```python
memory = MemoryManager()
# Uso assíncrono (recomendado)
await memory.add_message(
    user_id=123,
    chat_id=456,
    content="Mensagem a salvar",
    role="user"
)

# Ou versão síncrona (apenas para scripts)
memory.add_message_sync(
    user_id=123,
    chat_id=456,
    content="Mensagem a salvar",
    role="user",
    category="obra",
    importance=3
)
```

### Busca de Contexto

```python
# Busca por relevância semântica
results = await memory.get_relevant_context(
    query="busca semântica",
    user_id=123,
    chat_id=456,
    limit=5,
    time_window=60  # minutos
)

# Busca de contexto completo para LLM
context = await memory.get_context_messages(
    user_id=123,
    chat_id=456,
    query="pergunta atual"
)
```

### Estatísticas

```python
# Obtém estatísticas por categoria
stats = await memory.get_category_stats(user_id=123, chat_id=456)

# Formato de retorno:
# {
#   'categories': [
#     {'category': 'obra', 'total': 15, 'avg_importance': 3.5, 'last_message': '2023-05-10...'},
#     {'category': 'financeiro', 'total': 8, 'avg_importance': 4.1, 'last_message': '2023-05-09...'}
#   ],
#   'total_messages': 23
# }
```

## Manutenção

### Diagnóstico

```bash
# Na raiz do projeto
python check_memory.py
```

### Reparo

```bash
# Reparo rápido
python fix_memory.py

# Reparo completo
python repair_memory.py
```

## Tratamento de Erros

O sistema possui várias camadas de proteção:

1. **Transações atômicas** para consistência
2. **Retry automático** em operações críticas
3. **Verificação de integridade** na inicialização
4. **Fallbacks** em caso de falha no ChromaDB

## Arquitetura Interna

```
LLMAgent
    └── MemoryManager
         ├── ChromaManager
         │    └── PersistentClient (chromadb)
         └── Database
              └── SQLite
```

## Estrutura do Banco

- **SQLite (messages)**: Armazena histórico completo, metadados e texto
- **ChromaDB (messages)**: Armazena embeddings para busca semântica