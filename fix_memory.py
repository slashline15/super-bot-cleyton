# python fix_memory.py
"""
Script para reparo rápido do sistema de memória.

Este script faz uma correção mais simples, focada em:
1. Corrigir o método get_context_messages do LLMAgent
2. Verificar se há mensagens sem embedding_id e corrigi-las 

Para um reparo completo, use repair_memory.py
"""

import os
import sys
import sqlite3
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('fix_memory')

def backup_file(file_path):
    """Faz backup de um arquivo antes de modificá-lo"""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return False

def fix_agent_code():
    """Corrige o código do agente LLM"""
    agent_path = 'src/bot/agents/llm_agent.py'
    
    # Verifica se o arquivo existe
    if not os.path.exists(agent_path):
        print(f"❌ Arquivo {agent_path} não encontrado!")
        return False
    
    # Faz backup do arquivo
    if not backup_file(agent_path):
        print("❌ Abortando operação por falha no backup!")
        return False
    
    try:
        # Lê o arquivo
        with open(agent_path, 'r', encoding='utf-8') as f:
            agent_code = f.read()
        
        # Verifica se o código já foi modificado
        if "# Método simplificado por fix_memory.py" in agent_code:
            print("✅ Código já foi corrigido anteriormente!")
            return True
            
        # Modifica o método get_context_messages para o mais simples possível
        new_method = '''
    async def get_context_messages(self, user_id: int, chat_id: int, query: str = "") -> List[Dict[str, str]]:
        """
        Recupera mensagens de contexto de forma simplificada
        # Método simplificado por fix_memory.py
        """
        try:
            # Delega para o MemoryManager
            return await self.memory.get_context_messages(
                user_id=user_id,
                chat_id=chat_id,
                query=query
            )
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {str(e)}", exc_info=True)
            
            # Fallback: busca direta no banco de dados
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
                    
                    rows = cursor.fetchall()
                    return [
                        {"role": row[0], "content": row[1]} 
                        for row in reversed(rows)
                    ]
            except Exception as db_error:
                logger.error(f"Erro no fallback do banco: {db_error}")
                return []
        '''
        
        # Substitui o método
        pattern = r'async def get_context_messages\(self, user_id: int, chat_id: int, query: str = ""\).*?return \[\]\s*'
        replacement = new_method
        
        # Usa a flag re.DOTALL para incluir quebras de linha
        new_code = re.sub(pattern, replacement, agent_code, flags=re.DOTALL)
        
        # Verifica se houve substituição
        if new_code == agent_code:
            print("⚠️ Nenhuma alteração foi feita no código!")
            return False
        
        # Escreve o código modificado
        with open(agent_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        
        print("✅ Código do agente modificado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao modificar código: {e}")
        return False

def fix_missing_embeddings():
    """
    Corrige mensagens sem embedding_id,
    atualizando o banco de dados SQLite para que o repair_memory.py possa corrigir mais tarde.
    """
    try:
        print("\n🔍 Verificando mensagens sem embedding_id...")
        
        # Conecta ao banco
        conn = sqlite3.connect('engenharia_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verifica se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if not cursor.fetchone():
            print("❌ Tabela 'messages' não existe! Não há como recuperar mensagens.")
            return False
        
        # Conta mensagens sem embedding_id
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE embedding_id IS NULL OR embedding_id = ''")
        missing_count = cursor.fetchone()[0]
        
        if missing_count == 0:
            print("✅ Não há mensagens sem embedding_id!")
            return True
        
        print(f"⚠️ Encontradas {missing_count} mensagens sem embedding_id.")
        
        # Gera embedding_ids temporários
        print(f"🔄 Gerando embedding_ids temporários...")
        
        cursor.execute("""
            SELECT id, user_id FROM messages 
            WHERE embedding_id IS NULL OR embedding_id = ''
            LIMIT 100
        """)
        
        messages = cursor.fetchall()
        fixed_count = 0
        
        for msg in messages:
            msg_id = msg['id']
            user_id = msg['user_id']
            
            # Gera um embedding_id temporário
            embedding_id = f"tmp_fix_{user_id}_{msg_id}_{datetime.now().timestamp()}"
            
            # Atualiza no banco
            cursor.execute(
                "UPDATE messages SET embedding_id = ? WHERE id = ?",
                (embedding_id, msg_id)
            )
            
            fixed_count += 1
        
        # Commit das alterações
        conn.commit()
        
        print(f"✅ Corrigidas {fixed_count} mensagens no SQLite!")
        
        if fixed_count < missing_count:
            print(f"⚠️ Ainda restam {missing_count - fixed_count} mensagens para corrigir.")
            print("🔧 Execute repair_memory.py para uma correção completa.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir embedding_ids: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔧 INICIANDO REPARO RÁPIDO DA MEMÓRIA 🔧")
    print("="*60)
    
    # Adiciona o diretório do projeto ao path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Verifica se existem mensagens no banco
        try:
            conn = sqlite3.connect('engenharia_bot.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
            
        except Exception as e:
            print(f"❌ Erro ao verificar banco: {e}")
            exit(1)
        
        # Corrige o código do agente LLM
        print("\n🔧 Corrigindo o código do agente LLM...")
        fix_agent_code()
        
        # Corrige mensagens sem embedding_id
        print("\n🔧 Corrigindo mensagens sem embedding_id...")
        fix_missing_embeddings()
        
        print("\n" + "="*60)
        print("🎉 REPARO RÁPIDO CONCLUÍDO! 🎉")
        print("="*60)
        print("\nPara um reparo completo, execute:")
        print("  python repair_memory.py")
        print("\nPara verificar o estado atual da memória, execute:")
        print("  python check_memory.py")
        print("\n🚀 Reinicie o bot para aplicar as alterações!")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        logger.exception("Erro durante reparo rápido")
        raise