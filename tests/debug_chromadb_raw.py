# python -m tests.debug_chromadb_raw
from src.bot.memory.chroma_manager import ChromaManager

client = ChromaManager.get_client()
collection = client.get_collection("messages")

# 1. Quantos documentos tem no total?
count = collection.count()
print(f"Total de documentos no ChromaDB: {count}")

# 2. Mostra os últimos 5 documentos que foram salvos
peek = collection.peek(limit=5)
print("\nÚltimos 5 documentos salvos:")
if peek['ids']:
    for i, id_ in enumerate(peek['ids']):
        print(f"ID: {id_}")
        print(f"Metadata: {peek['metadatas'][i]}")
        print(f"Conteúdo: {peek['documents'][i][:50]}...")
        print("-" * 50)

# 3. Tenta buscar sem nenhum filtro
results = collection.query(query_texts=["TESTE_UNICO"], n_results=5)
print(f"\nBusca sem filtro: {len(results['ids'][0]) if results['ids'] else 0} resultados")

# 4. Tenta buscar com apenas um filtro
results = collection.query(
    query_texts=["TESTE_UNICO"],
    where={"user_id": {"$eq": "999888"}},
    n_results=5
)
print(f"Busca com 1 filtro: {len(results['ids'][0]) if results['ids'] else 0} resultados")