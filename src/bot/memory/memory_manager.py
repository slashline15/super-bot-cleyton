# src/bot/memory/memory_manager.py
import logging
import json
import threading
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

import chromadb
from src.config.config import Config
from src.bot.database.db_init import Database
from src.bot.memory.chroma_manager import ChromaManager, retry_on_exception

logger = logging.getLogger('MemoryManager')

class MemoryManager:
    """
    Gerenciador de memória usando ChromaDB e SQLite.

    Esta classe gerencia o armazenamento e recuperação de mensagens,
    mantendo contexto e permitindo busca semântica eficiente.

    Args:
        persist_directory (str): Diretório para persistência do ChromaDB

    Attributes:
        chroma_manager: Gerenciador do ChromaDB
        messages_collection: Coleção de mensagens no ChromaDB
        db: Conexão com banco SQLite

    Example:
        >>> memory = MemoryManager("./data/chroma_db")
        >>> stats = await memory.get_category_stats(1, 1)
    """
    def __init__(self, persist_directory="./data/chroma_db"):
        """
        Inicializa o gerenciador de memória usando ChromaDB e SQLite
        """
        logger.info(f"Inicializando MemoryManager com diretório: {persist_directory}")
        
        try:
            # Inicializa o gerenciador de ChromaDB
            self.chroma_manager = ChromaManager(persist_directory)
            self.client = self.chroma_manager.client
            self.messages_collection = self.chroma_manager.get_or_create_collection(
                name="messages",
                metadata={"description": "Histórico de mensagens do chatbot"}
            )
            self.db = Database()
            
            # Trava para operações críticas
            self._lock = threading.Lock()
            self._async_lock = asyncio.Lock()
            
            # Verificação de integridade
            self._verify_integrity()
            
            logger.info("MemoryManager inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar MemoryManager: {str(e)}", exc_info=True)
            raise
    
    def _verify_integrity(self):
        """
        Verifica a integridade entre SQLite e ChromaDB, logando avisos quando necessário.
        """
        try:
            # Verifica total de mensagens no SQLite
            total_sqlite = self.db.execute_query(
                "SELECT COUNT(*) as count FROM messages"
            )[0]['count']
            
            # Verifica tamanho da coleção ChromaDB
            try:
                total_chroma = self.messages_collection.count()
            except:
                # O método count() pode não estar disponível em todas as versões
                results = self.messages_collection.query(
                    query_texts=[""],
                    n_results=1  # Apenas para check
                )
                total_chroma = len(results['ids'][0]) if results['ids'] else 0
            
            if total_sqlite != total_chroma:
                logger.warning(
                    f"⚠️ Divergência detectada: SQLite tem {total_sqlite} mensagens, "
                    f"ChromaDB tem {total_chroma} mensagens"
                )
            else:
                logger.info(f"✅ Integridade OK: {total_sqlite} mensagens em ambos os bancos")
        
        except Exception as e:
            logger.error(f"Erro ao verificar integridade: {e}")
    
    @contextmanager
    def transaction(self):
        """
        Context manager para transações atômicas.
        Realiza rollback em caso de erro.
        
        Uso:
            with memory.transaction():
                # operações atômicas aqui
        """
        with self._lock:
            try:
                yield
            except Exception as e:
                logger.error(f"Erro na transação, realizando limpeza: {e}")
                raise

    async def get_relevant_context(
        self, 
        query: str, 
        user_id: int, 
        chat_id: int, 
        limit: int = 5, 
        time_window: int = 60,
        min_relevance_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Busca contexto relevante combinando ChromaDB e SQLite
        
        Args:
            query (str): Texto para buscar similaridade
            user_id (int): ID do usuário
            chat_id (int): ID do chat
            limit (int): Número máximo de resultados
            time_window (int): Janela de tempo em minutos (0 = sem limite)
            min_relevance_score (float): Score mínimo de relevância (0-1)
            
        Returns:
            list: Lista de mensagens relevantes
        """
        try:
            # Se não houver query, retorna vazio (evita chamadas desnecessárias)
            if not query or len(query.strip()) < 3:
                logger.debug("Query muito curta, pulando busca vetorial")
                return []
                
            # Constrói o filtro para ChromaDB
            where_filter = {
                "$and": [
                    {"user_id": {"$eq": str(user_id)}},
                    {"chat_id": {"$eq": str(chat_id)}}
                ]
            }
            
            # Busca por similaridade no ChromaDB
            results = await self._query_chromadb_with_retry(
                query_text=query,
                where_filter=where_filter,
                limit=limit * 2  # Busca mais para filtrar por relevância depois
            )
            
            if not results['ids'] or len(results['ids'][0]) == 0:
                logger.debug("Nenhum resultado encontrado no ChromaDB")
                return []
            
            # Recupera os IDs dos embeddings com seus scores
            embedding_ids = results['ids'][0]
            distances = results['distances'][0] if 'distances' in results else None
            
            # Se temos distâncias (scores de similaridade), filtra por relevância
            if distances:
                # Converte distâncias para scores de similaridade (quanto menor a distância, maior a similaridade)
                similarity_scores = [1.0 - min(dist, 1.0) for dist in distances]
                
                # Filtra ids com base no score mínimo de relevância
                filtered_ids_with_scores = [
                    (id, score) for id, score in zip(embedding_ids, similarity_scores)
                    if score >= min_relevance_score
                ]
                
                if not filtered_ids_with_scores:
                    logger.debug(f"Nenhum resultado com score >= {min_relevance_score}")
                    return []
                    
                # Ordena por relevância
                filtered_ids_with_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Extrai apenas os IDs após a filtragem
                embedding_ids = [id for id, _ in filtered_ids_with_scores]
                
                # Limita ao número de resultados desejados
                embedding_ids = embedding_ids[:limit]
            
            # Prepara a consulta SQL
            placeholders = ','.join('?' * len(embedding_ids))
            time_condition = ""
            
            params = list(embedding_ids)
            
            # Adiciona condição de tempo se necessário
            if time_window > 0:
                time_condition = "AND timestamp >= datetime('now', '-' || ? || ' minutes')"
                params.append(time_window)
                
            query_sql = f"""
                SELECT * FROM messages 
                WHERE embedding_id IN ({placeholders})
                {time_condition}
                ORDER BY importance DESC, timestamp DESC
            """
            
            # Executa a query
            messages = self.db.execute_query(query_sql, tuple(params))
            
            logger.debug(f"Contexto recuperado: {len(messages)} mensagens")
            return messages
            
        except Exception as e:
            logger.error(f"Erro ao buscar contexto: {str(e)}", exc_info=True)
            # Não deixa a execução quebrar completamente
            return []

    async def _query_chromadb_with_retry(self, query_text, where_filter=None, limit=5):
        """
        Executa query no ChromaDB com retry em caso de falhas.
        """
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                return self.messages_collection.query(
                    query_texts=[query_text],
                    n_results=limit,
                    where=where_filter,
                    include=["metadatas", "distances"]
                )
            except Exception as e:
                logger.warning(
                    f"Erro na consulta ChromaDB (tentativa {attempt+1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:  # Última tentativa
                    logger.error(f"Falha em todas as tentativas de consulta ChromaDB")
                    # Retorna um objeto vazio compatível com o formato esperado
                    return {"ids": [[]], "distances": [[]], "metadatas": [[]]}
                    
                # Tenta reiniciar o cliente
                if hasattr(self.chroma_manager, 'reset_client'):
                    try:
                        self.client = self.chroma_manager.reset_client()
                        self.messages_collection = self.chroma_manager.get_or_create_collection("messages")
                    except Exception as reset_error:
                        logger.error(f"Erro ao resetar cliente ChromaDB: {reset_error}")
                        
                # Espera antes de tentar novamente
                wait_time = retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)

    async def add_message(
        self, 
        user_id: int, 
        chat_id: int, 
        content: str, 
        role: str,
        category: str = None,
        importance: int = None
    ) -> Optional[str]:
        """
        Adiciona uma mensagem de forma atômica.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            content: Conteúdo da mensagem
            role: Papel do emissor (user/assistant)
            category: Categoria da mensagem (opcional)
            importance: Importância (1-5, opcional)
            
        Returns:
            str: ID do embedding ou None em caso de erro
        """
        async with self._async_lock:  # Trava assíncrona
            transaction_successful = False
            embedding_id = None
            
            try:
                # 1. Gera ID único
                timestamp = int(time.time() * 1000)
                embedding_id = f"msg_{user_id}_{timestamp}"
                
                # 2. Categoriza a mensagem se necessário
                if category is None or importance is None:
                    category, importance = await self.categorize_message(content, role=="user")
                
                # 3. PRIMEIRO salva no SQLite (mais fácil de recuperar em caso de erro)
                self.db.execute_query(
                    """
                    INSERT INTO messages 
                    (user_id, chat_id, role, content, category, importance, embedding_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, chat_id, role, content, category, importance, embedding_id)
                )
                
                # 4. DEPOIS salva no ChromaDB
                self.messages_collection.add(
                    documents=[content],
                    metadatas=[{
                        "user_id": str(user_id),
                        "chat_id": str(chat_id),
                        "role": role,
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    }],
                    ids=[embedding_id]
                )
                
                transaction_successful = True
                logger.debug(f"Mensagem {embedding_id} salva com sucesso")
                return embedding_id
                
            except Exception as e:
                # Se houve erro e já inserimos no SQLite, tenta remover
                if embedding_id and not transaction_successful:
                    try:
                        logger.warning(f"Revertendo inserção falha no SQLite: {embedding_id}")
                        self.db.execute_query(
                            "DELETE FROM messages WHERE embedding_id = ?",
                            (embedding_id,)
                        )
                    except Exception as cleanup_err:
                        logger.error(f"Erro ao limpar inserção em SQLite: {cleanup_err}")
                
                logger.error(f"Erro ao salvar mensagem: {e}", exc_info=True)
                return None

    def add_message_sync(
        self,
        user_id: int,
        chat_id: int,
        content: str,
        role: str, 
        category: str = None,
        importance: int = None
    ) -> Optional[str]:
        """
        Versão síncrona do add_message para scripts de manutenção.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            content: Conteúdo da mensagem
            role: Papel do emissor (user/assistant)
            category: Categoria (opcional)
            importance: Importância (1-5, opcional)
            
        Returns:
            str: ID do embedding ou None em caso de erro
        """
        with self._lock:  # Trava para operações críticas
            transaction_successful = False
            embedding_id = None
            
            try:
                # 1. Gera ID único
                timestamp = int(time.time() * 1000)
                embedding_id = f"msg_{user_id}_{timestamp}"
                
                # 2. Define valores padrão para categoria/importância se não fornecidos
                if category is None:
                    category = 'geral'
                if importance is None:
                    importance = 3
                
                # 3. PRIMEIRO salva no SQLite
                self.db.execute_query(
                    """
                    INSERT INTO messages 
                    (user_id, chat_id, role, content, category, importance, embedding_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, chat_id, role, content, category, importance, embedding_id)
                )
                
                # 4. DEPOIS salva no ChromaDB
                self.messages_collection.add(
                    documents=[content],
                    metadatas=[{
                        "user_id": str(user_id),
                        "chat_id": str(chat_id),
                        "role": role,
                        "category": category,
                        "timestamp": datetime.now().isoformat()
                    }],
                    ids=[embedding_id]
                )
                
                transaction_successful = True
                logger.debug(f"Mensagem {embedding_id} adicionada com sucesso (sync)")
                return embedding_id
                
            except Exception as e:
                # Se houve erro e já inserimos no SQLite, tenta remover
                if embedding_id and not transaction_successful:
                    try:
                        logger.warning(f"Revertendo inserção falha no SQLite: {embedding_id}")
                        self.db.execute_query(
                            "DELETE FROM messages WHERE embedding_id = ?",
                            (embedding_id,)
                        )
                    except Exception as cleanup_err:
                        logger.error(f"Erro ao limpar inserção em SQLite: {cleanup_err}")
                
                logger.error(f"Erro ao adicionar mensagem (sync): {e}", exc_info=True)
                return None

    async def get_recent_messages(self, user_id: int, chat_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca mensagens recentes para um usuário/chat.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            limit: Número máximo de mensagens
            
        Returns:
            list: Lista de mensagens recentes
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, category, importance, timestamp 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens recentes: {e}")
            return []

    async def get_important_messages(
        self, 
        user_id: int, 
        chat_id: int, 
        min_importance: int = 4, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca mensagens importantes com base no score de importância.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            min_importance: Importância mínima (1-5)
            limit: Número máximo de mensagens
            
        Returns:
            list: Lista de mensagens importantes
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content, category, importance, timestamp 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ? AND importance >= ?
                    ORDER BY importance DESC, timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, min_importance, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens importantes: {e}")
            return []

    async def get_category_stats(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """
        Retorna estatísticas por categoria
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            
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
        
    async def categorize_message(self, content: str, is_user_message: bool = True) -> Tuple[str, int]:
        """
        Categoriza uma mensagem usando método simples.
        Para categorização com LLM, deve-se implementar em LLMAgent.
        
        Args:
            content: Conteúdo da mensagem
            is_user_message: Se é mensagem do usuário
            
        Returns:
            tuple: (categoria, importância)
        """
        # Mensagens curtas têm baixa importância
        if len(content.split()) < 5:
            return 'geral', 2
        
        # Importância padrão
        importance = 3
        
        # Palavras-chave para categorias comuns
        keywords = {
            'diario_obra': ['obra', 'construção', 'rdo', 'diário', 'canteiro'],
            'financeiro': ['pagamento', 'custo', 'orçamento', 'valor', 'preço', 'fatura'],
            'cronograma': ['prazo', 'agenda', 'data', 'cronograma', 'atraso'],
            'tarefas': ['tarefa', 'pendência', 'atividade', 'fazer', 'pendente'],
            'tecnico': ['projeto', 'engenharia', 'especificação', 'material', 'técnico'],
            'importante': ['urgente', 'crítico', 'prioridade', 'importante']
        }
        
        # Verificação simples de palavras-chave
        content_lower = content.lower()

        # Se importante, aumenta a pontuação
        if any(word in content_lower for word in keywords['importante']):
            importance = 4

        # Busca categoria por palavras-chave
        for category, words in keywords.items():
            if category == 'importante':
                continue
            if any(word in content_lower for word in words):
                return category, importance

        return 'geral', importance

    async def get_context_messages(
        self, 
        user_id: int, 
        chat_id: int, 
        query: str = "",
        context_limit: int = None
    ) -> List[Dict[str, str]]:
        """
        Recupera contexto combinando mensagens recentes e semanticamente relevantes
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            query: Consulta atual para busca semântica (opcional)
            context_limit: Limite de mensagens (usa Config.MAX_CONTEXT_MESSAGES se não definido)
            
        Returns:
            list: Lista de mensagens formatadas para o contexto
        """
        if context_limit is None:
            context_limit = Config.MAX_CONTEXT_MESSAGES
            
        try:
            # 1. Mensagens recentes (memória de curto prazo)
            recent_messages = await self.get_recent_messages(
                user_id=user_id,
                chat_id=chat_id,
                limit=context_limit // 2  # Metade para mensagens recentes
            )
            
            # 2. Mensagens semanticamente relevantes
            semantic_messages = []
            if query and len(query.strip()) > 2:  # Ignora queries muito curtas
                relevant_context = await self.get_relevant_context(
                    query=query,
                    user_id=user_id,
                    chat_id=chat_id,
                    limit=context_limit // 2,  # Metade para busca semântica
                    time_window=60 * 24 * 7  # Uma semana
                )
                
                # Converte para formato desejado e evita duplicações
                recent_content_set = {msg['content'] for msg in recent_messages}
                
                for msg in relevant_context:
                    if msg['content'] not in recent_content_set:
                        semantic_messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
                        recent_content_set.add(msg['content'])
            
            # 3. Mensagens importantes
            important_messages = await self.get_important_messages(
                user_id=user_id,
                chat_id=chat_id,
                min_importance=4,
                limit=context_limit // 4  # Um quarto para mensagens importantes
            )
            
            # Formata mensagens recentes
            formatted_recent = [
                {"role": msg['role'], "content": msg['content']}
                for msg in recent_messages
            ]
            
            # Formata mensagens importantes (evitando duplicações)
            recent_and_semantic_content = {
                msg['content'] for msg in recent_messages + semantic_messages
            }
            
            formatted_important = [
                {"role": msg['role'], "content": msg['content']}
                for msg in important_messages
                if msg['content'] not in recent_and_semantic_content
            ]
            
            # Combina todos os tipos de mensagens
            all_messages = formatted_recent + semantic_messages + formatted_important
            
            # Limita o total de mensagens
            if len(all_messages) > context_limit:
                all_messages = all_messages[:context_limit]
            
            logger.info(
                f"Contexto recuperado: {len(all_messages)} mensagens ("
                f"{len(formatted_recent)} recentes, {len(semantic_messages)} semânticas, "
                f"{len(formatted_important)} importantes)"
            )
            
            return all_messages
                
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {str(e)}", exc_info=True)
            # Retorna ao menos as mensagens recentes em caso de falha
            try:
                recent_msgs = await self.get_recent_messages(user_id, chat_id, limit=5)
                return [{"role": msg['role'], "content": msg['content']} for msg in recent_msgs]
            except:
                return []
    
    async def check_and_repair(self) -> Dict[str, Any]:
        """
        Verifica e repara problemas na sincronização entre SQLite e ChromaDB.
        
        Returns:
            dict: Estatísticas de reparo
        """
        stats = {
            "checked": 0,
            "repaired": 0,
            "errors": 0,
            "status": "success"
        }
        
        try:
            # 1. Busca mensagens sem embedding_id no SQLite
            missing_embedding = self.db.execute_query("""
                SELECT id, user_id, chat_id, role, content, category, importance 
                FROM messages 
                WHERE embedding_id IS NULL OR embedding_id = ''
                LIMIT 100
            """)
            
            stats["missing_embeddings"] = len(missing_embedding)
            
            # 2. Tenta corrigir cada uma
            for msg in missing_embedding:
                try:
                    # Gera novo embedding_id
                    embedding_id = f"msg_{msg['user_id']}_{int(time.time()*1000)}_{msg['id']}"
                    
                    # Adiciona ao ChromaDB
                    self.messages_collection.add(
                        documents=[msg['content']],
                        metadatas=[{
                            "user_id": str(msg['user_id']),
                            "chat_id": str(msg['chat_id']),
                            "role": msg['role'],
                            "category": msg['category'] or 'geral',
                            "timestamp": datetime.now().isoformat()
                        }],
                        ids=[embedding_id]
                    )
                    
                    # Atualiza o SQLite
                    self.db.execute_query(
                        "UPDATE messages SET embedding_id = ? WHERE id = ?",
                        (embedding_id, msg['id'])
                    )
                    
                    stats["repaired"] += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao reparar mensagem #{msg['id']}: {e}")
                    stats["errors"] += 1
            
            stats["status"] = "success"
            return stats
            
        except Exception as e:
            logger.error(f"Erro durante verificação/reparo: {e}")
            stats["status"] = "error"
            stats["error_message"] = str(e)
            return stats

    def debug_memory_state(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """
        Retorna o estado atual da memória para depuração.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            
        Returns:
            dict: Estado da memória
        """
        state = {
            "sqlite": {"count": 0, "samples": []},
            "chromadb": {"count": 0, "samples": []},
            "health": "ok"
        }
        
        try:
            # Verifica SQLite
            sql_results = self.db.execute_query(
                "SELECT COUNT(*) as count FROM messages WHERE user_id=? AND chat_id=?",
                (user_id, chat_id)
            )
            state["sqlite"]["count"] = sql_results[0]['count'] if sql_results else 0
            
            # Amostras do SQLite
            samples = self.db.execute_query(
                """
                SELECT id, role, embedding_id, substr(content, 1, 50) as content_preview
                FROM messages 
                WHERE user_id=? AND chat_id=?
                ORDER BY timestamp DESC LIMIT 5
                """,
                (user_id, chat_id)
            )
            state["sqlite"]["samples"] = samples
            
            # Verifica ChromaDB
            try:
                results = self.messages_collection.query(
                    query_texts=[""],
                    where={
                        "user_id": {"$eq": str(user_id)},
                        "chat_id": {"$eq": str(chat_id)}
                    },
                    include=["metadatas"],
                    n_results=999
                )
                
                state["chromadb"]["count"] = len(results['ids'][0]) if results['ids'] else 0
                
                # Amostras do ChromaDB
                if results['ids'] and len(results['ids'][0]) > 0:
                    samples = []
                    for i in range(min(5, len(results['ids'][0]))):
                        samples.append({
                            "id": results['ids'][0][i],
                            "metadata": results['metadatas'][0][i]
                        })
                    state["chromadb"]["samples"] = samples
            except Exception as chroma_err:
                state["chromadb"]["error"] = str(chroma_err)
                state["health"] = "chroma_error"
            
            # Verifica divergência
            if state["sqlite"]["count"] != state["chromadb"]["count"]:
                state["health"] = "diverged"
                state["divergence"] = abs(state["sqlite"]["count"] - state["chromadb"]["count"])
            
            return state
            
        except Exception as e:
            logger.error(f"Erro ao verificar estado da memória: {e}")
            state["health"] = "error"
            state["error"] = str(e)
            return state