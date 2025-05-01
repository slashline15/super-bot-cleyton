# 🧠 Super Bot CLEYTON

**CLEYTON** é uma IA sarcástica e funcional, inspirada em Rick Sanchez, projetada para auxiliar na gestão de obras. Integrando OpenAI, ChromaDB, Notion, Google Sheets e Gemini, ele oferece funcionalidades como diário de obra, controle financeiro, cronogramas e gerenciamento de documentos.

## 🚀 Funcionalidades

- **Assistente de Obra**: Registro de atividades, atrasos e reuniões.
- **Memória Vetorial**: Contexto semântico com ChromaDB.
- **Integrações**: OpenAI (GPT-4o), Google Gemini, Notion, Google Sheets.
- **Processamento de Documentos**: Análise de PDFs e áudios.
- **Interface CLI**: Testes interativos com o Gemini.

## 🛠️ Estrutura do Projeto

```
super-bot-cleyton/
├── src/
│   └── bot/
│       ├── agents/
│       ├── database/
│       ├── memory/
│       ├── prompts/
│       └── utils/
├── tests/
├── data/
├── docs/
├── .env.exemplo
└── README.md
```

## ⚙️ Configuração

1. Renomeie `.env.exemplo` para `.env` e preencha com suas credenciais.
2. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate no Windows
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```


## 🧪 Testes

Execute os testes com:

```bash
python -m tests.test_<nome_do_teste>
```

Exemplos:
- `test_chroma_mem`
- `test_database`
- `test_document_manager`
- `test_llm_agent`

## 📄 Licença

Este projeto está sob a licença MIT.
