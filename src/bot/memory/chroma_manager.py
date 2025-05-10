# python -m src.bot.memory.chroma_manager
# src/bot/memory/chroma_manager.py
import chromadb
import threading

class ChromaManager:
    """Tipo um Singleton, mas sem o drama todo de Singleton"""
    _client = None
    _lock = threading.Lock()  # NÃO usa asyncio.Lock()
    
    @classmethod
    def get_client(cls, persist_dir="./data/chroma_db"):
        if cls._client is None:
            with cls._lock:
                if cls._client is None:  # Double-check locking, a parada clássica
                    cls._client = chromadb.PersistentClient(path=persist_dir)
        return cls._client
