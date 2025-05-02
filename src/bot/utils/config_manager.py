# src/bot/utils/config_manager.py
import json
import os
from pathlib import Path
import logging
from typing import Dict, Any, Optional, List, Union
import threading

logger = logging.getLogger("ConfigManager")

CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "runtime_config.json"

# Configurações que podem ser alteradas em tempo real
EDITABLE_CONFIGS = {
    "llm_provider": {
        "type": "select",
        "options": ["openai", "gemini"],
        "description": "Provedor de LLM a ser usado",
        "default": "openai"
    },
    "model": {
        "type": "text",
        "description": "Nome do modelo específico a ser usado",
        "default": "gpt-4o"
    },
    "temperature": {
        "type": "float",
        "min": 0.0,
        "max": 2.0,
        "description": "Criatividade nas respostas (0-2)",
        "default": 0.7
    },
    "max_tokens": {
        "type": "int",
        "min": 100,
        "max": 10000,
        "description": "Número máximo de tokens por resposta",
        "default": 4000
    },
    "custom_prompt": {
        "type": "text",
        "description": "Prompt de sistema personalizado",
        "default": None,
        "multiline": True
    },
    "debug_mode": {
        "type": "bool",
        "description": "Modo de depuração",
        "default": False
    }
}

class ConfigManager:
    """Gerencia configurações dinamicamente ajustáveis"""
    
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
        """Inicializa o gerenciador de configuração"""
        if self._initialized:
            return
            
        self._configs = {}
        self._initialized = True
        self._load_config()
        
        # Inicializa com valores padrão se não existirem
        for key, config in EDITABLE_CONFIGS.items():
            if key not in self._configs:
                self._configs[key] = config["default"]
        
        # Salva para garantir que temos um arquivo atualizado
        self._save_config()
        logger.info("ConfigManager inicializado")
    
    def _load_config(self):
        """Carrega configurações do arquivo"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    self._configs = json.load(f)
                logger.info(f"Configurações carregadas de {CONFIG_FILE}")
            else:
                logger.info("Arquivo de configuração não encontrado, usando valores padrão")
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
    
    def _save_config(self):
        """Salva configurações para o arquivo"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self._configs, f, indent=2)
            logger.info(f"Configurações salvas em {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Obtém uma configuração pelo nome"""
        return self._configs.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """Define uma configuração e salva"""
        if key not in EDITABLE_CONFIGS:
            logger.warning(f"Tentativa de definir configuração inválida: {key}")
            return False
            
        # Validação de tipo
        config_def = EDITABLE_CONFIGS[key]
        
        if config_def["type"] == "float":
            try:
                value = float(value)
                if "min" in config_def and value < config_def["min"]:
                    return False
                if "max" in config_def and value > config_def["max"]:
                    return False
            except ValueError:
                return False
        
        elif config_def["type"] == "int":
            try:
                value = int(value)
                if "min" in config_def and value < config_def["min"]:
                    return False
                if "max" in config_def and value > config_def["max"]:
                    return False
            except ValueError:
                return False
        
        elif config_def["type"] == "bool":
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "t", "yes", "y")
        
        elif config_def["type"] == "select" and value not in config_def["options"]:
            return False
            
        # Salva o valor
        self._configs[key] = value
        return self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Retorna todas as configurações"""
        return self._configs.copy()
    
    def reset(self, key: Optional[str] = None) -> bool:
        """Reseta uma ou todas as configurações para os valores padrão"""
        if key is None:
            # Reset all
            self._configs = {k: cfg["default"] for k, cfg in EDITABLE_CONFIGS.items()}
        elif key in EDITABLE_CONFIGS:
            # Reset specific key
            self._configs[key] = EDITABLE_CONFIGS[key]["default"]
        else:
            return False
            
        return self._save_config()
    
    def get_editable_configs(self) -> Dict[str, Dict]:
        """Retorna metadados sobre as configurações editáveis"""
        return EDITABLE_CONFIGS.copy()