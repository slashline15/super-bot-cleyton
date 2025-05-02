# src/bot/utils/token_tracker.py
import json
from pathlib import Path
import threading
import datetime
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("TokenTracker")

# Custos aproximados (por 1000 tokens)
TOKEN_COSTS = {
    "openai": {
        "gpt-4o": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015}
    },
    "gemini": {
        "gemini-1.5-pro": {"input": 0.0007, "output": 0.0028},
        "gemini-1.5-flash": {"input": 0.00014, "output": 0.00056}
    }
}

class TokenTracker:
    """Rastreia o uso de tokens e custos estimados"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton para garantir uma única instância"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Inicializa o rastreador de tokens"""
        if self._initialized:
            return
            
        self.data_dir = Path("data/usage")
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # Formato: YYYY-MM-DD.json
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.current_file = self.data_dir / f"{today}.json"
        
        self.usage = {
            "total_tokens": {"input": 0, "output": 0},
            "total_cost": 0.0,
            "providers": {},
            "sessions": []
        }
        
        self._load_usage()
        self._initialized = True
        
        # Cria uma nova sessão
        self._session_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.usage["sessions"].append({
            "id": self._session_id,
            "start_time": datetime.datetime.now().isoformat(),
            "tokens": {"input": 0, "output": 0},
            "cost": 0.0,
            "requests": []
        })
        
        logger.info("TokenTracker inicializado")
    
    def _load_usage(self):
        """Carrega dados de uso do arquivo atual"""
        try:
            if self.current_file.exists():
                with open(self.current_file, "r") as f:
                    self.usage = json.load(f)
                logger.info(f"Dados de uso carregados de {self.current_file}")
        except Exception as e:
            logger.error(f"Erro ao carregar dados de uso: {e}")
    
    def _save_usage(self):
        """Salva dados de uso para o arquivo atual"""
        try:
            with open(self.current_file, "w") as f:
                json.dump(self.usage, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar dados de uso: {e}")
    
    def track(self, provider: str, model: str, input_tokens: int, output_tokens: int, query: str):
        """Rastreia uso de tokens e calcula custos"""
        with self._lock:
            # Atualiza totais
            self.usage["total_tokens"]["input"] += input_tokens
            self.usage["total_tokens"]["output"] += output_tokens
            
            # Atualiza por provedor
            if provider not in self.usage["providers"]:
                self.usage["providers"][provider] = {
                    "total_tokens": {"input": 0, "output": 0},
                    "total_cost": 0.0,
                    "models": {}
                }
            
            provider_data = self.usage["providers"][provider]
            provider_data["total_tokens"]["input"] += input_tokens
            provider_data["total_tokens"]["output"] += output_tokens
            
            # Atualiza por modelo
            if model not in provider_data["models"]:
                provider_data["models"][model] = {
                    "total_tokens": {"input": 0, "output": 0},
                    "total_cost": 0.0
                }
            
            model_data = provider_data["models"][model]
            model_data["total_tokens"]["input"] += input_tokens
            model_data["total_tokens"]["output"] += output_tokens
            
            # Calcula custos
            input_cost = 0
            output_cost = 0
            
            try:
                if provider in TOKEN_COSTS and model in TOKEN_COSTS[provider]:
                    rates = TOKEN_COSTS[provider][model]
                    input_cost = (input_tokens / 1000) * rates["input"]
                    output_cost = (output_tokens / 1000) * rates["output"]
                else:
                    # Fallback para estimativa genérica
                    input_cost = (input_tokens / 1000) * 0.001
                    output_cost = (output_tokens / 1000) * 0.002
            except Exception as e:
                logger.error(f"Erro ao calcular custos: {e}")
            
            total_cost = input_cost + output_cost
            
            # Atualiza custos
            self.usage["total_cost"] += total_cost
            provider_data["total_cost"] += total_cost
            model_data["total_cost"] += total_cost
            
            # Atualiza sessão atual
            current_session = next(s for s in self.usage["sessions"] if s["id"] == self._session_id)
            current_session["tokens"]["input"] += input_tokens
            current_session["tokens"]["output"] += output_tokens
            current_session["cost"] += total_cost
            
            # Adiciona o request
            current_session["requests"].append({
                "timestamp": datetime.datetime.now().isoformat(),
                "query": query[:100] + "..." if len(query) > 100 else query,
                "tokens": {"input": input_tokens, "output": output_tokens},
                "cost": total_cost
            })
            
            # Salva os dados
            self._save_usage()
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": total_cost
            }
    
    def get_daily_stats(self) -> Dict:
        """Retorna estatísticas do dia atual"""
        return {
            "total_tokens": self.usage["total_tokens"]["input"] + self.usage["total_tokens"]["output"],
            "input_tokens": self.usage["total_tokens"]["input"],
            "output_tokens": self.usage["total_tokens"]["output"],
            "total_cost": self.usage["total_cost"],
            "providers": self.usage["providers"]
        }
    
    def get_session_stats(self, session_id: Optional[str] = None) -> Dict:
        """Retorna estatísticas da sessão atual ou específica"""
        if session_id is None:
            session_id = self._session_id
            
        try:
            session = next(s for s in self.usage["sessions"] if s["id"] == session_id)
            return {
                "id": session["id"],
                "start_time": session["start_time"],
                "total_tokens": session["tokens"]["input"] + session["tokens"]["output"],
                "input_tokens": session["tokens"]["input"],
                "output_tokens": session["tokens"]["output"],
                "cost": session["cost"],
                "requests": len(session["requests"])
            }
        except StopIteration:
            return {}