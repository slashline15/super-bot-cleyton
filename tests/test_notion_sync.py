# tests/test_notion_sync.py

import unittest
from unittest.mock import patch, MagicMock
import logging
import sys
sys.path.append('.')
from src.bot.utils.notion_sync import NotionSync
from src.config.config import Config

# Configuração de log para os testes
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

test_token = Config.NOTION_TOKEN
test_database_id = Config.NOTION_DATABASE_ID

class TestNotionSync(unittest.TestCase):

    """
    Classe de testes para NotionSync
    """
    def setUp(self):
        """
        Configura os mocks antes de cada teste
        """
        self.notion_token = "test_token"
        self.database_id = "test_db_id"
        
        # Mock do Client do Notion
        self.client_patcher = patch('notion_client.Client')
        self.mock_client = self.client_patcher.start()
        
        # Configura os mocks dos métodos
        self.mock_client.return_value.databases.retrieve.return_value = {
            "properties": {}
        }
        self.mock_client.return_value.databases.update.return_value = True
        self.mock_client.return_value.pages.create.return_value = {"id": "test_page_id"}
        
        # Cria instância do NotionSync com o client mockado
        self.notion_sync = NotionSync(self.notion_token, self.database_id)

    def tearDown(self):
        """Limpa os mocks após cada teste"""
        self.client_patcher.stop()

    def test_sync_single_message(self):
        """Testa sincronização de mensagem única"""
        test_message = {
            "User ID": 123,
            "Role": "user",
            "Content": "Test message"
        }
        
        self.notion_sync.sync_message(test_message)
        
        # Verifica se create_page foi chamado com os argumentos corretos
        self.mock_client.return_value.pages.create.assert_called_once()
        
    def test_sync_multiple_messages(self):
        """Testa sincronização de múltiplas mensagens"""
        test_messages = [
            {"User ID": 123, "Role": "user", "Content": "Message 1"},
            {"User ID": 456, "Role": "assistant", "Content": "Message 2"}
        ]
        
        self.notion_sync.sync_all(test_messages)
        
        # Verifica se create_page foi chamado para cada mensagem
        self.assertEqual(
            self.mock_client.return_value.pages.create.call_count,
            len(test_messages)
        )

    def test_create_properties(self):
        """Testa criação de propriedades"""
        test_message = {
            "User ID": 123,
            "Role": "user",
            "Content": "Test"
        }
        
        # Simula que o database não tem propriedades
        self.mock_client.return_value.databases.retrieve.return_value = {
            "properties": {}
        }
        
        self.notion_sync.notion_client.create_properties(test_message)
        
        # Verifica se update foi chamado para criar as propriedades
        self.assertTrue(self.mock_client.return_value.databases.update.called)

if __name__ == '__main__':
    unittest.main()