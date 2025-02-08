# notion_sync.py
import logging
from bot.database.db_init import Database
from config.config import Config
from notion_client import Client
from bot.utils.data_utils import normalize_message  # Importe a função

logger = logging.getLogger('NotionSync')


class NotionClient:
    """
    Classe para gerenciar a conexão com o Notion.
    """

    def __init__(self, notion_token, database_id):
        self.notion_token = notion_token
        self.client = Client(auth=self.notion_token)
        self.database_id = database_id
        self.base_url = "https://api.notion.com/v1/pages"
        self.headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        logger.info(f"Inicializando NotionClient com database_id: {database_id}")

    def _create_notion_property(self, property_name: str, property_type: str):
      """
      Cria uma nova propriedade no Notion database.

      Args:
        property_name (str): Nome da propriedade.
        property_type (str): Tipo da propriedade ("title", "rich_text", "number", etc).

      Returns:
         bool: True se a propriedade foi criada com sucesso, False caso contrário.
      """
      try:
          logger.info(f"Criando propriedade: {property_name} ({property_type})")
          payload = {
              "properties": {
                  property_name: {
                      property_type: {}
                  }
              }
          }
          response = self.client.databases.update(
              database_id=self.database_id,
              **payload
          )
          if response:
            logger.debug(f"Propriedade {property_name} do tipo {property_type} criada com sucesso!")
            return True
          else:
              logger.error(f"Erro ao criar propriedade: {property_name}")
              return False
      except Exception as e:
          logger.error(f"Erro ao criar propriedade {property_name}: {e}", exc_info=True)
          return False

    def create_properties(self, message: dict):
        """
        Cria as propriedades de uma mensagem no Notion database caso elas não existam.

        Args:
            message (dict): Dicionário contendo os dados da mensagem (ex.: user_id, role, content, etc).
        """
        try:
            logger.info(f"Verificando propriedades do database: {self.database_id}")
            database_properties = self.client.databases.retrieve(database_id=self.database_id).get("properties")
            for property_name, value in message.items():
                if property_name not in database_properties:
                    if isinstance(value, (int, float)):
                        self._create_notion_property(property_name, "number")
                    elif isinstance(value, str):
                        self._create_notion_property(property_name, "rich_text")
            logger.debug("Propriedades verificadas e criadas com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao verificar propriedades do database: {e}", exc_info=True)


    def create_page(self, message: dict):
        """
        Cria uma nova página no database do Notion.

        Args:
            message (dict): Dicionário contendo os dados da mensagem (ex.: user_id, role, content, etc).
        """
        try:
            logger.info(f"Criando página no Notion com mensagem: {message}")
            properties = {}
            for key, value in message.items():
                if isinstance(value, int):
                    properties[key] = {"number": value}
                elif isinstance(value, str):
                   properties[key] = {"rich_text": [{"text": {"content": value}}]}
                else:
                    properties[key] = {"title": [{"text": {"content": value}}]}
            
            new_page = {
                "parent": {"database_id": self.database_id},
                "properties": properties
            }
            response = self.client.pages.create(**new_page)
            if response:
                logger.info(f"Página no Notion criada com sucesso: {response}")
            else:
                logger.error(f"Falha ao criar página no Notion com mensagem {message}")
        except Exception as e:
            logger.error(f"Falha ao criar página no Notion com mensagem {message}: {e}", exc_info=True)

class NotionSync:
    """
    Classe para sincronizar mensagens do SQLite para o database do Notion.
    """

    def __init__(self, notion_token, database_id):
        """
        Inicializa a instância do NotionSync.

        Args:
            notion_token (str): Token de acesso à API do Notion.
            database_id (str): ID do database no Notion onde as mensagens serão inseridas.
        """
        self.notion_client = NotionClient(notion_token, database_id)
        logger.info("Inicializando NotionSync")

    def sync_message(self, message: dict):
        """Sincroniza uma única mensagem."""
        try:
            self.notion_client.create_properties(message)
            self.notion_client.create_page(message)
            logger.info("Mensagem sincronizada com sucesso")
        except Exception as e:
            logger.error(f"Falha ao sincronizar mensagem: {message}: {e}", exc_info=True)

    def sync_all(self, messages: list):
        """Sincroniza todas as mensagens."""
        for msg in messages:
            try:
                self.sync_message(msg)
            except Exception as e:
                logger.error(f"Falha ao sincronizar mensagem {msg}: {e}")


def main():
    """
    Função principal para testar a sincronização com o Notion
    """
    database = Database()
    notion_token = Config.NOTION_TOKEN
    database_id = Config.NOTION_DATABASE_ID
    
    try:
        messages_raw = database.execute_query("SELECT user_id, role, content FROM messages")
        messages = [normalize_message(row) for row in messages_raw]
        notion_sync = NotionSync(notion_token=notion_token, database_id=database_id)
        notion_sync.sync_all(messages)
        logger.info("Sincronização concluída com sucesso")
    except Exception as e:
        logger.error(f"Erro durante sincronização: {e}", exc_info=True)

if __name__ == "__main__":
    main()