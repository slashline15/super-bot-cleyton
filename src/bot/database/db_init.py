# database/db_init.py
"""
db_init.py

Módulo responsável pela inicialização e gerenciamento do banco de dados SQLite.
Contém a classe Database que fornece métodos para conexão, inicialização e execução
de queries no banco de dados.
"""

import sqlite3
import os
from datetime import datetime
import logging
from contextlib import contextmanager
from src.config.config import Config

# Configura o logger para o módulo de banco de dados
logger = logging.getLogger(__name__)

class Database:
    """
    Classe para gerenciar conexões e operações no banco de dados SQLite.

    A classe inicializa o banco de dados, criando a tabela 'messages' e seus índices,
    e fornece métodos para executar queries e inserir dados de forma segura usando
    um context manager.
    """
    def __init__(self, db_name=Config.DB_NAME):
        """
        Inicializa a instância do Database.

        Parâmetros:
            db_name (str): Nome do arquivo do banco de dados. O padrão é Config.DB_NAME.
        """
        self.db_name = db_name
        self.initialize_db()  # Garante que a estrutura do banco esteja criada
        logger.info(f"Database inicializado: {db_name}")
    
    @contextmanager
    def connect(self):
        """
        Context manager para conexão com o banco de dados SQLite.

        Garante que a conexão seja commitada se tudo ocorrer bem ou que ocorra um rollback
        em caso de erro, além de fechar a conexão ao final do bloco.

        Yields:
            sqlite3.Connection: Conexão com o banco de dados.
        """
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Define o row_factory para sqlite3.Row
        try:
            yield conn
            conn.commit()
            logger.debug("Transação commitada com sucesso")
        except Exception as e:
            conn.rollback()
            logger.error(f"Erro na transação, realizando rollback: {e}")
            raise
        finally:
            conn.close()
            logger.debug("Conexão fechada")

    def execute_query(self, query: str, params: tuple = ()):
        """
        Executa uma query SQL e retorna os resultados

        Args:
            query (str): Query SQL a ser executada
            params (tuple): Parâmetros para a query (opcional)

        Returns:
            list: Lista com os resultados da query
        """
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # Se for SELECT, retorna os resultados
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            
            # Se for INSERT/UPDATE/DELETE, retorna o número de linhas afetadas
            return cursor.rowcount

    def initialize_db(self):
        """Inicializa o banco de dados com todas as tabelas necessárias"""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Tabela messages
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                chat_id INTEGER,
                context_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tokens INTEGER,
                category TEXT,
                importance INTEGER,
                embedding_id TEXT
            )
            ''')
            
            # Tabela documents
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE,
                title TEXT,
                doc_type TEXT,
                total_chunks INTEGER,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Índices para a tabela messages
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_chat ON messages(user_id, chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_category ON messages(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_importance ON messages(importance)')
            
            # Índices para a tabela documents
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(doc_type)')
            
            logger.info("Tabelas e índices inicializados com sucesso")