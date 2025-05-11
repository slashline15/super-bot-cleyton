# Changelog do Sistema de Memória

## [1.0.0] - 2025-05-11

### Adicionado

- **ChromaManager**: Implementação robusta com padrão Singleton
- **Mecanismo de retry**: Exponential backoff para operações no ChromaDB
- **Scripts de manutenção**: check_memory.py, versão aprimorada do repair_memory.py
- **Documentação detalhada**: MEMORY_REFACTOR.md e README em src/bot/memory
- **Testes de integridade**: test_memory_refactor.py para validar o sistema

### Melhorado

- **MemoryManager**: Transações atômicas entre ChromaDB e SQLite
- **Busca semântica**: Filtragem por relevância e threshold de similaridade
- **Tratamento de erros**: Fallbacks e robustez em caso de falhas
- **Performance**: Otimização de consultas e redução de tokens
- **Estado da memória**: Diagnóstico e monitoramento simplificado

### Corrigido

- **Inconsistências de dados**: Algoritmo de sincronização entre bancos de dados
- **Perda de mensagens**: Verificação e reparo automático
- **Deadlocks**: Sistema de locks explícito para transações
- **Queries ineficientes**: Otimização de buscas desnecessárias
- **Duplicações**: Verificação de unicidade de embedding_ids

## Uso dos Novos Scripts

### Diagnóstico

```bash
# Verificação básica
python check_memory.py

# Com amostra de mensagens
python check_memory.py --sample

# Filtrando por usuário específico
python check_memory.py --user 123 --chat 456
```

### Reparo

```bash
# Reparo rápido (código + mensagens sem embedding)
python fix_memory.py

# Reparo completo (apenas mensagens com problemas)
python repair_memory.py

# Reconstrução completa dos índices
python repair_memory.py --force
```

### Teste

```bash 
# Executa testes do novo sistema
python -m tests.test_memory_refactor
```

## Arquitetura Refatorada

A nova arquitetura do sistema de memória implementa o padrão de camadas:

1. **LLMAgent**: Interface de alto nível para o bot
2. **MemoryManager**: Gerenciamento de operações e transações
3. **ChromaManager**: Acesso e manipulação do banco vetorial
4. **Database**: Acesso ao banco SQLite (mantido original)

A comunicação entre camadas segue regras estritas:
- LLMAgent → MemoryManager: Para todas operações de memória
- MemoryManager → ChromaManager e Database: Para operações nos bancos
- Nunca "pular" níveis (ex: LLMAgent → ChromaManager diretamente)

## Melhorias de Performance

- Redução de consultas desnecessárias ao ChromaDB
- Otimização na busca de mensagens similares
- Filtragem de queries muito curtas (< 3 palavras)
- Melhor uso de índices SQL para consultas frequentes

## Próximos Passos

1. Implementar um sistema de cache de consultas frequentes
2. Adicionar métricas de desempenho para operações de memória
3. Criar um modo "economia de tokens" para reduzir custos de API
4. Implementar compressão de contexto para mensagens longas
5. Adicionar exportação/importação completa da memória