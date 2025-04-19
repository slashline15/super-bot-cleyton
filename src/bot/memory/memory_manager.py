# memory/memory_manager.py
import chromadb
import logging
from datetime import datetime, timedelta
from src.config.config import Config
from src.bot.database.db_init import Database

logger = logging.getLogger('MemoryManager')

class MemoryManager:
    """
    Gerenciador de memória usando ChromaDB e SQLite.

    Esta classe gerencia o armazenamento e recuperação de mensagens,
    mantendo contexto e permitindo busca semântica eficiente.

    Args:
        persist_directory (str): Diretório para persistência do ChromaDB

    Attributes:
        client: Cliente ChromaDB configurado
        messages_collection: Coleção de mensagens no ChromaDB
        db: Conexão com banco SQLite

    Example:
        >>> memory = MemoryManager("./data/chroma")
        >>> stats = await memory.get_category_stats(1, 1)
    """
    def __init__(self, persist_directory="./chroma_db"):
        """
        Inicializa o gerenciador de memória usando ChromaDB e SQLite
        
        Args:
            persist_directory (str): Diretório onde o ChromaDB salvará os dados
        """
        logger.info(f"Inicializando MemoryManager com diretório: {persist_directory}")
        
        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.messages_collection = self.client.get_or_create_collection(
                name="messages",
                metadata={"description": "Histórico de mensagens do chatbot"}
            )
            self.db = Database()
            logger.info("MemoryManager inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar MemoryManager: {str(e)}", exc_info=True)
            raise

    async def get_relevant_context(self, 
                                 query: str, 
                                 user_id: int, 
                                 chat_id: int, 
                                 limit: int = 5, 
                                 time_window: int = 60):
        """
        Busca contexto relevante combinando ChromaDB e SQLite
        
        Args:
            query (str): Texto para buscar similaridade
            user_id (int): ID do usuário
            chat_id (int): ID do chat
            limit (int): Número máximo de resultados
            time_window (int): Janela de tempo em minutos
            
        Returns:
            list: Lista de mensagens relevantes
        """
        try:
            # ChromaDB precisa de um operador $eq para comparações
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": str(user_id)}},
                    {"chat_id": {"$eq": str(chat_id)}}
                ]
            }
            
            # Busca por similaridade no ChromaDB
            results = self.messages_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )
            
            if not results['ids']:
                logger.debug("Nenhum resultado encontrado no ChromaDB")
                return []
            
            # Recupera mensagens completas do SQLite
            embedding_ids = results['ids'][0]  # Pega a primeira lista de IDs
            
            # Prepara a query SQL
            placeholders = ','.join('?' * len(embedding_ids))
            query_sql = f"""
                SELECT * FROM messages 
                WHERE embedding_id IN ({placeholders})
                AND timestamp >= datetime('now', '-' || ? || ' minutes')
                ORDER BY importance DESC, timestamp DESC
            """
            
            # Prepara os parâmetros
            params = [*embedding_ids, time_window]
            
            # Debug log
            logger.debug(f"Executing SQL: {query_sql}")
            logger.debug(f"With params: {params}")
            
            # Executa a query
            messages = self.db.execute_query(query_sql, tuple(params))
            
            logger.debug(f"Contexto recuperado: {len(messages)} mensagens")
            return messages
            
        except Exception as e:
            logger.error(f"Erro ao buscar contexto: {str(e)}", exc_info=True)
            return []

    async def add_message(self, user_id: int, chat_id: int, content: str, role: str):
        """
        Adiciona uma mensagem à memória (ChromaDB e SQLite)
        
        Args:
            user_id (int): ID do usuário
            chat_id (int): ID do chat
            content (str): Conteúdo da mensagem
            role (str): Papel da mensagem (user/assistant)
        """
        try:
            category, importance = self._categorize_message(content)
            
            # Adiciona ao ChromaDB
            embedding_id = f"msg_{user_id}_{datetime.now().timestamp()}"
            self.messages_collection.add(
                documents=[content],
                metadatas=[{
                    "user_id": str(user_id),  # Convertido para string
                    "chat_id": str(chat_id),  # Convertido para string
                    "role": role,
                    "category": category,
                    "timestamp": datetime.now().isoformat()
                }],
                ids=[embedding_id]
            )
            
            # Adiciona ao SQLite
            self.db.execute_query(
                """
                INSERT INTO messages 
                (user_id, chat_id, role, content, category, importance, embedding_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, chat_id, role, content, category, importance, embedding_id)
            )
            
            logger.debug(f"Mensagem adicionada com ID: {embedding_id}")
            
        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}", exc_info=True)
            raise

    def _categorize_message(self, content: str) -> tuple:
        """Categoriza uma mensagem"""
        importance = 3  # importância padrão
        
        keywords = {
            'diario_obra': ['obra', 'construção', 'rdo', 'diário'],
            'financeiro': ['pagamento', 'custo', 'orçamento', 'valor'],
            'cronograma': ['prazo', 'agenda', 'data', 'cronograma'],
            'tarefas': ['tarefa', 'pendência', 'atividade', 'fazer']
        }
        
        content_lower = content.lower()
        for category, words in keywords.items():
            if any(word in content_lower for word in words):
                return category, importance
                
        return 'geral', importance

    async def get_category_stats(self, user_id: int, chat_id: int):
        """
        Retorna estatísticas por categoria
        
        Args:
            user_id (int): ID do usuário
            chat_id (int): ID do chat
            
        Returns:
            dict: Estatísticas por categoria
        """
        try:
            logger.debug(f"Buscando estatísticas para user_id={user_id}, chat_id={chat_id}")
            
            # Primeiro verifica se existem mensagens
            count_check = self.db.execute_query(
                """
                SELECT COUNT(*) as count 
                FROM messages 
                WHERE user_id = ? AND chat_id = ?
                """,
                (user_id, chat_id)
            )
            
            total_messages = count_check[0]['count'] if count_check else 0
            
            if total_messages == 0:
                logger.info(f"Nenhuma mensagem encontrada para user_id={user_id}, chat_id={chat_id}")
                return {'categories': [], 'total_messages': 0}
            
            # Busca estatísticas
            stats = self.db.execute_query(
                """
                SELECT 
                    category,
                    COUNT(*) as total,
                    ROUND(AVG(CAST(importance as FLOAT)), 1) as avg_importance,
                    MAX(timestamp) as last_message
                FROM messages
                WHERE user_id = ? AND chat_id = ?
                GROUP BY category
                ORDER BY total DESC
                """,
                (user_id, chat_id)
            )
            
            logger.debug(f"Estatísticas encontradas: {stats}")
            return {'categories': stats, 'total_messages': total_messages}
            
        except Exception as e:
            logger.error(f"Erro ao buscar estatísticas: {str(e)}", exc_info=True)
            return {'categories': [], 'total_messages': 0}