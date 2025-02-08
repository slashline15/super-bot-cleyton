# src/bot/memory/document_manager.py
import logging
from typing import List, Dict, Optional
import chromadb
from datetime import datetime
from bot.database.db_init import Database

logger = logging.getLogger('DocumentManager')

class DocumentManager:
    def __init__(self, memory_manager):
        """
        Inicializa o gerenciador de documentos.
        
        Args:
            memory_manager: Instância do MemoryManager para acessar ChromaDB
        """
        self.memory = memory_manager
        self.db = Database()
        self.documents_collection = self.memory.client.get_or_create_collection(
            name="documents",
            metadata={"description": "Documentos e textos longos processados"}
        )
        logger.info("DocumentManager inicializado")
    
    async def add_document(
        self,
        content: str,
        metadata: Dict,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> str:
        """
        Adiciona um documento dividindo em chunks menores.
        
        Args:
            content: Texto do documento
            metadata: Metadados do documento (título, tipo, etc)
            chunk_size: Tamanho de cada chunk
            chunk_overlap: Sobreposição entre chunks
            
        Returns:
            str: ID do documento
        """
        try:
            # Gera um ID único para o documento
            doc_id = f"doc_{datetime.now().timestamp()}"
            
            # Divide o texto em chunks
            chunks = self._split_text(content, chunk_size, chunk_overlap)
            
            # Prepara os metadados para cada chunk
            chunk_metadatas = []
            chunk_ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_metadata = {
                    **metadata,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                chunk_metadatas.append(chunk_metadata)
                chunk_ids.append(chunk_id)
            
            # Adiciona os chunks ao ChromaDB
            self.documents_collection.add(
                documents=chunks,
                metadatas=chunk_metadatas,
                ids=chunk_ids
            )
            
            # Registra o documento no SQLite
            self.db.execute_query(
                """
                INSERT INTO documents 
                (doc_id, title, doc_type, total_chunks, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc_id, metadata.get('title'), metadata.get('type'), 
                 len(chunks), str(metadata))
            )
            
            logger.info(f"Documento {doc_id} adicionado com {len(chunks)} chunks")
            return doc_id
            
        except Exception as e:
            logger.error(f"Erro ao adicionar documento: {str(e)}")
            raise

    async def search_documents(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Busca documentos relevantes para uma query.
        
        Args:
            query: Texto para buscar
            filters: Filtros para a busca (tipo de documento, data, etc)
            limit: Número máximo de resultados
            
        Returns:
            Lista de documentos encontrados com seus metadados
        """
        try:
            # Prepara o filtro do ChromaDB
            where_filter = None
            if filters:
                # Aplica os filtros diretamente sem usar $and
                where_filter = {}
                for key, value in filters.items():
                    where_filter[key] = {"$eq": value}
            
            # Realiza a busca
            results = self.documents_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )
            
            # Organiza os resultados
            documents = []
            if results['ids']:
                for i in range(len(results['ids'][0])):
                    doc = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i]
                    }
                    documents.append(doc)
            
            logger.info(f"Busca retornou {len(documents)} resultados")
            return documents
            
        except Exception as e:
            logger.error(f"Erro na busca de documentos: {str(e)}")
            raise

    def _split_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """
        Divide um texto em chunks menores com sobreposição.
        
        Args:
            text: Texto a ser dividido
            chunk_size: Tamanho de cada chunk
            overlap: Sobreposição entre chunks
            
        Returns:
            Lista de chunks de texto
        """
        words = text.split()
        chunks = []
        start = 0
        
        while start < len(words):
            # Define o fim do chunk atual
            end = start + chunk_size
            
            # Se não é o último chunk, ajusta para não cortar palavras
            if end < len(words):
                # Procura um ponto final ou espaço próximo ao tamanho desejado
                while end > start and not (
                    words[end-1].endswith('.') or 
                    words[end-1].endswith('!') or 
                    words[end-1].endswith('?')
                ):
                    end -= 1
                # Se não encontrou pontuação, usa espaço
                if end == start:
                    end = start + chunk_size
            
            # Cria o chunk
            chunk = ' '.join(words[start:end])
            chunks.append(chunk)
            
            # Atualiza o início do próximo chunk considerando a sobreposição
            start = end - overlap
        
        return chunks