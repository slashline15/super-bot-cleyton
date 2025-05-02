# src/bot/utils/log_config.py
import logging
import os
from datetime import datetime
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme
import dotenv
import os

# Define o diretório de logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Define o arquivo de log atual
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"bot_session_{current_time}.log"

# Rich Theme customizado com cores por categoria
custom_theme = Theme({
    "info": "green",
    "warning": "yellow",
    "error": "bold red",
    "critical": "bold white on red",
    "message": "cyan",
    "api": "magenta",
    "db": "blue",
    "memory": "dark_orange",
    "auth": "purple"
})

console = Console(theme=custom_theme)

class CustomFilter(logging.Filter):
    """Filtra mensagens de ping de atualização."""
    
    def filter(self, record):
        # Se for um ping de GetUpdates sem novas mensagens, filtra
        if "getUpdates" in getattr(record, 'msg', '') and "HTTP/1.1 200 OK" in getattr(record, 'msg', ''):
            return False
        return True

class CustomFormatter(logging.Formatter):
    """Formato personalizado que adiciona categoria aos logs."""
    
    FORMATS = {
        logging.DEBUG: "%(asctime)s - [DEBUG] %(message)s",
        logging.INFO: "%(asctime)s - [%(category)s] %(message)s",
        logging.WARNING: "%(asctime)s - [WARN] %(message)s",
        logging.ERROR: "%(asctime)s - [ERROR] %(message)s",
        logging.CRITICAL: "%(asctime)s - [CRITICAL] %(message)s"
    }
    
    def format(self, record):
        # Adiciona categoria se não existir
        if not hasattr(record, 'category'):
            record.category = 'INFO'
            
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging():
    """Configura o sistema de logging com cores e categorias."""
    
    # Remove handlers anteriores
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler para o terminal com rich
    console_handler = RichHandler(console=console, rich_tracebacks=True)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(CustomFilter())
    
    # Handler para arquivo
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(CustomFormatter())
    
    # Configura o logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Registra início da sessão
    logging.info(f"Sessão iniciada: {current_time}", extra={"category": "SYSTEM"})
    logging.info(f"Log sendo salvo em: {LOG_FILE}", extra={"category": "SYSTEM"})

def get_logger(name, category=None):
    """Obtém um logger com categoria personalizada."""
    logger = logging.getLogger(name)
    
    # Define a categoria padrão baseada no nome se não fornecida
    if category is None:
        if "db" in name.lower():
            category = "DB"
        elif "memory" in name.lower():
            category = "MEMORY"
        elif "api" in name.lower() or "http" in name.lower():
            category = "API"
        elif "auth" in name.lower():
            category = "AUTH"
        elif "handler" in name.lower() or "telegram" in name.lower():
            category = "MSG"
        else:
            category = "SYSTEM"
    
    # Customiza o logger para incluir a categoria
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.category = category
        return record
    
    logging.setLogRecordFactory(record_factory)
    return logger

def export_log_summary():
    """Exporta um resumo do log atual, pronto para enviar no Telegram."""
    
    # Lê o log completo
    with open(LOG_FILE, "r") as f:
        log_lines = f.readlines()
    
    # Filtra os pings e outros logs menos importantes
    filtered_lines = []
    for line in log_lines:
        if "getUpdates" in line and "HTTP/1.1 200 OK" in line:
            continue
        if "[SYSTEM]" in line and "Log sendo salvo" in line:
            continue
        filtered_lines.append(line)
    
    # Cria um arquivo resumido
    summary_file = LOG_DIR / f"summary_{current_time}.txt"
    with open(summary_file, "w") as f:
        f.write("".join(filtered_lines))
    
    return str(summary_file)