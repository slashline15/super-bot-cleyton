# tests/test_memory_manager.py 
# python -m tests.test_memory_manager
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

from src.bot.memory.memory_manager import MemoryManager

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
        if isinstance(stats, dict):
            categories = stats.get('categories', [])
            total = stats.get('total_messages', 0)
            print(f"✓ Categorias encontradas: {len(categories)}")
            print(f"✓ Total de mensagens: {total}")
        else:
            raise ValueError("Estatísticas retornadas em formato inválido")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False
    finally:
        if memory:
            print("\n🧹 Limpando dados de teste...")
            try:
                # Apaga todos os documentos do teste usando o user_id específico
                memory.messages_collection.delete(
                    where={"user_id": {"$eq": "123"}}  # 123 é o user_id usado no teste
                )
                print("✓ Dados limpos com sucesso")
            except Exception as e:
                print(f"⚠️ Erro ao limpar dados: {e}")
                
if __name__ == "__main__":
    print("🚀 Iniciando teste do MemoryManager...")
    success = asyncio.run(test_memory_manager())
    
    if success:
        print("\n✨ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1)