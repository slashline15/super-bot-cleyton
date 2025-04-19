import chromadb

# Testa conexão com ChromaDB
try:
    client = chromadb.PersistentClient(path="./chroma_db")
    print("✅ ChromaDB conectado com sucesso!")
    collection = client.get_or_create_collection(name="test_collection")
    print("✅ Coleção criada com sucesso!")
except Exception as e:
    print(f"❌ Erro ao conectar ao ChromaDB: {e}")