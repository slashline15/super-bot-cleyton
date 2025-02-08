# config/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Define o diretório base do projeto
BASE_DIR = Path(__file__).parent.parent.parent  # Um nível acima

class Config:
    # Configurações do LLM
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL_NAME = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
    SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')
    
    # Configurações de contexto
    CONTEXT_TIME_WINDOW = int(os.getenv('CONTEXT_TIME_WINDOW', 30))  # minutos
    MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', 20))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 20000))
    
    # Configurações do banco de dados
    DB_NAME = os.getenv('DB_NAME', 'engenharia_bot.db')
    
    # Configurações de logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    
    # Configurações do Google
    CREDENTIALS_DIR = BASE_DIR / "credentials"  # Novo caminho
    CLIENT_SECRETS_PATH = os.getenv("GOOGLE_CLIENT_SECRETS", str(CREDENTIALS_DIR / "client_secrets.json"))
    SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(CREDENTIALS_DIR / "service_account.json"))