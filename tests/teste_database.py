# python -m tests.teste_database
import sys
import os
import sqlite3
import logging
from pathlib import Path

# Adiciona o diretório src ao PATH para importar os módulos
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

from src.bot.database.db_init import Database

def test_database_migration():
    """Testa se a migração do banco de dados foi bem sucedida"""
    try:
        # Usa um banco de teste
        test_db = Database('test_database.db')
        
        # Verifica se as novas colunas existem
        with test_db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(messages)")
            columns = {col['name'] for col in cursor.fetchall()}
            
            # Verifica cada coluna
            expected_columns = {
                'category', 'importance', 'embedding_id',
                'id', 'user_id', 'role', 'content', 'chat_id',
                'context_id', 'timestamp', 'tokens'
            }
            
            missing_columns = expected_columns - columns
            if missing_columns:
                print(f"❌ Erro: Colunas faltando: {missing_columns}")
                return False
                
            print("✅ Todas as colunas esperadas estão presentes!")
            return True
            
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False
    finally:
        # Limpa o banco de teste
        if os.path.exists('test_database.db'):
            os.remove('test_database.db')
            print("🧹 Banco de teste removido")

if __name__ == "__main__":
    # Configura logging básico
    logging.basicConfig(level=logging.INFO)
    
    # Executa o teste
    print("🚀 Iniciando teste de migração do banco...")
    success = test_database_migration()
    
    if success:
        print("✨ Teste concluído com sucesso!")
    else:
        print("❌ Teste falhou!")
        sys.exit(1)