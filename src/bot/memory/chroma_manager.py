# src/bot/memory/chroma_manager.py
import chromadb
import threading
import logging
import os
import time
from pathlib import Path
from functools import wraps

logger = logging.getLogger("ChromaManager")

def retry_on_exception(max_retries=3, retry_delay=0.5):
    """Decorator para fazer retry em operações do ChromaDB."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    wait_time = retry_delay * (2 ** attempt)  # Backoff exponencial
                    logger.warning(f"Tentativa {attempt+1}/{max_retries} falhou: {e}. Aguardando {wait_time:.2f}s")
                    time.sleep(wait_time)
            
            # Se chegamos aqui, todas as tentativas falharam
            logger.error(f"Todas as {max_retries} tentativas falharam. Último erro: {last_exception}")
            raise last_exception
        return wrapper
    return decorator

class ChromaManager:
    """
    Gerenciador de conexão com ChromaDB usando padrão Singleton thread-safe.

    Esta classe garante que apenas uma conexão com o ChromaDB seja
    estabelecida por processo, economizando recursos e evitando
    problemas de concorrência.
    """
    _instance = None
    _client = None
    _lock = threading.Lock()
    _initialized = False  # Atributo de classe para controle real

    def __new__(cls, *args, **kwargs):
        """Implementa o padrão Singleton thread-safe."""
        with cls._lock:  # Protege toda a criação de instância
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, persist_directory="./data/chroma_db"):
        """
        Inicializa o gerenciador do ChromaDB de forma thread-safe.

        Args:
            persist_directory: Diretório para persistência dos dados
        """
        with self._lock:  # Protege toda a inicialização
            # Evita reinicialização do Singleton
            if ChromaManager._initialized:
                return

            self.persist_directory = persist_directory

            # Garante que o diretório existe
            os.makedirs(Path(persist_directory), exist_ok=True)

            try:
                self._client = self._connect_with_retry()
                logger.info(f"ChromaDB inicializado em {persist_directory}")
            except Exception as e:
                logger.error(f"Falha ao inicializar ChromaDB: {e}")
                raise

            ChromaManager._initialized = True
    
    @retry_on_exception(max_retries=3)
    def _connect_with_retry(self):
        """Conecta ao ChromaDB com retries."""
        return chromadb.PersistentClient(path=self.persist_directory)
    
    @property
    def client(self):
        """Retorna o cliente ChromaDB."""
        return self._client
    
    @classmethod
    def get_client(cls, persist_directory="./data/chroma_db"):
        """
        Método de classe para obter o cliente ChromaDB.
        
        Args:
            persist_directory: Diretório para persistência dos dados
            
        Returns:
            Cliente ChromaDB inicializado
        """
        # Garante que o singleton está inicializado
        instance = cls(persist_directory)
        return instance.client
    
    def get_or_create_collection(self, name, metadata=None):
        """
        Obtém ou cria uma coleção no ChromaDB.
        
        Args:
            name: Nome da coleção
            metadata: Metadados da coleção (opcional)
            
        Returns:
            Coleção do ChromaDB
        """
        try:
            return self._client.get_or_create_collection(name=name, metadata=metadata)
        except Exception as e:
            logger.error(f"Erro ao criar coleção {name}: {e}")
            raise
    
    def health_check(self):
        """
        Verifica se o ChromaDB está funcionando corretamente.
        
        Returns:
            bool: True se está saudável, False caso contrário
        """
        try:
            # Tenta listar as coleções para verificar se a conexão está ok
            collections = self._client.list_collections()
            return True
        except Exception as e:
            logger.error(f"Erro no health check do ChromaDB: {e}")
            return False
    
    def reset_client(self):
        """
        Reseta o cliente do ChromaDB em caso de problemas.
        
        Returns:
            Novo cliente ChromaDB
        """
        with self._lock:
            try:
                logger.warning("Resetando cliente ChromaDB")
                self._client = self._connect_with_retry()
                return self._client
            except Exception as e:
                logger.error(f"Falha ao resetar cliente ChromaDB: {e}")
                raise