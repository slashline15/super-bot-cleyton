
<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Sistema de Memória - Documentação](#sistema-de-memória---documentação)
  - [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
    - [Tabela: messages](#tabela-messages)
      - [Campos:](#campos)
      - [Índices:](#índices)
  - [Próximos Passos](#próximos-passos)
  - [Como Usar](#como-usar)

<!-- /code_chunk_output -->

# Sistema de Memória - Documentação

## Estrutura do Banco de Dados

### Tabela: messages
A tabela `messages` armazena todas as mensagens do bot e foi atualizada com novos campos para suportar o sistema de memória.

#### Campos:
- **Campos Principais:**
  - `id`: Identificador único da mensagem
  - `user_id`: ID do usuário no Telegram
  - `role`: Papel da mensagem (user/assistant)
  - `content`: Conteúdo da mensagem
  - `chat_id`: ID do chat no Telegram
  - `context_id`: ID do contexto da conversa
  - `timestamp`: Data/hora da mensagem
  - `tokens`: Quantidade de tokens na mensagem

- **Novos Campos:**
  - `category`: Categorização da mensagem (ex: diario_obra, financeiro)
  - `importance`: Nível de importância (1-5)
  - `embedding_id`: ID do embedding no ChromaDB

#### Índices:
- `idx_messages_user_chat`: Otimiza busca por usuário e chat
- `idx_messages_timestamp`: Otimiza busca por data/hora
- `idx_messages_category`: Otimiza busca por categoria
- `idx_messages_importance`: Otimiza busca por importância

## Próximos Passos
1. Integrar ChromaDB com LLMAgent
2. Implementar sistema de categorização automática
3. Definir critérios de importância
4. Criar sistema de recuperação contextual

## Como Usar
Para acessar os novos campos, use queries SQL incluindo as novas colunas:

```sql
-- Exemplo: Buscar mensagens importantes de uma categoria
SELECT * FROM messages 
WHERE category = 'diario_obra' 
AND importance >= 4 
ORDER BY timestamp DESC;
```

<style>
  body {
    font-family: Monopaced, sans-serif;
    background-color:rgb(39, 37, 37); /* Cor de fundo preto*/
    color: #333;
  }
</style>
<HTML>
  <HEAD>
    <TITLE>Próximos Passos - Interface web</TITLE>
  </HEAD>
  <BODY>
<H1>Próximos Passos</H1>
  <UL>
    <h2><b>Foco total:</b></h2>
      <LI>Integrar ChromaDB com LLMAgent</LI>
      <LI>Como assim esse cara ainda não foi integrado?</LI>
      <LI>Implementar sistema de categorização automática</LI>
      <LI>Definir critérios de importância</LI>
      <LI>Criar sistema de recuperação contextual</LI>
    <button onclick="window.location.href='https://www.google.com'"><b>Clique aqui para ver o próximo passo</b></button>
  </UL>
</BODY>
</HTML>