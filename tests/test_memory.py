# python -m tests.test_memory
import asyncio
import pytest
from datetime import datetime
from src.bot.memory.memory_manager import MemoryManager
from src.config.config import Config

@pytest.fixture
async def memory_manager():
    manager = MemoryManager(persist_directory="./test_chroma_db")
    yield manager
    # Limpa a coleção após os testes
    manager.messages_collection.delete(where={})

async def test_add_message(memory_manager):
    user_id = 123
    content = "Teste de mensagem"
    metadata = {"chat_id": 456, "role": "user"}
    
    await memory_manager.add_message(user_id, content, metadata)
    
    # Verifica se a mensagem foi adicionada
    results = memory_manager.messages_collection.get(
        where={"user_id": user_id}
    )
    
    assert len(results['documents']) == 1
    assert results['documents'][0] == content

async def test_search_similar_messages(memory_manager):
    # Adiciona algumas mensagens
    messages = [
        "Como faço um cronograma de obra?",
        "Qual o melhor método para controle financeiro?",
        "Preciso de ajuda com o diário de obra"
    ]
    
    for i, msg in enumerate(messages):
        await memory_manager.add_message(
            user_id=123,
            content=msg,
            metadata={"chat_id": 456, "role": "user"}
        )
    
    # Busca mensagens similares
    query = "Me ajude com o cronograma da obra"
    results = await memory_manager.search_similar_messages(
        query=query,
        user_id=123,
        limit=2
    )
    
    assert len(results) > 0
    assert "cronograma" in results[0].lower()

async def test_clear_old_messages(memory_manager):
    # Adiciona mensagens
    await memory_manager.add_message(
        user_id=123,
        content="Mensagem antiga",
        metadata={
            "timestamp": (datetime.now().timestamp() - 40*24*60*60),
            "chat_id": 456,
            "role": "user"
        }
    )
    
    await memory_manager.add_message(
        user_id=123,
        content="Mensagem recente",
        metadata={"chat_id": 456, "role": "user"}
    )
    
    # Limpa mensagens antigas
    await memory_manager.clear_old_messages(days=30)
    
    # Verifica resultados
    results = memory_manager.messages_collection.get()
    assert len(results['documents']) == 1
    assert results['documents'][0] == "Mensagem recente"

if __name__ == "__main__":
    asyncio.run(pytest.main(["-v", __file__]))