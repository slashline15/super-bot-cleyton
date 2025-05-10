# python fix_memory.py
import os
import sqlite3
import json

# Verifique se existem mensagens no banco
try:
    con = sqlite3.connect('engenharia_bot.db')
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    
    # Verifica se a tabela messages existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    if not cursor.fetchone():
        print("❌ Tabela 'messages' não existe! Não há como recuperar mensagens.")
        exit(1)
    
    # Busca algumas mensagens recentes
    cursor.execute("SELECT user_id, chat_id, role, content FROM messages ORDER BY timestamp DESC LIMIT 5")
    msgs = cursor.fetchall()
    
    if not msgs:
        print("⚠️ Nenhuma mensagem encontrada no banco!")
    else:
        print(f"✅ Encontradas {len(msgs)} mensagens recentes")
        for msg in msgs:
            print(f"[{msg['user_id']}] {msg['role']}: {msg['content'][:30]}...")
    
    print("\n🔧 Consertando o código do agente LLM...")
    
    # Lê o arquivo llm_agent.py
    agent_path = 'src/bot/agents/llm_agent.py'
    with open(agent_path, 'r', encoding='utf-8') as f:
        agent_code = f.read()
    
    # Cria backup
    with open(f'{agent_path}.bak', 'w', encoding='utf-8') as f:
        f.write(agent_code)
    
    # Modifica o método get_context_messages para o mais simples possível
    new_method = '''
    async def get_context_messages(self, user_id: int, chat_id: int) -> list:
        """
        Recupera mensagens de contexto de forma simplificada
        """
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, Config.MAX_CONTEXT_MESSAGES))
                
                messages = cursor.fetchall()
                
                # Converte para o formato esperado
                context_messages = []
                for row in reversed(messages):
                    role, content = row
                    context_messages.append({
                        "role": role,
                        "content": content
                    })
                
                logger.info(f"Contexto recuperado: {len(context_messages)} mensagens")
                return context_messages
                
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {str(e)}", exc_info=True)
            return []
    '''
    
    # Substitui o método
    import re
    pattern = r'async def get_context_messages\(self, user_id: int, chat_id: int\).*?return \[\]\s*'
    replacement = new_method
    
    # Usa a flag re.DOTALL para incluir quebras de linha
    new_code = re.sub(pattern, replacement, agent_code, flags=re.DOTALL)
    
    # Escreve o código modificado
    with open(agent_path, 'w', encoding='utf-8') as f:
        f.write(new_code)
    
    print("✅ Código modificado com sucesso!")
    print("🚀 Reinicie o bot para aplicar as alterações!")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    raise