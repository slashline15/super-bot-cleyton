# tests/test_memory_manager.py
import sys
import os
import asyncio
from pathlib import Path
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)

# Adiciona o diretório src ao PATH
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

from bot.memory.memory_manager import MemoryManager

async def test_memory_manager():
    """Testa as funcionalidades básicas do MemoryManager"""
    memory = None
    try:
        # Inicializa com diretório de teste
        memory = MemoryManager("./test_chroma_db")
        
        # Dados de teste
        user_id = 123
        chat_id = 456
        messages = [
            ("Preciso registrar no diário de obra que tivemos atraso na concretagem", "user"),
            ("Quanto ficou o orçamento da obra?", "user"),
            ("Agendar reunião com o cliente para amanhã", "user"),
        ]
        
        print("🔄 Testando adição de mensagens...")
        for content, role in messages:
            await memory.add_message(user_id, chat_id, content, role)
            print(f"✓ Mensagem adicionada: {content[:30]}...")
        
        print("\n🔍 Testando busca de contexto...")
        context = await memory.get_relevant_context(
            "problemas na obra",
            user_id,
            chat_id
        )
        print(f"✓ Contexto encontrado: {len(context)} mensagens")
        
        print("\n📊 Testando estatísticas...")
        stats = await memory.get_category_stats(user_id, chat_id)
        print(f"✓ Categorias encontradas: {[stat['category'] for stat in stats]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False
    finally:
        if memory:
            del memory  # Força a limpeza do ChromaDB

if __name__ == "__main__":
    print("🚀 Iniciando teste do MemoryManager...")
    success = asyncio.run(test_memory_manager())
    
    if success:
        print("\n✨ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1)