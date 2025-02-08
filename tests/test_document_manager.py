# tests/test_document_manager.py
import sys
import os
import logging
from datetime import datetime

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bot.memory.memory_manager import MemoryManager
from bot.memory.document_manager import DocumentManager

async def test_document_processing():
    """Teste das funcionalidades do DocumentManager"""
    try:
        # Inicializa os gerenciadores
        logger.info("Iniciando teste do DocumentManager...")
        memory = MemoryManager(persist_directory="./test_chroma_db")
        doc_manager = DocumentManager(memory)
        
        # Documento de teste
        test_document = """
        Este é um documento de teste que será dividido em chunks menores.
        Vamos adicionar várias frases para ter certeza que o texto será
        dividido corretamente. Este texto precisa ser grande o suficiente
        para gerar pelo menos 2 ou 3 chunks diferentes.
        
        Cada chunk deve ter um tamanho razoável e manter a coerência do texto.
        A sobreposição entre os chunks ajuda a manter o contexto quando
        realizamos buscas posteriormente.
        
        Este é o último parágrafo do nosso texto de teste. Vamos ver como
        o sistema lida com a divisão e depois com a busca por conteúdo
        específico dentro destes chunks.
        """
        
        # Metadados do documento
        metadata = {
            "title": "Documento de Teste",
            "type": "text",
            "author": "Test User",
            "created_at": datetime.now().isoformat()
        }
        
        # Teste 1: Adicionar documento
        logger.info("Teste 1: Adicionando documento...")
        doc_id = await doc_manager.add_document(
            content=test_document,
            metadata=metadata,
            chunk_size=100,  # Tamanho menor para teste
            chunk_overlap=20
        )
        
        # Teste 2: Buscar conteúdo
        logger.info("Teste 2: Buscando conteúdo...")
        results = await doc_manager.search_documents(
            query="chunks diferentes",
            filters={"type": "text"}
        )
        
        # Verifica os resultados
        if results:
            logger.info(f"Encontrados {len(results)} resultados")
            for i, result in enumerate(results, 1):
                logger.info(f"Resultado {i}:")
                logger.info(f"- Conteúdo: {result['content'][:100]}...")
                logger.info(f"- Metadados: {result['metadata']}")
        else:
            logger.warning("Nenhum resultado encontrado!")
        
        return "Testes do DocumentManager concluídos com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_document_processing())
    print(result)