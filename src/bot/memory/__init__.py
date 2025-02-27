# memory/__init__.py
"""
Pacote de gerenciamento de memória do sistema.

Este pacote fornece funcionalidades para armazenamento e recuperação
de mensagens, documentos e contexto usando ChromaDB e SQLite.

Modules:
    memory_manager: Gerenciamento principal de memória e contexto
    document_manager: Gerenciamento de documentos e chunks de texto

Classes:
    MemoryManager: Gerenciador principal de memória
    DocumentManager: Gerenciador de documentos

Example:
    >>> from bot.memory import MemoryManager
    >>> memory = MemoryManager()
    >>> await memory.add_message(user_id=1, chat_id=1, content="Olá", role="user")
"""

import dotenv

dotenv.load_dotenv()

from .memory_manager import MemoryManager

__all__ = ['MemoryManager']
