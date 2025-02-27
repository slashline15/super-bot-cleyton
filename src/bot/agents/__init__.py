# src\bot\agents\__init__.py
"""
Módulo de agentes de IA para o sistema financeiro.

Este pacote contém diferentes implementações de agentes de IA,
incluindo integrações com OpenAI GPT e Google Gemini.

Modules:
    llm_agent: Agente principal baseado em LLM para processamento de linguagem natural
    gemini: Subpacote com implementação do cliente Gemini

Example:
    >>> from bot.agents import LLMAgent
    >>> agent = LLMAgent()
    >>> response = await agent.process_message("Olá", user_id=1, chat_id=1)
"""

from .llm_agent import LLMAgent
from .gemini import GeminiClient, GeminiConfig

__all__ = ['LLMAgent', 'GeminiClient', 'GeminiConfig']
