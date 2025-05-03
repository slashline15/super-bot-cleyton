import chromadb
from functools import lru_cache
import logging
import os

logger = logging.getLogger('MemorySingleton')

@lru_cache(maxsize=1)
def get_chroma_client(persist_directory="./data/chroma_db"):
    """
    Retorna um único cliente ChromaDB por processo
    """
    logger.info(f"Criando cliente ChromaDB com persist_directory={persist_directory}")
    return chromadb.PersistentClient(path=persist_directory)