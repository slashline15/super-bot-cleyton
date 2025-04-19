# tests/test_memory_chroma.py
import sys
import os
import logging
from datetime import datetime

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório src ao path para importar os módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.bot.memory.memory_manager import MemoryManager

async def test_chroma_basic():
    """Teste básico das funcionalidades do ChromaDB"""
    try:
        # Inicializa o MemoryManager com um diretório de teste
        logger.info("Iniciando teste do ChromaDB...")
        memory = MemoryManager(persist_directory="./test_chroma_db")
        
        # Dados de teste
        user_id = 12345
        chat_id = 67890
        test_message = "Esta é uma mensagem de teste para validar o ChromaDB"
        
        # Teste 1: Adicionar mensagem
        logger.info("Teste 1: Adicionando mensagem...")
        await memory.add_message(
            user_id=user_id,
            chat_id=chat_id,
            content=test_message,
            role="user"
        )
        
        # Teste 2: Buscar contexto relevante
        logger.info("Teste 2: Buscando contexto...")
        context = await memory.get_relevant_context(
            query="mensagem de teste",
            user_id=user_id,
            chat_id=chat_id
        )
        
        # Verifica se encontrou a mensagem
        if context:
            logger.info(f"Mensagem encontrada: {context[0]['content']}")
        else:
            logger.warning("Nenhuma mensagem encontrada!")
            
        # Teste 3: Obter estatísticas
        logger.info("Teste 3: Obtendo estatísticas...")
        stats = await memory.get_category_stats(user_id, chat_id)
        logger.info(f"Estatísticas: {stats}")
        
        return "Testes concluídos com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_chroma_basic())
    print(result)