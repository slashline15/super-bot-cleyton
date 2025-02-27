import sqlite3
from threading import Lock
from contextlib import contextmanager
import logging
from config.config import Config

logger = logging.getLogger('DatabaseConnection')

class DatabaseConnectionManager:
    _instance = None
    _lock = Lock()
    _connection = None
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_name = Config.DB_NAME
            self.initialized = True
            logger.info(f"Inicializando connection manager para {self.db_name}")
    
    def _get_connection(self):
        """
        Retorna uma conexão existente ou cria uma nova se necessário
        """
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(
                    self.db_name,
                    check_same_thread=False  # Permite uso em múltiplas threads
                )
                logger.debug("Nova conexão com banco de dados estabelecida")
            except sqlite3.Error as e:
                logger.error(f"Erro ao conectar ao banco: {e}")
                raise
        return self._connection
    
    @contextmanager
    def get_cursor(self):
        """
        Contexto que fornece um cursor e gerencia transações
        """
        connection = self._get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
            connection.commit()
        except Exception as e:
            connection.rollback()
            logger.error(f"Erro durante operação no banco: {e}")
            raise
        finally:
            cursor.close()
    
    def close(self):
        """
        Fecha a conexão explicitamente se necessário
        """
        if self._connection is not None:
            try:
                self._connection.close()
                self._connection = None
                logger.info("Conexão com banco de dados fechada")
            except sqlite3.Error as e:
                logger.error(f"Erro ao fechar conexão: {e}")
                raise