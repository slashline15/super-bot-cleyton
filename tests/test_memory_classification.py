# tests/test_categorization.py
import asyncio
from src.bot.memory.memory_manager import MemoryManager

async def test_categorization():
    memory = MemoryManager()
    
    test_messages = [
        "Me lembre de comprar café amanhã",
        "Qual a resistência do concreto de 30 MPa?",
        "Precisamos terminar o relatório até sexta-feira",
        "O orçamento do projeto está em R$ 150.000"
    ]
    
    print("\n===== TESTE DE CATEGORIZAÇÃO =====")
    for msg in test_messages:
        category, importance = await memory.categorize_with_llm(msg)
        print(f"Mensagem: {msg[:30]}...")
        print(f"Categoria: {category}")
        print(f"Importância: {importance}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_categorization())