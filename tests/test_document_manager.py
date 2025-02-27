# tests/test_document_manager.py
import sys
import os
import logging
from datetime import datetime
import tempfile
import uuid
import shutil
import asyncio

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from bot.memory.memory_manager import MemoryManager
from bot.memory.document_manager import DocumentManager

async def test_document_processing():
    """Teste das funcionalidades do DocumentManager"""
    # Cria um diretório temporário único
    test_dir = os.path.join(tempfile.gettempdir(), f"test_chroma_{uuid.uuid4().hex}")
    
    try:
        # Inicializa os gerenciadores
        logger.info(f"Iniciando teste do DocumentManager em {test_dir}...")
        memory = MemoryManager(persist_directory=test_dir)
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
        
        # Verifica se o documento foi adicionado
        assert doc_id is not None, "Documento não foi adicionado corretamente"
        
        # Teste 2: Buscar sem filtros
        logger.info("Teste 2: Buscando conteúdo...")
        results = await doc_manager.search_documents(
            query="chunks diferentes",
            limit=5
        )
        
        # Verifica os resultados da busca
        assert results is not None, "Busca não retornou resultados"
        assert len(results) > 0, "Nenhum resultado encontrado"
        
        if results:
            logger.info(f"Encontrados {len(results)} resultados")
            for i, result in enumerate(results, 1):
                logger.info(f"Resultado {i}:")
                logger.info(f"- Conteúdo: {result['content'][:100]}...")
                logger.info(f"- Metadados: {result['metadata']}")
                
                # Verifica metadados essenciais
                assert 'doc_id' in result['metadata'], "doc_id não encontrado nos metadados"
                assert 'chunk_index' in result['metadata'], "chunk_index não encontrado nos metadados"
                assert 'total_chunks' in result['metadata'], "total_chunks não encontrado nos metadados"
        
        # Teste 3: Buscar com filtros
        logger.info("Teste 3: Buscando com filtros...")
        filtered_results = await doc_manager.search_documents(
            query="teste",
            filters={"type": "text"},
            limit=2
        )
        
        # Verifica os resultados filtrados
        assert len(filtered_results) > 0, "Busca filtrada não retornou resultados"
        assert filtered_results[0]['metadata']['type'] == 'text', "Filtro de tipo não funcionou"
        
        return "Testes do DocumentManager concluídos com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro durante os testes: {str(e)}")
        raise
        
    finally:
        # Aguarda um momento antes de tentar limpar
        await asyncio.sleep(1)
        
        # Tenta limpar o diretório de teste
        try:
            # Força o garbage collector para liberar recursos
            import gc
            gc.collect()
            
            if os.path.exists(test_dir):
                # Em Windows, às vezes precisamos de múltiplas tentativas
                for _ in range(3):
                    try:
                        shutil.rmtree(test_dir, ignore_errors=True)
                        if not os.path.exists(test_dir):
                            logger.info("Diretório de teste removido com sucesso")
                            break
                        await asyncio.sleep(1)
                    except Exception:
                        continue
                else:
                    logger.warning(f"Não foi possível remover o diretório de teste: {test_dir}")
        except Exception as e:
            logger.error(f"Erro ao limpar diretório de teste: {e}")

if __name__ == "__main__":
    result = asyncio.run(test_document_processing())
    print(result)