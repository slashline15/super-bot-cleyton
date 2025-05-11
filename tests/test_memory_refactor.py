# python -m tests.test_memory_refactor
"""
Teste do sistema de memória refatorado.

Este teste valida as principais funcionalidades da refatoração,
garantindo que o sistema está funcionando corretamente.

Uso:
    python -m tests.test_memory_refactor
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
import random
import string

# Adiciona o diretório src ao PATH
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('memory_test')

# Importa os componentes a serem testados
from src.bot.memory.memory_manager import MemoryManager
from src.bot.memory.chroma_manager import ChromaManager
from src.bot.database.db_init import Database

# IDs de teste aleatórios para evitar conflitos
TEST_USER_ID = random.randint(100000, 999999)
TEST_CHAT_ID = random.randint(100000, 999999)

async def test_memory_roundtrip():
    """Testa o ciclo completo de escrita e leitura na memória."""
    print(f"\n🧪 Teste de ciclo escrita/leitura (user_id={TEST_USER_ID}, chat_id={TEST_CHAT_ID})")
    
    test_content = f"Mensagem de teste {random.randint(1000, 9999)}: " + ''.join(random.choices(string.ascii_letters, k=20))
    test_category = "teste"
    test_importance = 3
    
    memory = MemoryManager()
    
    # Adiciona uma mensagem
    print("▶️ Adicionando mensagem à memória...")
    embedding_id = await memory.add_message(
        user_id=TEST_USER_ID,
        chat_id=TEST_CHAT_ID,
        content=test_content,
        role="user",
        category=test_category,
        importance=test_importance
    )
    
    if not embedding_id:
        print("❌ Falha ao adicionar mensagem!")
        return False
    
    print(f"✅ Mensagem adicionada com embedding_id: {embedding_id}")
    
    # Recupera mensagens recentes
    print("▶️ Buscando mensagens recentes...")
    recent_msgs = await memory.get_recent_messages(
        user_id=TEST_USER_ID,
        chat_id=TEST_CHAT_ID,
        limit=5
    )
    
    if not recent_msgs:
        print("❌ Falha ao recuperar mensagens recentes!")
        return False
    
    found_recent = any(test_content == msg['content'] for msg in recent_msgs)
    print(f"✅ Mensagem encontrada em mensagens recentes: {found_recent}")
    
    # Busca semântica
    print("▶️ Realizando busca semântica...")
    results = await memory.get_relevant_context(
        query=test_content.split()[-1],  # Usa última palavra como query
        user_id=TEST_USER_ID,
        chat_id=TEST_CHAT_ID,
        limit=5
    )
    
    found_semantic = any(test_content == msg['content'] for msg in results)
    print(f"✅ Mensagem encontrada em busca semântica: {found_semantic}")
    
    # Obtém contexto completo
    print("▶️ Obtendo contexto completo...")
    context = await memory.get_context_messages(
        user_id=TEST_USER_ID,
        chat_id=TEST_CHAT_ID,
        query=test_content.split()[0]  # Usa primeira palavra como query
    )
    
    found_context = any(test_content == msg['content'] for msg in context)
    print(f"✅ Mensagem encontrada em contexto: {found_context}")
    
    return found_recent and found_context

async def test_memory_integrity():
    """Testa a integridade entre SQLite e ChromaDB."""
    print("\n🧪 Teste de integridade SQLite-ChromaDB")
    
    # Conecta ao banco SQLite
    db = Database()
    
    # Conta no SQLite
    try:
        sql_count = db.execute_query(
            "SELECT COUNT(*) as count FROM messages WHERE user_id=? AND chat_id=?",
            (TEST_USER_ID, TEST_CHAT_ID)
        )[0]['count']
        
        print(f"✅ SQLite: {sql_count} mensagens")
    except Exception as e:
        print(f"❌ Erro ao contar no SQLite: {e}")
        return False
    
    # Conecta ao ChromaDB
    try:
        cm = ChromaManager()
        collection = cm.get_or_create_collection("messages")
        
        # Conta no ChromaDB
        results = collection.query(
            query_texts=[""],
            where={
                "user_id": {"$eq": str(TEST_USER_ID)},
                "chat_id": {"$eq": str(TEST_CHAT_ID)}
            },
            include=["metadatas"],
            n_results=999
        )
        
        chroma_count = len(results['ids'][0]) if results['ids'] else 0
        print(f"✅ ChromaDB: {chroma_count} documentos")
    except Exception as e:
        print(f"❌ Erro ao contar no ChromaDB: {e}")
        return False
        
    # Verifica integridade
    if sql_count == chroma_count:
        print(f"✅ Integridade perfeita: {sql_count} mensagens em ambos os bancos")
        return True
    else:
        print(f"❌ Divergência detectada: SQLite tem {sql_count}, ChromaDB tem {chroma_count}")
        return False

async def test_error_handling():
    """Testa o tratamento de erros no sistema de memória."""
    print("\n🧪 Teste de tratamento de erros")
    
    try:
        memory = MemoryManager()
        
        # Tenta adicionar mensagem com conteúdo inválido
        print("▶️ Testando tratamento com mensagem vazia...")
        result = await memory.add_message(
            user_id=TEST_USER_ID,
            chat_id=TEST_CHAT_ID,
            content="",
            role="user"
        )
        
        # Deve aceitar mensagem vazia (criar ID de embedding)
        if result:
            print("✅ Tratou mensagem vazia corretamente")
        else:
            print("⚠️ Tratamento de mensagem vazia com falha (não crítico)")
            
        # Tenta processar query vazia
        print("▶️ Testando busca com query vazia...")
        results = await memory.get_relevant_context(
            query="",
            user_id=TEST_USER_ID,
            chat_id=TEST_CHAT_ID
        )
        
        # Deve retornar lista vazia, não erro
        if isinstance(results, list):
            print("✅ Tratou query vazia corretamente")
        else:
            print("❌ Falha ao tratar query vazia")
            return False
            
        # Testa debug_memory_state
        print("▶️ Testando diagnóstico de memória...")
        state = memory.debug_memory_state(TEST_USER_ID, TEST_CHAT_ID)
        
        if isinstance(state, dict) and "health" in state:
            print(f"✅ Diagnóstico retornado: status='{state['health']}'")
        else:
            print("❌ Falha ao obter diagnóstico")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Erro não tratado: {e}")
        return False

async def run_tests():
    """Executa todos os testes em sequência."""
    print("\n" + "="*80)
    print("🧪 INICIANDO TESTES DO SISTEMA DE MEMÓRIA REFATORADO 🧪")
    print("="*80)
    
    tests = [
        ("Ciclo escrita/leitura", test_memory_roundtrip),
        ("Integridade SQLite-ChromaDB", test_memory_integrity),
        ("Tratamento de erros", test_error_handling)
    ]
    
    results = []
    
    for name, test_func in tests:
        print(f"\n[TESTE] {name}")
        print("-" * 40)
        
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Exceção não tratada: {e}")
            results.append((name, False))
    
    # Resumo dos resultados
    print("\n" + "="*40)
    print("📋 RESUMO DOS TESTES")
    print("="*40)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*40)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM! Sistema de memória está funcionando.")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM. Verifique os logs acima.")
    print("="*40)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Testes interrompidos pelo usuário.")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n❌ Erro fatal durante os testes: {e}")
        sys.exit(3)