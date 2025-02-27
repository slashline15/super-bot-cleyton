# tests/test_database.py
import sqlite3
import datetime
import os
import logging
from dotenv import load_dotenv

# Importa a classe Database para inicializar as tabelas
from src.bot.database.db_init import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database():
    print("\n🔄 Iniciando testes do banco de dados...\n")
    
    test_db = 'test_database.db'
    try:
        # Primeiro inicializa o banco com a estrutura correta
        db = Database(db_name=test_db)
        print("✓ Banco de dados inicializado")
        
        # Agora conecta para os testes
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # 1. Testa inserção na tabela messages
        print("\n1️⃣ Testando mensagens...")
        cursor.execute('''
            INSERT INTO messages 
            (user_id, role, content, chat_id, category, importance) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            123456,
            'user',
            'Teste de mensagem',
            789,
            'diario_obra',
            3
        ))
        print("✓ Mensagem inserida")
        
        # 2. Testa inserção na tabela documents
        print("\n2️⃣ Testando documentos...")
        cursor.execute('''
            INSERT INTO documents 
            (doc_id, title, doc_type, total_chunks, metadata) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'doc_123',
            'Documento de Teste',
            'text',
            3,
            '{"author": "Test User"}'
        ))
        print("✓ Documento inserido")
        
        # Commit das alterações
        conn.commit()
        
        # 3. Testa consultas
        print("\n📊 Testando consultas...")
        
        # Consulta mensagens
        cursor.execute('SELECT * FROM messages WHERE user_id = 123456')
        messages = cursor.fetchone()
        print(f"Mensagem encontrada: {messages}")
        
        # Consulta documentos
        cursor.execute('SELECT * FROM documents WHERE doc_id = "doc_123"')
        document = cursor.fetchone()
        print(f"Documento encontrado: {document}")
        
        # 4. Testa atualizações
        print("\n🔄 Testando atualizações...")
        cursor.execute('''
            UPDATE messages 
            SET content = 'Mensagem atualizada'
            WHERE user_id = 123456
        ''')
        
        # Verifica atualização
        cursor.execute('SELECT content FROM messages WHERE user_id = 123456')
        content_updated = cursor.fetchone()[0]
        print(f"Conteúdo atualizado: {content_updated}")
        
        conn.commit()
        print("\n✅ Todos os testes concluídos com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {str(e)}")
        
    finally:
        # Fecha conexão se estiver aberta
        if 'conn' in locals():
            conn.close()
            
        # Remove banco de teste
        if os.path.exists(test_db):
            os.remove(test_db)
            print("\n🧹 Banco de teste removido")

if __name__ == "__main__":
    load_dotenv()
    test_database()