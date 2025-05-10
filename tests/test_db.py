# python -m tests.test_db

import sqlite3

# Conecta ao banco de dados
conn = sqlite3.connect('engenharia_bot.db')
conn.row_factory = sqlite3.Row

# Busca as mensagens
cursor = conn.cursor()
cursor.execute('SELECT * FROM messages ORDER BY timestamp DESC LIMIT 10')
rows = cursor.fetchall()

# Mostra as mensagens encontradas
if rows:
    print(f"✅ Encontradas {len(rows)} mensagens:")
    for row in rows:
        print(f"- User {row['user_id']}: {row['content'][:30]}...")
else:
    print("❌ Nenhuma mensagem encontrada no banco de dados!")

conn.close()