# src/bot/agents/gemini/__init__.py
"""
Pacote Gemini para processamento de linguagem natural.

Este pacote fornece uma interface completa para interação com o modelo Gemini,
incluindo configuração, gerenciamento de sessões e processamento de documentos.

Modules:
    client: Implementação do cliente Gemini
    config: Configurações e parâmetros do modelo

Classes:
    GeminiClient: Cliente principal para interação com o modelo
    GeminiConfig: Configurações e parâmetros do modelo

Example:
    >>> from bot.agents.gemini import GeminiClient, GeminiConfig
    >>> config = GeminiConfig(temperature=0.7)
    >>> client = GeminiClient(config=config)
"""

from .config import GeminiConfig
from .client import GeminiClient

__all__ = ['GeminiClient', 'GeminiConfig']