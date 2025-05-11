# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Super-Bot-Cleyton is a Telegram chatbot assistant for engineering management, with LLM integration (OpenAI/Gemini), memory persistence (ChromaDB + SQLite), and document processing. The bot maintains conversational context through semantic search and helps with tasks related to engineering workflows.

## Running the Bot

```bash
# Activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Start the bot
python run.py
```

## Testing

Run individual tests with:
```bash
# Run specific tests
python -m tests.test_llm_agent
python -m tests.test_chroma_mem
python -m tests.test_memory_manager
python -m tests.test_database

# Run integration tests
python -m tests.test_integrations
```

## Memory System Maintenance

There are two scripts for fixing memory issues:

```bash
# Simple fix (modifies LLM agent code)
python fix_memory.py

# Complete repair (rebuilds ChromaDB from SQLite)
python repair_memory.py
```

## Key Components

1. **LLM Agent** (`src/bot/agents/llm_agent.py`): Abstract interface for both OpenAI and Google Gemini providers
2. **Memory Manager** (`src/bot/memory/memory_manager.py`): Handles context retrieval and message persistence
3. **Main Bot** (`src/bot/main.py`): Telegram bot setup and handlers
4. **ChromaDB Manager** (`src/bot/memory/chroma_manager.py`): Vector database for semantic search

## Configuration

Configuration is managed through:
1. Environment variables (`.env`)
2. Runtime configuration (`config/runtime_config.json`)
3. Config class (`src/config/config.py`)

Key configuration parameters:
- `llm_provider`: 'openai' or 'gemini'
- `model`: The LLM model to use
- `temperature`: Response creativity (0-1)
- `max_tokens`: Maximum tokens for context

## Common Issues

1. **Memory Divergence**: If ChromaDB and SQLite get out of sync, use `repair_memory.py`
2. **Context Issues**: If context retrieval seems broken, use `fix_memory.py`
3. **Token Usage**: Monitor token usage in `data/usage/` directory

## Development Workflow

1. Make changes to code
2. Run relevant tests
3. Test with the bot running
4. Monitor memory usage and performance