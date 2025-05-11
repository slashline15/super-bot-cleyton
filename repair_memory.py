# python repair_memory.py
"""
Script para reparar índices do ChromaDB.

Este script faz um diagnóstico completo da memória do bot,
limpa o diretório do ChromaDB se necessário e recria todos os índices
a partir do SQLite de forma segura e atômica.

Uso:
    python repair_memory.py [--force]
    
    --force: Se fornecido, força a recriação completa dos índices
"""
import os
import sys
import shutil
import logging
import time
import argparse
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Configuração de logging
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

def backup_database(source_dir, backup_dir, skip_if_recent=True):
    """
    Cria um backup do diretório do ChromaDB.
    
    Args:
        source_dir (Path): Diretório fonte
        backup_dir (Path): Diretório de backup
        skip_if_recent (bool): Pula se já existe backup recente (última hora)
    
    Returns:
        bool: True se backup criado, False se pulado
    """
    # Verifica se deve pular (backup recente)
    if skip_if_recent and backup_dir.exists():
        # Verifica idade do backup
        try:
            backup_time = datetime.fromtimestamp(backup_dir.stat().st_mtime)
            age_hours = (datetime.now() - backup_time).total_seconds() / 3600
            
            if age_hours < 1:
                logger.info(f"Backup existente é recente ({age_hours:.1f}h). Pulando backup.")
                return False
        except Exception as e:
            logger.warning(f"Não foi possível determinar idade do backup: {e}")
    
    # Se o diretório fonte não existe, nada a fazer
    if not source_dir.exists():
        logger.warning(f"Diretório fonte {source_dir} não existe. Nada para backup.")
        return False
    
    logger.info(f"📦 Fazendo backup de {source_dir} para {backup_dir}")
    
    try:
        # Remove backup existente
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        
        # Cria o backup
        shutil.copytree(source_dir, backup_dir)
        logger.info(f"✅ Backup concluído em {backup_dir}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao criar backup: {e}")
        return False

def check_database_integrity():
    """
    Verifica a integridade do banco SQLite.
    
    Returns:
        dict: Estatísticas e status da verificação
    """
    logger.info("🔍 Verificando integridade do banco SQLite...")
    stats = {
        "status": "ok",
        "total_messages": 0,
        "messages_without_embedding": 0,
        "categories": {}
    }
    
    try:
        # Conecta ao banco
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verifica se tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            stats["status"] = "error"
            stats["error"] = "Tabela 'messages' não existe"
            return stats
        
        # Contagem total
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        stats["total_messages"] = cursor.fetchone()[0]
        
        # Contagem sem embedding_id
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE embedding_id IS NULL OR embedding_id = ''")
        stats["messages_without_embedding"] = cursor.fetchone()[0]
        
        # Contagem por categoria
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM messages 
            GROUP BY category
        """)
        categories = cursor.fetchall()
        for cat in categories:
            stats["categories"][cat['category']] = cat['count']
        
        # Inclui amostra de mensagens recentes
        cursor.execute("""
            SELECT id, user_id, chat_id, role, substr(content, 1, 50) as snippet
            FROM messages 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        stats["recent_messages"] = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"✅ Verificação concluída: {stats['total_messages']} mensagens no total")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar banco: {e}")
        stats["status"] = "error"
        stats["error"] = str(e)
        return stats

def diagnose_problems():
    """
    Diagnostica problemas específicos no sistema de memória.
    
    Returns:
        dict: Diagnóstico com problemas encontrados
    """
    logger.info("🔍 Diagnosticando problemas específicos...")
    issues = {
        "has_issues": False,
        "problems": []
    }
    
    try:
        # Conecta ao banco
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Mensagens sem embedding_id
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE embedding_id IS NULL OR embedding_id = ''")
        missing_embedding = cursor.fetchone()[0]
        
        if missing_embedding > 0:
            issues["has_issues"] = True
            issues["problems"].append({
                "type": "missing_embedding_id",
                "count": missing_embedding,
                "description": f"Há {missing_embedding} mensagens sem embedding_id"
            })
        
        # Embedding_ids duplicados
        cursor.execute("""
            SELECT embedding_id, COUNT(*) as count 
            FROM messages 
            WHERE embedding_id IS NOT NULL AND embedding_id != ''
            GROUP BY embedding_id 
            HAVING COUNT(*) > 1
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            issues["has_issues"] = True
            issues["problems"].append({
                "type": "duplicate_embedding_id",
                "count": len(duplicates),
                "description": f"Há {len(duplicates)} embedding_ids duplicados"
            })
        
        # Registros inválidos (sem user_id ou chat_id)
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE user_id IS NULL OR chat_id IS NULL")
        invalid_records = cursor.fetchone()[0]
        
        if invalid_records > 0:
            issues["has_issues"] = True
            issues["problems"].append({
                "type": "invalid_records",
                "count": invalid_records,
                "description": f"Há {invalid_records} mensagens sem user_id ou chat_id"
            })
        
        if not issues["has_issues"]:
            logger.info("✅ Nenhum problema específico encontrado!")
        else:
            logger.warning(f"⚠️ Encontrados {len(issues['problems'])} problemas")
            
        return issues
        
    except Exception as e:
        logger.error(f"❌ Erro no diagnóstico: {e}")
        issues["has_issues"] = True
        issues["problems"].append({
            "type": "diagnostic_error",
            "description": f"Erro ao diagnosticar: {str(e)}"
        })
        return issues

def repair_memory(force_rebuild=False):
    """
    Repara a memória do ChromaDB recriando os índices a partir do SQLite.
    
    Args:
        force_rebuild (bool): Se deve forçar reconstrução completa
    """
    print("\n" + "="*60)
    print("🔧 INICIANDO REPARO DA MEMÓRIA 🔧")
    print("="*60)
    
    start_time = time.time()
    
    # 1. Verifica banco e diagnostica problemas
    db_stats = check_database_integrity()
    if db_stats["status"] != "ok":
        print(f"❌ Erro no banco: {db_stats.get('error', 'Erro desconhecido')}")
        print("Abortando reparo.")
        return
    
    issues = diagnose_problems()
    
    # Determina se é necessário reparo
    needs_repair = force_rebuild or issues["has_issues"]
    
    if not needs_repair and db_stats["messages_without_embedding"] == 0:
        print("\n✅ Sistema de memória parece estar íntegro. Nenhum reparo necessário.")
        print("   Use --force para forçar o reparo completo.")
        return
    
    # 2. Define diretórios
    chroma_dir = Path("./data/chroma_db")
    backup_dir = Path("./data/chroma_backup_" + time.strftime("%Y%m%d_%H%M%S"))
    
    # 3. Backup do diretório atual do ChromaDB
    backup_created = backup_database(chroma_dir, backup_dir)
    
    if not backup_created and force_rebuild:
        print("⚠️ Não foi possível criar backup, mas --force foi especificado.")
        confirm = input("Continuar mesmo sem backup? (s/N): ").lower()
        if confirm != 's':
            print("Operação cancelada pelo usuário.")
            return
    
    # 4. Limpar o diretório do ChromaDB se forçar reconstrução
    if force_rebuild:
        print(f"🧹 Limpando diretório {chroma_dir}")
        if chroma_dir.exists():
            try:
                shutil.rmtree(chroma_dir)
                print("✅ Diretório do ChromaDB limpo com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao limpar diretório: {e}")
                return
    
    # Importa dependências apenas quando confirmado que reparo é necessário
    from src.bot.memory.memory_manager import MemoryManager
    from src.bot.database.db_init import Database
    
    # 5. Recuperar mensagens do SQLite
    print(f"🔍 Recuperando mensagens do SQLite")
    db = Database()
    
    # Se forçar reconstrução, pega todas as mensagens
    if force_rebuild:
        messages = db.execute_query("""
            SELECT user_id, chat_id, role, content, category, importance
            FROM messages 
            ORDER BY timestamp
        """)
    # Caso contrário, pega apenas mensagens sem embedding_id
    else:
        messages = db.execute_query("""
            SELECT user_id, chat_id, role, content, category, importance
            FROM messages 
            WHERE embedding_id IS NULL OR embedding_id = ''
            ORDER BY timestamp
        """)
    
    total_messages = len(messages)
    print(f"✅ Recuperadas {total_messages} mensagens para processamento")
    
    if total_messages == 0:
        print("✅ Nenhuma mensagem precisa ser processada!")
        return
    
    # 6. Inicializar um novo gerenciador de memória
    print("🧠 Inicializando gerenciador de memória...")
    memory = MemoryManager(persist_directory=str(chroma_dir))
    print("✅ MemoryManager inicializado!")
    
    # 7. Reprocessar mensagens
    print("\n🔄 Processando mensagens no ChromaDB...\n")
    count = 0
    errors = 0
    
    # Inicializar barra de progresso
    print_progress_bar(0, total_messages, prefix='Progresso:', suffix='Completo', length=40)
    
    # Processar mensagens
    for i, msg in enumerate(messages):
        try:
            # Aplica valores padrão para campos nulos
            if msg["category"] is None:
                msg["category"] = "geral"
            if msg["importance"] is None:
                msg["importance"] = 3
                
            memory.add_message_sync(
                user_id=msg["user_id"],
                chat_id=msg["chat_id"],
                content=msg["content"],
                role=msg["role"],
                category=msg["category"],
                importance=msg["importance"]
            )
            count += 1
            
        except Exception as e:
            errors += 1
            logger.error(f"❌ Erro na mensagem {i+1}: {str(e)[:100]}...")
        
        # Atualiza a barra de progresso
        print_progress_bar(i + 1, total_messages, 
                         prefix='Progresso:', 
                         suffix=f'Completo ({count} ok, {errors} erros)', 
                         length=40)
    
    elapsed_time = time.time() - start_time
    
    # Verifica integridade final
    final_errors = 0
    try:
        print("\n🔍 Verificando integridade final...")
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        total_in_sqlite = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE embedding_id IS NULL OR embedding_id = ''")
        missing_embedding = cursor.fetchone()[0]
        
        if missing_embedding > 0:
            print(f"⚠️ Ainda há {missing_embedding} mensagens sem embedding_id.")
            final_errors += 1
        else:
            print("✅ Todas as mensagens possuem embedding_id.")
    except Exception as e:
        print(f"❌ Erro na verificação final: {e}")
        final_errors += 1
    
    # Resumo final
    print("\n" + "="*60)
    print(f"🎉 REPARO CONCLUÍDO! 🎉")
    print(f"✅ Mensagens processadas: {count}/{total_messages}")
    if errors > 0:
        print(f"❌ Erros encontrados: {errors}")
    if final_errors > 0:
        print(f"⚠️ Problemas de integridade restantes: {final_errors}")
    print(f"⏱️ Tempo total: {elapsed_time:.2f} segundos")
    print("="*60)
    print("\nExecute o bot para verificar se tudo está funcionando corretamente.")

if __name__ == "__main__":
    # Processa argumentos de linha de comando
    parser = argparse.ArgumentParser(description="Repara a memória do bot")
    parser.add_argument("--force", action="store_true", help="Força reconstrução completa dos índices")
    args = parser.parse_args()
    
    try:
        # Adiciona o diretório do projeto ao path
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Executa o reparo
        repair_memory(force_rebuild=args.force)
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {str(e)}")
        logger.exception("Erro fatal durante o reparo")