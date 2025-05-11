# python check_memory.py
"""
Script para diagnóstico rápido do sistema de memória.

Verifica a integridade entre a base SQLite e o ChromaDB
e exibe estatísticas sobre o conteúdo da memória.

Uso:
    python check_memory.py [--user USER_ID] [--chat CHAT_ID] [--sample]
    
    --user: Filtra por ID de usuário específico
    --chat: Filtra por ID de chat específico
    --sample: Mostra amostras de mensagens recentes
"""
import os
import sys
import sqlite3
import argparse
import json
from datetime import datetime
from pathlib import Path
import logging
from tabulate import tabulate

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('check_memory')

def format_time_ago(timestamp_str):
    """Formata um timestamp como tempo relativo"""
    try:
        if not timestamp_str:
            return "desconhecido"
            
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        delta = datetime.now() - dt
        
        if delta.days > 365:
            return f"{delta.days // 365} anos atrás"
        elif delta.days > 30:
            return f"{delta.days // 30} meses atrás"
        elif delta.days > 0:
            return f"{delta.days} dias atrás"
        elif delta.seconds // 3600 > 0:
            return f"{delta.seconds // 3600} horas atrás"
        elif delta.seconds // 60 > 0:
            return f"{delta.seconds // 60} minutos atrás"
        else:
            return f"{delta.seconds} segundos atrás"
    except Exception:
        return "formato inválido"

def check_sqlite_integrity():
    """Verifica a integridade básica do banco SQLite"""
    stats = {
        "status": "ok",
        "total_messages": 0,
        "sqlite_problems": [],
    }
    
    try:
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            stats["status"] = "error"
            stats["sqlite_problems"].append("Tabela 'messages' não existe!")
            return stats
        
        # Estatísticas básicas
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        stats["total_messages"] = cursor.fetchone()[0]
        
        # Problemas comuns
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE embedding_id IS NULL OR embedding_id = ''")
        missing_embedding = cursor.fetchone()[0]
        if missing_embedding > 0:
            stats["sqlite_problems"].append(f"{missing_embedding} mensagens sem embedding_id")
            
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE user_id IS NULL OR chat_id IS NULL")
        invalid_ids = cursor.fetchone()[0]
        if invalid_ids > 0:
            stats["sqlite_problems"].append(f"{invalid_ids} mensagens com user_id ou chat_id nulos")
            
        # IDs duplicados
        cursor.execute("""
            SELECT embedding_id, COUNT(*) as count 
            FROM messages 
            WHERE embedding_id IS NOT NULL AND embedding_id != ''
            GROUP BY embedding_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            stats["sqlite_problems"].append(f"{len(duplicates)} embedding_ids duplicados")
            
        return stats
    except Exception as e:
        stats["status"] = "error"
        stats["sqlite_problems"].append(f"Erro ao conectar ao SQLite: {str(e)}")
        return stats

def check_chroma_integrity():
    """Verifica a integridade básica do ChromaDB"""
    stats = {
        "status": "ok",
        "total_documents": 0,
        "chroma_problems": [],
    }
    
    try:
        # Importa apenas se necessário
        from src.bot.memory.chroma_manager import ChromaManager
        
        # Verifica se o diretório existe
        chroma_dir = Path("./data/chroma_db")
        if not chroma_dir.exists():
            stats["status"] = "error"
            stats["chroma_problems"].append(f"Diretório do ChromaDB não existe: {chroma_dir}")
            return stats
            
        # Tenta inicializar o ChromaDB
        try:
            cm = ChromaManager()
            collection = cm.get_or_create_collection("messages")
            
            # Contagem de documentos
            try:
                # Tenta usar o método count() primeiro
                stats["total_documents"] = collection.count()
            except:
                # Se não tem o método count(), usa query vazia
                results = collection.query(
                    query_texts=[""],
                    n_results=1
                )
                stats["total_documents"] = len(results['ids'][0]) if results['ids'] else 0
                
        except Exception as e:
            stats["status"] = "error"
            stats["chroma_problems"].append(f"Erro ao inicializar ChromaDB: {str(e)}")
            
        return stats
    except Exception as e:
        stats["status"] = "error"
        stats["chroma_problems"].append(f"Erro ao importar dependências: {str(e)}")
        return stats

def get_message_sample(user_id=None, chat_id=None, limit=5):
    """Obtém uma amostra de mensagens recentes"""
    samples = []
    
    try:
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, chat_id, role, category, importance, 
                   substr(content, 1, 50) as preview, timestamp, embedding_id
            FROM messages 
        """
        
        params = []
        
        # Adiciona filtros se necessário
        if user_id is not None or chat_id is not None:
            conditions = []
            if user_id is not None:
                conditions.append("user_id = ?")
                params.append(user_id)
            if chat_id is not None:
                conditions.append("chat_id = ?")
                params.append(chat_id)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        # Ordenação e limite
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        
        for row in cursor.fetchall():
            samples.append(dict(row))
            
        return samples
    except Exception as e:
        logger.error(f"Erro ao buscar amostras: {e}")
        return []

def get_category_stats(user_id=None, chat_id=None):
    """Obtém estatísticas por categoria"""
    try:
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                category,
                COUNT(*) as count,
                ROUND(AVG(CAST(importance as FLOAT)), 1) as avg_importance,
                MAX(timestamp) as last_update
            FROM messages 
        """
        
        params = []
        
        # Adiciona filtros se necessário
        if user_id is not None or chat_id is not None:
            conditions = []
            if user_id is not None:
                conditions.append("user_id = ?")
                params.append(user_id)
            if chat_id is not None:
                conditions.append("chat_id = ?")
                params.append(chat_id)
                
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        # Agrupamento e ordenação
        query += " GROUP BY category ORDER BY count DESC"
        
        cursor.execute(query, tuple(params))
        
        results = []
        for row in cursor.fetchall():
            category_data = dict(row)
            # Formata a última atualização
            if 'last_update' in category_data and category_data['last_update']:
                category_data['last_update'] = format_time_ago(category_data['last_update'])
            results.append(category_data)
            
        return results
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas por categoria: {e}")
        return []

def print_memory_status(user_id=None, chat_id=None, show_samples=False):
    """Imprime o status atual da memória"""
    print("\n" + "="*80)
    print("📊 DIAGNÓSTICO DO SISTEMA DE MEMÓRIA 📊")
    print("="*80)
    
    # 1. Verifica integridade do SQLite
    sqlite_stats = check_sqlite_integrity()
    print("\n📁 STATUS DO BANCO SQLite:")
    print(f"  - Total de mensagens: {sqlite_stats['total_messages']}")
    
    if sqlite_stats['sqlite_problems']:
        print("  - ⚠️ Problemas encontrados:")
        for problem in sqlite_stats['sqlite_problems']:
            print(f"     * {problem}")
    else:
        print("  - ✅ Nenhum problema encontrado no SQLite")
    
    # 2. Verifica integridade do ChromaDB
    chroma_stats = check_chroma_integrity()
    print("\n🔍 STATUS DO BANCO VETORIAL (ChromaDB):")
    print(f"  - Total de documentos: {chroma_stats['total_documents']}")
    
    if chroma_stats['chroma_problems']:
        print("  - ⚠️ Problemas encontrados:")
        for problem in chroma_stats['chroma_problems']:
            print(f"     * {problem}")
    else:
        print("  - ✅ Nenhum problema encontrado no ChromaDB")
    
    # 3. Verifica sincronização
    print("\n🔄 SINCRONIZAÇÃO ENTRE BANCOS:")
    if sqlite_stats['total_messages'] == chroma_stats['total_documents']:
        print(f"  - ✅ Bancos sincronizados ({sqlite_stats['total_messages']} registros)")
    else:
        diff = abs(sqlite_stats['total_messages'] - chroma_stats['total_documents'])
        print(f"  - ⚠️ Divergência de {diff} registros")
        print(f"     * SQLite: {sqlite_stats['total_messages']} mensagens")
        print(f"     * ChromaDB: {chroma_stats['total_documents']} documentos")
        
        if sqlite_stats['total_messages'] > chroma_stats['total_documents']:
            print("     * Recomendação: Execute repair_memory.py para sincronizar")
    
    # 4. Estatísticas por categoria
    categories = get_category_stats(user_id, chat_id)
    
    filter_text = ""
    if user_id is not None:
        filter_text += f"user_id={user_id}"
    if chat_id is not None:
        filter_text += f" chat_id={chat_id}"
    
    print(f"\n📊 DISTRIBUIÇÃO POR CATEGORIA{' ('+filter_text+')' if filter_text else ''}:")
    
    if categories:
        # Formata como tabela
        table_data = []
        for cat in categories:
            table_data.append([
                cat['category'] or 'não-categorizado',
                cat['count'],
                cat['avg_importance'],
                cat['last_update'] or 'desconhecido'
            ])
        
        headers = ["Categoria", "Mensagens", "Importância Média", "Última Atualização"]
        print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        print("  - Nenhuma categoria encontrada")
    
    # 5. Amostra de mensagens
    if show_samples:
        samples = get_message_sample(user_id, chat_id, limit=5)
        
        print(f"\n📝 AMOSTRA DE MENSAGENS RECENTES{' ('+filter_text+')' if filter_text else ''}:")
        
        if samples:
            # Formata como tabela
            table_data = []
            for msg in samples:
                preview = (msg['preview'] + '...') if len(msg['preview']) >= 50 else msg['preview']
                table_data.append([
                    msg['id'],
                    msg['role'],
                    preview,
                    msg['category'] or 'não-categorizado',
                    msg['importance'] or '-',
                    format_time_ago(msg['timestamp']) if msg['timestamp'] else 'desconhecido'
                ])
            
            headers = ["ID", "Papel", "Conteúdo", "Categoria", "Imp.", "Quando"]
            print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            print("  - Nenhuma mensagem encontrada")
    
    print("\n" + "="*80)
    
    # 6. Recomendações
    if sqlite_stats['status'] == 'error' or chroma_stats['status'] == 'error' or sqlite_stats['sqlite_problems'] or chroma_stats['chroma_problems'] or sqlite_stats['total_messages'] != chroma_stats['total_documents']:
        print("\n⚠️ RECOMENDAÇÕES:")
        print("  - Execute 'python repair_memory.py' para corrigir problemas de sincronização")
        print("  - Use a opção --force se quiser reconstruir completamente o índice")
    else:
        print("\n✅ SISTEMA DE MEMÓRIA SAUDÁVEL")
        print("  - Executa 'python check_memory.py --sample' para ver amostras de mensagens")
    
    print("\n")

if __name__ == "__main__":
    # Parse argumentos
    parser = argparse.ArgumentParser(description="Verifica o estado da memória do bot")
    parser.add_argument("--user", type=int, help="Filtra por ID de usuário")
    parser.add_argument("--chat", type=int, help="Filtra por ID de chat")
    parser.add_argument("--sample", action="store_true", help="Mostra amostras de mensagens")
    
    args = parser.parse_args()
    
    try:
        # Verifica se o pacote tabulate está instalado
        try:
            from tabulate import tabulate
        except ImportError:
            print("⚠️ Pacote 'tabulate' não encontrado. Instale com: pip install tabulate")
            
            # Função de fallback simples
            def tabulate(data, headers, tablefmt):
                result = " | ".join(headers) + "\n"
                result += "-" * 80 + "\n"
                
                for row in data:
                    result += " | ".join(str(cell) for cell in row) + "\n"
                    
                return result
        
        # Executa o diagnóstico
        print_memory_status(args.user, args.chat, args.sample)
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n\n❌ Erro: {str(e)}")
        logger.exception("Erro durante verificação")