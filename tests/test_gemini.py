# tests/test_gemini.py
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.bot.agents.gemini import GeminiClient, GeminiConfig

def test_gemini():
    """Testa a funcionalidade básica do cliente Gemini."""
    
    # Carrega variáveis de ambiente
    load_dotenv()
    
    # Debug: mostra a API key (com ****)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        masked_key = f"{api_key[:8]}{'*' * (len(api_key)-12)}{api_key[-4:]}"
        print(f"API Key encontrada: {masked_key}")
    else:
        print("❌ API Key não encontrada!")
        return False
    
    try:
        # Cria uma configuração de teste
        print("\n1. Criando configuração...")
        config = GeminiConfig(
            temperature=0.7,
            max_output_tokens=2000
        )
        print("✅ Configuração criada")
        print(f"Configuração atual: {config.to_dict()}")
        
        # Inicializa o cliente
        print("\n2. Inicializando cliente...")
        client = GeminiClient(config=config)
        print("✅ Cliente iniciado com sucesso!")
        
        # Inicia sessão de chat
        print("\n3. Iniciando sessão de chat...")
        chat = client.start_chat_session()
        print("✅ Sessão de chat iniciada!")
        
        # Prepara mensagem de teste
        test_message = "Olá! Por favor, me responda com uma frase curta."
        print(f"\n4. Preparando mensagem de teste: '{test_message}'")
        
        # Envia a mensagem
        print("\n5. Enviando mensagem...")
        try:
            response = client.send_message(chat, test_message)
            print("✅ Mensagem enviada e resposta recebida!")
            print("\nResposta do modelo:")
            print(response.text)
            print(f"Tokens usados: {client.token_cost(response)}")
        except Exception as chat_error:
            print(f"❌ Erro ao enviar mensagem: {str(chat_error)}")
            print(f"Tipo do erro no chat: {type(chat_error)}")
            raise
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro geral: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        import traceback
        print("\nStack trace completo:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🚀 Iniciando teste do cliente Gemini...")
    success = test_gemini()
    if success:
        print("\n✅ Teste concluído com sucesso!")
    else:
        print("\n❌ Teste falhou!")
        sys.exit(1)