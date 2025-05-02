# python -m tests.test_llm_agent
import sys
import os
import asyncio
from pathlib import Path
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)

# Adiciona o diretório src ao PATH
src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(src_path))

from src.bot.agents.llm_agent import LLMAgent

async def test_llm_agent():
    """Testa a integração do LLMAgent com MemoryManager"""
    try:
        # Inicializa o agente
        agent = LLMAgent()
        
        # Dados de teste
        user_id = 123
        chat_id = 456
        
        print("\n🧪 Testando processamento de mensagens...")
        
        # Testa primeira mensagem
        response1 = await agent.process_message(
            "Preciso fazer um diário de obra para registrar o atraso na concretagem",
            user_id,
            chat_id
        )
        print("✓ Primeira mensagem processada")
        print(f"  Resposta: {response1[:100]}...")
        
        # Testa continuidade do contexto
        response2 = await agent.process_message(
            "Qual foi o último registro que fiz sobre a concretagem?",
            user_id,
            chat_id
        )
        print("✓ Segunda mensagem processada")
        print(f"  Resposta: {response2[:100]}...")
        
        # Testa estatísticas da memória
        print("\n📊 Testando estatísticas da memória...")
        stats = await agent.get_memory_stats(user_id, chat_id)
        
        # Verifica se retornou um dicionário válido
        assert isinstance(stats, dict), "Stats deve ser um dicionário"
        assert "categories" in stats, "Stats deve ter a chave 'categories'"
        assert "total_messages" in stats, "Stats deve ter a chave 'total_messages'"
        
        print(f"✓ Estatísticas obtidas: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando teste do LLMAgent...")
    success = asyncio.run(test_llm_agent())
    
    if success:
        print("\n✨ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1)