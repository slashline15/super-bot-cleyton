# src/bot/agents/gemini/config.py
"""
Configurações para o cliente Gemini.

Este módulo define as configurações disponíveis para personalizar o comportamento
do cliente Gemini, incluindo parâmetros de geração de texto e formatação de resposta.

Example:
    >>> from src.bot.agents.gemini import GeminiConfig
    >>> config = GeminiConfig(temperature=0.7)
    >>> print(config.to_dict())
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class GeminiConfig:
    """
    Classe para gerenciar a configuração do cliente Gemini.

    Esta classe utiliza dataclasses para definir e validar os parâmetros
    de configuração do modelo Gemini.

    Args:
        temperature (float): Controla a aleatoriedade das respostas (0.0 a 1.0)
        top_p (float): Controla a diversidade do texto (0.0 a 1.0)
        top_k (int): Número de tokens mais prováveis a considerar
        max_output_tokens (int): Número máximo de tokens na resposta
        response_mime_type (str): Tipo MIME da resposta

    Attributes:
        temperature: Temperatura para geração de texto
        top_p: Valor de top-p sampling
        top_k: Valor de top-k sampling
        max_output_tokens: Limite máximo de tokens
        response_mime_type: Formato da resposta

    Example:
        >>> config = GeminiConfig(temperature=0.8, top_p=0.9)
        >>> print(f"Temperatura: {config.temperature}")
    """
    
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 40
    max_output_tokens: int = 8192
    response_mime_type: str = "text/plain"
    
    def __post_init__(self):
        """Valida os valores após a inicialização."""
        self._validate_temperature()
        self._validate_top_p()
        self._validate_top_k()
        self._validate_max_output_tokens()
    
    def _validate_temperature(self):
        """Valida o valor da temperature."""
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("Temperature deve estar entre 0.0 e 1.0")
    
    def _validate_top_p(self):
        """Valida o valor do top_p."""
        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError("Top_p deve estar entre 0.0 e 1.0")
    
    def _validate_top_k(self):
        """Valida o valor do top_k."""
        if self.top_k < 1:
            raise ValueError("Top_k deve ser maior que 0")
    
    def _validate_max_output_tokens(self):
        """Valida o valor do max_output_tokens."""
        if self.max_output_tokens < 1:
            raise ValueError("Max_output_tokens deve ser maior que 0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte a configuração para um dicionário."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_output_tokens,
            "response_mime_type": self.response_mime_type
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'GeminiConfig':
        """
        Cria uma instância de GeminiConfig a partir de um dicionário.
        
        Args:
            config_dict: Dicionário com os valores de configuração
            
        Returns:
            GeminiConfig: Nova instância configurada
        """
        return cls(**config_dict)