# tests/test_gemini_cli.py
"""
Script de teste em linha de comando para o cliente Gemini.
Permite testar a funcionalidade básica do cliente e alterar configurações.
Inclui processamento de arquivos e configurações dinâmicas.
"""

import os
from pathlib import Path
import sys
import mimetypes

# Adiciona o diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.bot.agents.gemini import GeminiClient, GeminiConfig
from dotenv import load_dotenv

def print_help():
    """Exibe ajuda com os comandos disponíveis."""
    print("\nComandos disponíveis:")
    print("  config                             - Mostra configuração atual")
    print("  set [param] [valor]                - Altera um parâmetro")
    print("  file [caminho]                     - Processa um arquivo")
    print("  help                               - Mostra esta ajuda")
    print("  sair                               - Encerra o programa")
    print("="*100)
    print("\nParâmetros disponíveis para 'set':")
    print("  temperature                        - Valor entre 0.0 e 1.0")
    print("  top_p                              - Valor entre 0.0 e 1.0")
    print("  top_k                              - Valor inteiro > 0")
    print("  max_output_tokens                  - Valor inteiro > 0")
    print("="*100)
    print("\nExemplos de uso do comando file:")
    print("  file docs/exemplo.txt")
    print("  file data/documento.pdf")




def get_mime_type(file_path):
    """Determina o tipo MIME do arquivo."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        # Fallback para text/plain se não conseguir determinar
        mime_type = "text/plain"
    return mime_type

def process_file(client, file_path, system_prompt=None):
    """
    Processa um arquivo usando o cliente Gemini.
    
    Args:
        client: Instância do GeminiClient
        file_path: Caminho do arquivo a ser processado
        system_prompt: Instrução opcional para processamento
    """
    try:
        # Verifica se arquivo existe
        if not os.path.exists(file_path):
            print(f"Erro: Arquivo não encontrado: {file_path}")
            return False
            
        # Determina tipo MIME
        mime_type = get_mime_type(file_path)
        print(f"\nProcessando arquivo: {file_path}")
        print(f"Tipo MIME: {mime_type}")
        
        # Upload do arquivo
        print("\nFazendo upload...")
        file = client.upload_file(file_path, mime_type=mime_type)
        
        # Aguarda processamento
        print("Aguardando processamento do arquivo...")
        active_file = client.wait_for_file_active(file)
        
        # Se não foi fornecido system_prompt, pede ao usuário
        if system_prompt is None:
            print("\nQual instrução você quer dar para o processamento do arquivo?")
            print("(Ex: 'Faça um resumo', 'Extraia os principais pontos', etc)")
            system_prompt = input("Instrução: ").strip()
        
        # Inicia chat com o arquivo
        print("\nIniciando análise...")
        chat = client.start_chat_session([{
            "role": "user",
            "parts": [active_file]
        }])
        
        # Envia instrução
        response = client.send_message(chat, system_prompt)
        
        # Exibe resultado
        print("\nResultado da análise:")
        print("-" * 100)
        print(response.text)
        print("-" * 100)
        

        return True
        
    except Exception as e:
        print(f"\nErro ao processar arquivo: {str(e)}")
        return False

def test_client_interactive():
    """Teste interativo do cliente Gemini via linha de comando."""
    print("\n=== Teste Interativo do Cliente Gemini ===\n")
    
    load_dotenv()
    
    try:
        print("Inicializando cliente Gemini...")
        config = GeminiConfig()
        client = GeminiClient(config=config)
        print("✓ Cliente inicializado com sucesso! ^_^ ")
        
        # Inicia sessão de chat
        print("▶ Iniciando sessão de chat...")
        chat = client.start_chat_session()
        print("❤ Sessão iniciada! ^_^ ")
        

        print_help()
        
        # Loop principal
        print("\nDigite suas mensagens (ou 'help' para ver comandos):")
        while True:
            try:
                # Obtém input do usuário
                user_input = input("\nVocê: ").strip()
                
                # Comandos especiais
                if user_input.lower() == 'sair':
                    print("\nEncerrando teste...")
                    break
                    
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                    
                elif user_input.lower() == 'config':
                    config = client.get_current_config()
                    print("\nConfigurações atuais:")
                    for key, value in config.to_dict().items():
                        print(f"  {key}: {value}")
                    continue
                
                elif user_input.lower().startswith('file '):
                    # Processa comando de arquivo
                    parts = user_input.split(maxsplit=1)
                    if len(parts) != 2:
                        print("Uso: file [caminho_do_arquivo]")
                        continue
                    
                    file_path = parts[1]
                    process_file(client, file_path)
                    continue
                
                elif user_input.lower().startswith('set '):
                    # Processa comando set
                    parts = user_input.split()
                    if len(parts) != 3:
                        print("Uso: set [parâmetro] [valor]")
                        continue
                        
                    _, param, value = parts
                    
                    try:
                        # Converte valor para o tipo apropriado
                        if param in ['temperature', 'top_p']:
                            value = float(value)
                        elif param in ['top_k', 'max_output_tokens']:
                            value = int(value)
                        else:
                            print(f"Parâmetro desconhecido: {param}")
                            continue
                        
                        # Cria nova configuração
                        new_config_dict = client.get_current_config().to_dict()
                        new_config_dict[param] = value
                        new_config = GeminiConfig(**new_config_dict)
                        
                        # Atualiza cliente
                        client.update_config(new_config)
                        print(f"✓ {param} atualizado para {value}")
                        
                        # Reinicia sessão de chat
                        chat = client.start_chat_session()
                        print("✓ Sessão reiniciada com nova configuração")
                        
                    except ValueError as e:
                        print(f"Erro ao atualizar configuração: {str(e)}")
                    continue
                
                # Ignora mensagens vazias
                if not user_input:
                    print("Por favor, digite uma mensagem.")
                    continue
                
                # Envia mensagem normal
                print("\nAguardando resposta...")
                response = client.send_message(chat, user_input)
                
                # Exibe resposta
                print("\nGemini:", response.text)
                
            except KeyboardInterrupt:
                print("\n\nEncerrando teste...")
                break
                
            except Exception as e:
                print(f"\nErro ao processar mensagem: {str(e)}")
                print("Tente novamente ou digite 'help' para ver os comandos.")
                print("Ou se não aguentar mais, digite 'sair' para sair (roteirista preguiçoso, poderia ter feito um 'exit' ou 'quit' ou 'Hasta la vista, baby').")
                print("="*100)
                print("="*100)
    


    except Exception as e:
        print(f"\nErro ao inicializar cliente: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_client_interactive()
    sys.exit(0 if success else 1)