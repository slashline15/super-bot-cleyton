import sqlite3
import datetime
from dotenv import load_dotenv
import os

def test_database():
    print("\n🔄 Iniciando testes do banco de dados...\n")
    
    try:
        # Conecta ao banco de dados
        conn = sqlite3.connect('engenharia_bot.db')
        cursor = conn.cursor()
        
        # 1. Teste de inserção de usuário
        print("1️⃣ Testando inserção de usuário...")
        cursor.execute('''
            INSERT OR IGNORE INTO usuarios (telegram_id, nome)
            VALUES (123456, 'Usuário Teste')
        ''')
        
        # 2. Teste de inserção no diário de obra
        print("2️⃣ Testando inserção no diário de obra...")
        cursor.execute('''
            INSERT INTO diario_obra (telegram_id, data, descricao, clima, efetivo, fotos)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            123456,
            datetime.date.today().isoformat(),
            'Teste de fundação concluído',
            'Ensolarado',
            10,
            'foto1.jpg,foto2.jpg'
        ))
        
        # 3. Teste de inserção financeira
        print("3️⃣ Testando inserção financeira...")
        cursor.execute('''
            INSERT INTO financeiro (telegram_id, data, tipo, categoria, valor, descricao)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            123456,
            datetime.date.today().isoformat(),
            'despesa',
            'material',
            1500.50,
            'Compra de cimento'
        ))
        
        # Commit das alterações
        conn.commit()
        
        # 4. Teste de consultas
        print("\n📊 Testando consultas...")
        
        # Consulta usuário
        cursor.execute('SELECT * FROM usuarios WHERE telegram_id = 123456')
        usuario = cursor.fetchone()
        print(f"\nUsuário encontrado: {usuario}")
        
        # Consulta diário
        cursor.execute('SELECT * FROM diario_obra WHERE telegram_id = 123456')
        diario = cursor.fetchone()
        print(f"\nDiário encontrado: {diario}")
        
        # Consulta financeiro
        cursor.execute('SELECT * FROM financeiro WHERE telegram_id = 123456')
        financeiro = cursor.fetchone()
        print(f"\nRegistro financeiro encontrado: {financeiro}")
        
        # 5. Teste de atualização
        print("\n🔄 Testando atualizações...")
        cursor.execute('''
            UPDATE diario_obra 
            SET descricao = 'Teste de fundação concluído - Atualizado'
            WHERE telegram_id = 123456
        ''')
        
        # Verifica atualização
        cursor.execute('SELECT descricao FROM diario_obra WHERE telegram_id = 123456')
        descricao_atualizada = cursor.fetchone()[0]
        print(f"\nDescrição atualizada: {descricao_atualizada}")
        
        # 6. Teste de remoção
        print("\n🗑️ Testando remoção...")
        cursor.execute('DELETE FROM financeiro WHERE telegram_id = 123456')
        
        # Verifica remoção
        cursor.execute('SELECT * FROM financeiro WHERE telegram_id = 123456')
        registro_removido = cursor.fetchone()
        print(f"Registro financeiro após remoção: {registro_removido}")
        
        conn.commit()
        print("\n✅ Todos os testes concluídos com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {str(e)}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    load_dotenv()
    test_database()
