# python -m tests.test_memory_fix
import asyncio
import pytest
from src.bot.memory.memory_manager import MemoryManager

async def test_memory_persistence():
    """Testa se a memória tá persistindo mesmo"""
    memory = MemoryManager()
    
    # Adiciona uma mensagem
    test_msg = "Essa mensagem tem que ficar salva, porra!"
    await memory.add_message(123, 456, test_msg, "user")
    
    # Cria uma nova instância (simula reinício)
    memory2 = MemoryManager()
    
    # Busca a mensagem
    results = await memory2.get_relevant_context(
        query="mensagem tem que ficar",
        user_id=123,
        chat_id=456
    )
    
    # Verifica se encontrou
    found = any(test_msg in str(r) for r in results)
    assert found, "CARALHO! A mensagem sumiu de novo!"
    
    print("✅ Funcionou! A memória tá persistindo!")

if __name__ == "__main__":
    asyncio.run(test_memory_persistence())