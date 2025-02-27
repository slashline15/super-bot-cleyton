
<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [Sistema de Memória - Documentação](#sistema-de-memória---documentação)
  - [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
    - [Tabela: messages](#tabela-messages)
      - [Campos:](#campos)
      - [Índices:](#índices)
  - [Próximos Passos](#próximos-passos)
  - [Como Usar](#como-usar)
- [Sugestões de melhoria do gemini](#sugestões-de-melhoria-do-gemini)

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

---

# Sugestões de melhoria do gemini

A documentação do seu projeto está boa como um ponto de partida, com a estrutura de pastas, conteúdo dos arquivos e alguns exemplos de uso. No entanto, há várias melhorias que podem torná-la mais completa, clara e útil para outros desenvolvedores (ou até mesmo para você no futuro). Aqui estão algumas sugestões:

**Geral:**

* **README.md:** Crie um arquivo README.md na raiz do projeto. Este é o primeiro arquivo que as pessoas verão, então ele deve fornecer uma visão geral do projeto, instruções de instalação, exemplos de uso e como contribuir.
* **Docstrings mais descritivas:** As docstrings existentes são um bom começo, mas podem ser expandidas.  Explique o propósito de cada função/classe/método com mais detalhes, incluindo os tipos de entrada e saída esperados, possíveis exceções e exemplos mais completos.
* **Documentação da arquitetura:** Descreva a arquitetura geral do projeto. Um diagrama simples pode ser muito útil para entender como os diferentes módulos interagem.
* **Tutorial ou guia de início rápido:** Um tutorial passo a passo mostrando como configurar e usar o bot seria muito benéfico para novos usuários.
* **Documentação das dependências:** Liste todas as dependências do projeto e suas versões em um arquivo `requirements.txt`. Isso facilita a instalação e garante a compatibilidade. Use `pip freeze > requirements.txt` para gerar o arquivo.
* **Documentação da API:** Se o projeto expõe alguma API, documente-a detalhadamente.  Considere usar ferramentas como Sphinx ou Swagger para gerar documentação de API interativa.
* **Testes como documentação:**  Mantenha os testes atualizados e bem escritos. Testes bem escritos podem servir como exemplos de como usar o código.
* **Controle de Versão:** Utilize um sistema de controle de versão como o Git e faça commits frequentes com mensagens descritivas. O histórico de commits pode ser uma fonte valiosa de informação sobre as mudanças no projeto.

**Específico para o código:**

* **`src/bot/document_processor.py`**: Os métodos `process_invoice` e `process_purchase_order` estão incompletos.  Implemente a lógica ou, se forem placeholders, adicione comentários explicando o que eles devem fazer.  Documente as exceções `InvalidDocumentError` e `InvalidPOError`.
* **`src/bot/main.py`**:  A função `init_google_auth` parece incompleta e não está sendo usada no `main`.  Finalize a implementação ou remova-a. Documente melhor o propósito do arquivo e da função `main`.
* **`src/bot/agents/llm_agent.py`**: Documente melhor o propósito do `SYSTEM_PROMPT` e como ele afeta o comportamento do bot.
* **`src/bot/agents/gemini/client.py`**:  Explique como configurar a API Key do Gemini.
* **`src/bot/database/models.py`**:  Este arquivo parece estar incompleto.  Defina a classe `Base` e a variável `engine`.  Implemente os atributos das classes `Invoice` e `PurchaseOrder` usando SQLAlchemy.
* **`src/bot/models/authorization_data.py`**: Documente o propósito de cada campo da classe `AuthorizationData`.
* **`src/bot/processors/ap_processor.py`**: Documente a lógica de cálculo das retenções em `_calculate_retencoes` e como o código do insumo é determinado em `_get_codigo_insumo`.
* **`src/bot/utils/notion_sync.py`**: Explique como configurar o token do Notion e o ID do banco de dados.
* **`src/config/config.py`**: Documente o propósito de cada variável de ambiente.

**Ferramentas:**

* **Sphinx:**  Uma ferramenta poderosa para gerar documentação HTML a partir de docstrings e outros arquivos de texto.
* **pdoc:** Uma ferramenta mais simples para gerar documentação HTML diretamente das docstrings.
* **MkDocs:**  Outra boa opção para criar documentação de projetos em Python.

**Exemplo de melhoria de docstring:**

```python
def process_invoice(self, file_path: str) -> Dict[str, Any]:
    """Processa uma nota fiscal e extrai informações relevantes.

    Lê o arquivo da nota fiscal no caminho especificado, extrai informações
    como número da nota, data de emissão, valor total, etc., e retorna
    um dicionário contendo esses dados.

    Args:
        file_path (str): O caminho para o arquivo da nota fiscal.

    Returns:
        Dict[str, Any]: Um dicionário contendo as informações extraídas da nota fiscal.
                       Retorna um dicionário vazio se ocorrer algum erro durante o processamento.

    Raises:
        FileNotFoundError: Se o arquivo especificado não for encontrado.
        InvalidDocumentError: Se o arquivo não for uma nota fiscal válida.

    Example:
        >>> data = processor.process_invoice("path/to/invoice.pdf")
        >>> print(data["invoice_number"])
    """
    # Implementação da função aqui...
```


Ao implementar essas sugestões, sua documentação se tornará muito mais útil e facilitará a compreensão e a manutenção do seu projeto. Lembre-se de que uma boa documentação é um investimento que economiza tempo e esforço a longo prazo.