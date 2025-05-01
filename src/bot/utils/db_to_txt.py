"""
Script para visualizar o conteúdo do banco de dados SQLite em um arquivo de texto formatado.
Facilita a visualização rápida dos dados sem precisar de ferramentas externas.

Uso:
    python db_to_txt.py [opções]
    python -m src.bot.utils.db_to_txt

Opções:
    --db NOME_DB     Nome do arquivo do banco de dados (padrão: engenharia_bot.db)
    --output ARQUIVO Nome do arquivo de saída (padrão: db_messages.txt)
    --limit N        Limitar a N registros (padrão: 50)
    --order ASC/DESC Ordem cronológica (padrão: DESC - mais recentes primeiro)
"""

import sqlite3
import sys
import os
import datetime
from pathlib import Path

def connect_db(db_name="engenharia_bot.db"):
    """Conecta ao banco de dados SQLite e retorna a conexão."""
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row  # Para acessar colunas pelo nome
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco: {e}")
        sys.exit(1)

def get_messages(conn, limit=50, order="DESC"):
    """Busca mensagens no banco de dados."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, user_id, role, content, chat_id, 
                  timestamp, category, importance, embedding_id
            FROM messages
            ORDER BY timestamp {order}
            LIMIT {limit}
        """)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao buscar mensagens: {e}")
        return []

def format_message(message, show_id=True):
    """Formata uma mensagem para exibição."""
    role_emoji = "🧑" if message["role"] == "user" else "🤖"
    category = message["category"] or "sem categoria"
    importance = message["importance"] or "0"
    
    # Formata a data/hora
    try:
        timestamp = datetime.datetime.fromisoformat(message["timestamp"])
        time_str = timestamp.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        time_str = message["timestamp"] or "desconhecido"
    
    # ID da mensagem (opcional)
    id_str = f"[ID: {message['id']}] " if show_id else ""
    
    # Cabeçalho da mensagem
    header = f"\n{'-'*80}\n{id_str}{role_emoji} {message['role'].upper()} (User: {message['user_id']}, Chat: {message['chat_id']})"
    header += f"\n📅 {time_str} | 🏷️ {category} | ⭐ Importância: {importance}\n{'-'*80}\n"
    
    # Conteúdo da mensagem
    content = message["content"]
    
    return header + content

def save_to_file(messages, filename="db_messages.txt"):
    """Salva as mensagens em um arquivo de texto."""
    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(f"MENSAGENS DO BANCO DE DADOS - {datetime.datetime.now()}\n")
            file.write(f"Total de registros: {len(messages)}\n\n")
            
            for msg in messages:
                file.write(format_message(msg))
                file.write("\n\n")
                
        print(f"✅ Arquivo salvo com sucesso: {filename}")
        print(f"   {len(messages)} mensagens exportadas.")
        
        # Mostra o caminho completo do arquivo
        abs_path = os.path.abspath(filename)
        print(f"   Caminho completo: {abs_path}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar arquivo: {e}")

def parse_args():
    """Processa argumentos da linha de comando."""
    args = {
        "db": "engenharia_bot.db",
        "output": "db_messages.txt",
        "limit": 50,
        "order": "DESC"
    }
    
    # Processamento básico de argumentos
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--db" and i+1 < len(sys.argv):
            args["db"] = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == "--output" and i+1 < len(sys.argv):
            args["output"] = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == "--limit" and i+1 < len(sys.argv):
            try:
                args["limit"] = int(sys.argv[i+1])
                i += 2
            except ValueError:
                print(f"Valor inválido para limit: {sys.argv[i+1]}")
                i += 2
        elif sys.argv[i] == "--order" and i+1 < len(sys.argv):
            if sys.argv[i+1].upper() in ["ASC", "DESC"]:
                args["order"] = sys.argv[i+1].upper()
            i += 2
        else:
            i += 1
            
    return args

def main():
    """Função principal do script."""
    # Processa argumentos
    args = parse_args()
    
    print(f"🔄 Conectando ao banco de dados: {args['db']}")
    conn = connect_db(args["db"])
    
    print(f"🔍 Buscando mensagens (limit: {args['limit']}, order: {args['order']})")
    messages = get_messages(conn, args["limit"], args["order"])
    
    if not messages:
        print("❌ Nenhuma mensagem encontrada no banco de dados.")
        return
    
    print(f"📝 Formatando e salvando {len(messages)} mensagens...")
    save_to_file(messages, args["output"])
    
    # Fecha a conexão
    conn.close()

if __name__ == "__main__":
    print("\n🤖 DB to TXT - Visualizador de mensagens\n")
    main()
    print("\n✨ Processo concluído!")