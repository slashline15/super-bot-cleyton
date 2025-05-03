# python -m tests.test_memory_persistence
import sys
import os
from pathlib import Path
import asyncio
import uuid

# Adiciona o diretório raiz ao PATH
sys.path.append(str(Path(__file__).parent.parent))

from src.bot.memory.memory_manager import MemoryManager

async def test_persistence():
    """Testa se os dados estão persistindo no ChromaDB"""
    try:
        # Usa um identificador único para o teste
        test_id = str(uuid.uuid4())
        
        # Cria um conteúdo de teste único
        test_content = f"Mensagem de teste para persistência: {test_id}"
        print(f"\nUsando conteúdo de teste: {test_content}")
        
        # Inicializa o MemoryManager com o diretório padrão
        print("\n1. Inicializando MemoryManager...")
        memory = MemoryManager()
        
        # Adiciona uma mensagem
        print("\n2. Adicionando mensagem de teste...")
        await memory.add_message(
            user_id=12345,
            chat_id=67890,
            content=test_content,
            role="user"
        )
        print("✓ Mensagem adicionada")
        
        # Reinicializa o MemoryManager para simular reinício do bot
        print("\n3. Reinicializando MemoryManager para simular reinício...")
        memory = MemoryManager()
        
        # Busca a mensagem usando o conteúdo exato
        print("\n4. Buscando mensagem após reinicialização...")
        results = await memory.get_relevant_context(
            query=test_id,  # Usamos parte do ID para busca
            user_id=12345,
            chat_id=67890,
            limit=5
        )
        
        # Verifica se encontrou a mensagem
        if results and any(test_id in result.get('content', '') for result in results):
            print("✅ SUCESSO: Mensagem persistiu após reinicialização!")
            for result in results:
                print(f"- Conteúdo: {result.get('content', '')[:50]}...")
            return True
        else:
            print("❌ FALHA: Mensagem não persistiu após reinicialização")
            print(f"Resultados encontrados: {len(results) if results else 0}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        return False
        
if __name__ == "__main__":
    print("🧪 Teste de Persistência do ChromaDB")
    result = asyncio.run(test_persistence())
    
    if not result:
        print("\n⚠️ O ChromaDB não está persistindo dados corretamente!")
        print("Possíveis causas:")
        print("1. Diretório de persistência incorreto")
        print("2. Permissões de escrita no diretório")
        print("3. Problemas na inicialização do ChromaDB")