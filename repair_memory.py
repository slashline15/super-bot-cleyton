# python repair_memory.py
"""
Script para reparar índices do ChromaDB.
Limpa o diretório do ChromaDB e faz uma reingestão limpa das mensagens.
"""
import os
import shutil
import logging
import time
from pathlib import Path
from src.bot.memory.memory_manager import MemoryManager
from src.bot.database.db_init import Database

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('repair_memory')

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """Imprime uma barra de progresso no terminal"""
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    # Imprime nova linha no final
    if iteration == total: 
        print()

def repair_memory():
    """Repara a memória do ChromaDB recriando os índices a partir do SQLite"""
    print("\n🔧 INICIANDO REPARO DA MEMÓRIA 🔧\n")
    start_time = time.time()
    
    # 1. Backup do diretório atual do ChromaDB
    chroma_dir = Path("./data/chroma_db")
    backup_dir = Path("./data/chroma_backup_" + time.strftime("%Y%m%d_%H%M%S"))
    
    if chroma_dir.exists():
        print(f"📦 Fazendo backup de {chroma_dir} para {backup_dir}")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(chroma_dir, backup_dir)
        print(f"✅ Backup concluído!")
    
    # 2. Limpar o diretório do ChromaDB
    print(f"🧹 Limpando diretório {chroma_dir}")
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    
    # 3. Recuperar mensagens do SQLite
    print("🔍 Recuperando mensagens do SQLite")
    db = Database()
    messages = db.execute_query("""
        SELECT user_id, chat_id, role, content, category, importance
        FROM messages 
        ORDER BY timestamp
    """)
    
    print(f"✅ Recuperadas {len(messages)} mensagens")
    
    # 4. Recriar o MemoryManager
    print("🧠 Inicializando novo gerenciador de memória...")
    memory = MemoryManager(persist_directory=str(chroma_dir))
    print("✅ MemoryManager inicializado!")
    
    # 5. Reingerir mensagens no ChromaDB
    print("\n🔄 Reingerindo mensagens no ChromaDB...\n")
    count = 0
    errors = 0
    
    # Inicializar barra de progresso
    print_progress_bar(0, len(messages), prefix='Progresso:', suffix='Completo', length=40)
    
    # Processar mensagens
    for i, msg in enumerate(messages):
        try:
            memory.add_message_sync(
                user_id=msg["user_id"],
                chat_id=msg["chat_id"],
                content=msg["content"],
                role=msg["role"],
                category=msg["category"],
                importance=msg["importance"]
            )
            count += 1
            
            # Atualizar barra de progresso a cada mensagem
            print_progress_bar(i + 1, len(messages), 
                              prefix='Progresso:', 
                              suffix=f'Completo ({count} ok, {errors} erros)', 
                              length=40)
            
        except Exception as e:
            errors += 1
            logger.error(f"❌ Erro na mensagem {i+1}: {str(e)[:100]}...")
            print_progress_bar(i + 1, len(messages), 
                              prefix='Progresso:', 
                              suffix=f'Completo ({count} ok, {errors} erros)', 
                              length=40)
    
    elapsed_time = time.time() - start_time
    
    # Resumo final
    print("\n" + "="*60)
    print(f"🎉 REPARO CONCLUÍDO! 🎉")
    print(f"✅ Mensagens processadas: {count}/{len(messages)}")
    if errors > 0:
        print(f"❌ Erros encontrados: {errors}")
    print(f"⏱️ Tempo total: {elapsed_time:.2f} segundos")
    print("="*60)

if __name__ == "__main__":
    try:
        repair_memory()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {str(e)}")
        logger.exception("Erro fatal durante o reparo")