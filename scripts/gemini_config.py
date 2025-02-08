# scripts/gemini_config.py
"""
Interface Streamlit para configuração e teste do modelo Gemini.
"""

import json
import os
import streamlit as st
from pathlib import Path
import sys

# Adiciona o diretório src ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.bot.agents.gemini import GeminiClient, GeminiConfig

# Configuração da página Streamlit
st.set_page_config(
    page_title="Configuração Gemini",
    page_icon="🤖",
    layout="wide"
)

def load_config():
    """Carrega configuração salva ou usa padrão."""
    config_path = Path("config/gemini_config.json")
    if config_path.exists():
        with open(config_path) as f:
            return GeminiConfig.from_dict(json.load(f))
    return GeminiConfig()

def save_config(config: GeminiConfig):
    """Salva configuração em arquivo JSON."""
    config_path = Path("config/gemini_config.json")
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config.to_dict(), f, indent=2)

def main():
    st.title("🤖 Configuração do Modelo Gemini")
    
    # Sidebar para configurações
    st.sidebar.header("Configurações do Modelo")
    
    # Carrega configuração atual
    config = load_config()
    
    # Controles de configuração
    with st.sidebar:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=config.temperature,
            step=0.1,
            help="Controla a criatividade das respostas. Valores mais altos = mais criativo"
        )
        
        top_p = st.slider(
            "Top P",
            min_value=0.0,
            max_value=1.0,
            value=config.top_p,
            step=0.05,
            help="Controla a diversidade do texto gerado"
        )
        
        top_k = st.slider(
            "Top K",
            min_value=1,
            max_value=100,
            value=config.top_k,
            help="Número de tokens mais prováveis a considerar"
        )
        
        max_tokens = st.number_input(
            "Máximo de Tokens",
            min_value=1,
            max_value=32768,
            value=config.max_output_tokens,
            help="Limite máximo de tokens na resposta"
        )
        
        if st.button("💾 Salvar Configuração"):
            new_config = GeminiConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_tokens
            )
            save_config(new_config)
            st.success("Configuração salva com sucesso!")
    
    # Área principal
    st.header("🔍 Área de Testes")
    
    # Tabs para diferentes tipos de teste
    tab1, tab2 = st.tabs(["💬 Chat", "📄 Processamento de Arquivo"])
    
    with tab1:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            # Cria um container para todo o chat
            chat_area = st.container()
            
            # Cria um container separado para o input na parte inferior
            input_area = st.container()
            
            # Exibe mensagens do histórico
            with chat_area:
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                # Espaço extra para empurrar mensagens para cima
                st.empty()
            
            # Input sempre na parte inferior
            with input_area:
                prompt = st.chat_input("Digite sua mensagem...", key="chat_message_input")
    
    with tab2:
        uploaded_file = st.file_uploader(
            "Escolha um arquivo para processar",
            type=["txt", "pdf", "docx"],
            key="file_uploader"  # key única para este elemento também
        )
        
        if uploaded_file:
            # Salva arquivo temporariamente
            temp_path = Path("temp") / uploaded_file.name
            temp_path.parent.mkdir(exist_ok=True)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            st.info("Arquivo carregado. Configure a instrução para processamento:")
            
            system_prompt = st.text_area(
                "Instrução de sistema",
                value="Analise o conteúdo do arquivo e forneça um resumo detalhado.",
                height=100,
                key="system_prompt"  # key única
            )
            
            if st.button("🔄 Processar Arquivo", key="process_button"):  # key única
                try:
                    with st.spinner("Processando arquivo..."):
                        client = GeminiClient(
                            config=GeminiConfig(
                                temperature=temperature,
                                top_p=top_p,
                                top_k=top_k,
                                max_output_tokens=max_tokens
                            ),
                            system_instruction=system_prompt
                        )
                        
                        file = client.upload_file(str(temp_path))
                        active_file = client.wait_for_file_active(file)
                        # Inicia chat apenas com o arquivo
                        chat = client.start_chat_session([{
                            "role": "user",
                            "parts": [active_file]
                        }])
                        
                        # A system_instruction já foi configurada no cliente
                        response = client.send_message(chat, "")
                        
                        st.success("Arquivo processado com sucesso!")
                        st.markdown("### Resultado:")
                        st.markdown(response.text)
                        st.caption(f"Tokens: {client.token_cost(response)}")
                
                except Exception as e:
                    st.error(f"Erro ao processar arquivo: {str(e)}")
                
                finally:
                    # Limpa arquivo temporário
                    if temp_path.exists():
                        temp_path.unlink()

if __name__ == "__main__":
    main()