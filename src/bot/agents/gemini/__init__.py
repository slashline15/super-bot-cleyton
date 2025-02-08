# src/bot/agents/gemini/__init__.py
"""
Módulo para interação com o modelo Gemini.
"""

from .config import GeminiConfig
from .client import GeminiClient

__all__ = ['GeminiClient', 'GeminiConfig']