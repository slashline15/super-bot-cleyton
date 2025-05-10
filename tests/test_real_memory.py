# python -m tests.test_real_memory
import asyncio
import uuid
from src.bot.memory.memory_manager import MemoryManager

async def test_real_persistence():
    """Teste pesado que nem sua sogra"""
    memory = MemoryManager()
    
    # ID único pra não confundir com lixo anterior
    test_user = 999888
    test_chat = 777666
    
    # Mensagem única identificável
    unique_id = str(uuid.uuid4())[:8]
    test_message = f"TESTE_UNICO_{unique_id}_DEVE_PERSISTIR"
    
    print(f"Salvando mensagem: {test_message}")
    
    # Salva a mensagem
    await memory.add_message(test_user, test_chat, test_message, "user")
    
    # Aguarda um pouco (pq pode ter delay no ChromaDB)
    await asyncio.sleep(2)
    
    # CRIAR NOVA INSTÂNCIA (simula reinício total)
    memory2 = MemoryManager()
    
    # Busca de várias formas
    print("Testando buscas...")
    
    # 1. Busca por texto exato
    results = await memory2.get_relevant_context(
        query=test_message,
        user_id=test_user,  # Os mesmos que salvou!
        chat_id=test_chat,   # Os mesmos que salvou!
    )
    
    # 2. Busca por parte do texto   
    results2 = await memory2.get_relevant_context(
        query=unique_id,
        user_id=test_user,
        chat_id=test_chat,
        limit=10
    )
    
    # 3. Busca no SQLite direto
    sql_results = memory2.db.execute_query(
        "SELECT * FROM messages WHERE user_id=? AND chat_id=? AND content LIKE ?",
        (test_user, test_chat, f"%{unique_id}%")
    )
    
    # 4. Busca no ChromaDB direto
    try:
        chroma_results = memory2.messages_collection.query(
            query_texts=[unique_id],
            where={
                "$and": [
                    {"user_id": {"$eq": str(test_user)}},
                    {"chat_id": {"$eq": str(test_chat)}}
                ]
            },
            n_results=10
        )
    except Exception as e:
        print(f"ChromaDB deu pau: {e}")
        chroma_results = None
    
    # Debug
    print(f"\nResultados:")
    print(f"- get_relevant_context (texto completo): {len(results1) if results1 else 0}")
    print(f"- get_relevant_context (ID): {len(results2) if results2 else 0}")
    print(f"- SQLite direto: {len(sql_results)}")
    print(f"- ChromaDB direto: {len(chroma_results['ids'][0]) if chroma_results and chroma_results['ids'] else 0}")
    
    # Mostra conteúdo
    if results1:
        print(f"\nPrimeiro resultado: {results1[0]}")
    if sql_results:
        print(f"\nSQLite encontrou: {sql_results[0]}")
    
    # Verifica se achou em pelo menos um
    found_in_context = any(unique_id in str(r) for r in (results1 + results2))
    found_in_sql = any(unique_id in str(r) for r in sql_results)
    found_in_chroma = chroma_results and len(chroma_results['ids'][0]) > 0
    
    if found_in_context and found_in_sql and found_in_chroma:
        print("\n✅ SUCESSO TOTAL! Encontrado em todos os lugares!")
    else:
        print(f"\n❌ FODEU! found_in_context={found_in_context}, found_in_sql={found_in_sql}, found_in_chroma={found_in_chroma}")
        
        # Se não achou, vamo ver onde tá o problema
        if not found_in_sql:
            print("🔥 PROBLEMA: Nem no SQLite salvou!")
        elif not found_in_chroma:
            print("🔥 PROBLEMA: SQLite tem, mas ChromaDB não!")
        elif not found_in_context:
            print("🔥 PROBLEMA: Tá salvo, mas get_relevant_context não acha!")

if __name__ == "__main__":
    asyncio.run(test_real_persistence())