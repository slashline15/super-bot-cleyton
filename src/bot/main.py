# main.py
"""
main.py

Script principal para iniciar o bot do Telegram.

Este módulo realiza as seguintes ações:
- Carrega as variáveis de ambiente do arquivo .env.
- Configura o logging para depuração e monitoramento.
- Cria a aplicação do Telegram utilizando o token configurado.
- Adiciona handlers para processar mensagens de texto e voz (exceto comandos).
- Inicia o bot usando o método de polling para receber atualizações.
"""

import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from src.bot.handlers.telegram_llm_handler import telegram_llm_handler
import sys
from src.config.config import Config
from src.bot.google_auth_helper import GoogleAuthHelper
from src.bot.utils.log_config import setup_logging
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Carrega variáveis de ambiente
load_dotenv()

# Configuração do logging: define o formato e o nível de mensagens que serão exibidas
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = setup_logging()


    
def init_google_auth():
    # instanciar o helper
    auth_helper = GoogleAuthHelper()

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    try:
        # Para OAuth2 (acesso como usuário)
        oauth_creds = auth_helper.setup_oauth_credentials(
            scopes=SCOPES,
            project_name="turing-lyceum-435603-k1",
            client_secrets_file=Config.CLIENT_SECRETS_PATH
        )
        
        # OU para Service Account (acesso como serviço)
        service_creds = auth_helper.setup_service_account(
            project_name="turing-lyceum-435603-k1",
            service_account_file=Config.SERVICE_ACCOUNT_PATH
        )
        
        return oauth_creds  # ou service_creds
        
    except Exception as e:
        logging.error(f"Erro na autenticação: {e}")
        raise

# # Obtém as credenciais
# credentials = init_google_auth()

# # Exemplo de uso com Google Sheets
# from googleapiclient.discovery import build
# sheets_service = build('sheets', 'v4', credentials=credentials)

# # Exemplo de uso com Google Drive
# drive_service = build('drive', 'v3', credentials=credentials)


def main():
    """
    Função principal que configura e inicia o bot do Telegram.

    Passos realizados:
    1. Recupera o token do Telegram das variáveis de ambiente.
    2. Cria a aplicação do Telegram utilizando esse token.
    3. Adiciona um handler para processar mensagens de texto e voz, ignorando comandos.
    4. Inicia o polling para receber atualizações do Telegram.
    """
    # Obtém o token do Telegram da variável de ambiente
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    if not telegram_token:
        logger.error("Token do Telegram não encontrado.")
        return

    application = Application.builder().token(telegram_token).build()
    # # Handler para comando /start
    # application.add_handler(CommandHandler("start", telegram_llm_handler.handle_start))
    
    # # Handler para comando /help
    # application.add_handler(CommandHandler("help", telegram_llm_handler.handle_help))
    
    # # Handler para comando /limpar
    # application.add_handler(CommandHandler("limpar", telegram_llm_handler.handle_limpar))
    
    # # Handler para erros
    # application.add_error_handler(telegram_llm_handler.handle_error)
    # Handler para comando /memoria
    application.add_handler(CommandHandler("memoria", telegram_llm_handler.handle_memoria))
    
    # Handler para comando /lembrar
    application.add_handler(CommandHandler("lembrar", telegram_llm_handler.handle_lembrar))
    
    # Handler para envio dos logs
    application.add_handler(CommandHandler("logs", telegram_llm_handler.handle_logs))
    
    # Handler para mensagens regulares
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.VOICE) & ~filters.COMMAND, 
        telegram_llm_handler.handle_message
    ))

    print("🤖Bot iniciado!")
    print("❌Pressione Ctrl+C para parar.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logging.info("Bot iniciado!")

if __name__ == '__main__':
    main()