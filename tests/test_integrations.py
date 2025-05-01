# test_integrations.py
import os
from dotenv import load_dotenv
import openai
from telegram import Bot
import asyncio
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
# from notion_client import Client
import sqlite3
import json

load_dotenv()

async def test_telegram():
    """
    Testa a conexão com a API do Telegram
    """
    try:
        bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
        bot_info = await bot.get_me()
        print(f"✅ Telegram: Conectado como {bot_info.first_name} (@{bot_info.username})")
        return True
    except Exception as e:
        print(f"❌ Telegram: Erro na conexão - {str(e)}")
        return False

def test_openai():
    """
    Testa a conexão com a API da OpenAI
    """
    try:
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Testa com uma mensagem simples
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Olá, teste de conexão"}
            ]
        )
        print("✅ OpenAI: Conexão estabelecida com sucesso")
        return True
    except Exception as e:
        print(f"❌ OpenAI: Erro na conexão - {str(e)}")
        return False

def test_google_sheets():
    """
    Testa a conexão com o Google Sheets
    """
    try:
        # Carrega as credenciais do arquivo JSON
        credentials_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
        credentials = service_account.Credentials.from_service_account_file(
            'C:\\Users\\danie\\OneDrive\\Área de Trabalho\\bot\\config\\turing-lyceum-435603-k1-1856236a07d0.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Cria o serviço
        service = build('sheets', 'v4', credentials=credentials)
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        
        # Tenta ler dados da planilha
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A1:A1'
        ).execute()
        
        print("✅ Google Sheets: Conexão estabelecida com sucesso")
        return True
    except Exception as e:
        print(f"❌ Google Sheets: Erro na conexão - {str(e)}")
        return False

def test_notion():
    """
    Testa a conexão com a API do Notion
    """
    try:
        notion = Client(auth=os.getenv('NOTION_TOKEN'))
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        # Tenta acessar o banco de dados
        notion.databases.query(database_id=database_id)
        
        print("✅ Notion: Conexão estabelecida com sucesso")
        return True
    except Exception as e:
        print(f"❌ Notion: Erro na conexão - {str(e)}")
        return False

def test_sqlite():
    """
    Testa a conexão com o SQLite e a criação do banco de dados
    """
    try:
        conn = sqlite3.connect('engenharia_bot.db')
        cursor = conn.cursor()
        
        # Testa criando uma tabela temporária
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_connection (
            id INTEGER PRIMARY KEY
        )
        ''')
        
        # Remove a tabela de teste
        cursor.execute('DROP TABLE test_connection')
        
        conn.close()
        print("✅ SQLite: Conexão e operações testadas com sucesso")
        return True
    except Exception as e:
        print(f"❌ SQLite: Erro na conexão - {str(e)}")
        return False

async def run_all_tests():
    """
    Executa todos os testes de integração
    """
    print("\n🔄 Iniciando testes de integração...\n")
    
    results = {
        "Telegram": await test_telegram(),
        "OpenAI": test_openai(),
        "Google Sheets": test_google_sheets(),
        "Notion": test_notion(),
        "SQLite": test_sqlite()
    }
    
    print("\n📊 Resumo dos testes:")
    for service, success in results.items():
        status = "✅ Passou" if success else "❌ Falhou"
        print(f"{service}: {status}")
    
    return all(results.values())

if __name__ == "__main__":
    asyncio.run(run_all_tests())