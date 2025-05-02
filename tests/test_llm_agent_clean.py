# python -m tests.test_llm_agent_clean
import sys
import os
import asyncio
import importlib

# Força recarregamento dos módulos de configuração
if 'src.config.config' in sys.modules:
    importlib.reload(sys.modules['src.config.config'])

# Configura o provider via variável de ambiente para o teste específico
os.environ['LLM_PROVIDER'] = 'gemini'  # ou 'openai'

# Importações após configuração do ambiente
from src.bot.agents.llm_agent import LLMAgent

async def test_agent():
    print("Iniciando teste com LLMAgent...")
    agent = LLMAgent()
    print(f"Provedor: {agent._client.provider}, Modelo: {agent._client.name}")
    
    response = await agent.process_message(
        "Olá, estou testando a integração com LLMs. Me responda como se fosse o Rick de Rick and Morty.", 
        user_id=1, 
        chat_id=1
    )
    print(f"\nResposta:\n{response}")

if __name__ == "__main__":
    asyncio.run(test_agent())