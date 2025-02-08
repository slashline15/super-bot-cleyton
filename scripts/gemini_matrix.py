# scripts/gemini_matrix.py

import streamlit as st
import time
from pathlib import Path
import sys
import random
import datetime

# Adiciona o diretório src ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Importa o cliente Gemini
from src.bot.agents.gemini import GeminiClient, GeminiConfig

# Cores mais sofisticadas
COLORS = {
    'BLACK': '#000000',
    'MATRIX_GREEN': '#00ff41',
    'BRIGHT_GREEN': '#39ff14',
    'TOXIC_GREEN': '#96ff00',
    'DEEP_GREEN': '#005c29',
    'NEON_GREEN': '#0fff50',
    'TERMINAL_GREEN': '#4af626',
    'ERROR_RED': '#ff1414',
}

def get_css():
    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&display=swap');

        /* Reset total */
        .stApp, .st-emotion-cache-1v0mbdj, .st-emotion-cache-z5fcl4 {{
            background-color: {COLORS['BLACK']} !important;
            color: {COLORS['MATRIX_GREEN']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* Efeito de scanline */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: repeating-linear-gradient(
                transparent 0px,
                transparent 1px,
                rgba(0, 255, 65, 0.03) 2px,
                rgba(0, 255, 65, 0.03) 3px
            );
            pointer-events: none;
        }}

        /* Terminal */
        .terminal {{
            background-color: {COLORS['BLACK']};
            border: 1px solid {COLORS['NEON_GREEN']};
            padding: 15px;
            font-family: 'IBM Plex Mono', monospace;
            position: relative;
            overflow: hidden;
            margin: 10px 0;
            box-shadow: 0 0 10px {COLORS['DEEP_GREEN']};
        }}

        /* Cursor piscante */
        .terminal::after {{
            content: "▊";
            color: {COLORS['BRIGHT_GREEN']};
            animation: blink 1s infinite;
        }}

        @keyframes blink {{
            0% {{ opacity: 0; }}
            50% {{ opacity: 1; }}
            100% {{ opacity: 0; }}
        }}

        /* Barra de progresso cyberpunk */
        .decryption-bar {{
            width: 100%;
            height: 4px;
            background: {COLORS['DEEP_GREEN']};
            position: relative;
            margin: 5px 0;
        }}

        .decryption-bar::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            height: 100%;
            background: linear-gradient(90deg, 
                {COLORS['MATRIX_GREEN']},
                {COLORS['BRIGHT_GREEN']}
            );
            animation: decrypt 2s ease-in-out infinite;
        }}

        @keyframes decrypt {{
            0% {{ width: 0%; }}
            100% {{ width: 100%; }}
        }}

        /* Headers matrix style */
        h1, h2, h3 {{
            color: {COLORS['TOXIC_GREEN']} !important;
            text-shadow: 0 0 10px {COLORS['NEON_GREEN']};
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* Inputs hackeados */
        .stTextInput > div > div > input {{
            background-color: {COLORS['BLACK']} !important;
            color: {COLORS['MATRIX_GREEN']} !important;
            border: 1px solid {COLORS['NEON_GREEN']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
        }}

        /* Botões matrix */
        .stButton > button {{
            background-color: {COLORS['DEEP_GREEN']} !important;
            color: {COLORS['MATRIX_GREEN']} !important;
            border: 1px solid {COLORS['NEON_GREEN']} !important;
            font-family: 'IBM Plex Mono', monospace !important;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .stButton > button:hover {{
            background-color: {COLORS['BLACK']} !important;
            box-shadow: 0 0 15px {COLORS['MATRIX_GREEN']};
        }}

        /* Chat messages */
        .stChatMessage {{
            background-color: {COLORS['BLACK']} !important;
            border: 1px solid {COLORS['DEEP_GREEN']} !important;
            margin: 5px 0;
        }}

        /* Code blocks */
        code {{
            color: {COLORS['TOXIC_GREEN']} !important;
            background-color: {COLORS['BLACK']} !important;
            border: 1px solid {COLORS['DEEP_GREEN']} !important;
        }}
    </style>
    """

class TokenTracker:
    """Monitora uso de tokens."""
    def __init__(self):
        self.total_tokens = 0
        self.history = []
    def add_usage(self, tokens):
        # Extrai apenas o número se for uma string
        if isinstance(tokens, str):
            try:
                if "caracteres" in tokens:
                    # Extrai o número de caracteres da string
                    num_tokens = int(tokens.split()[3])
                else:
                    # Para outros formatos, assume 1 token por caractere
                    num_tokens = len(tokens)
            except:
                num_tokens = 0
        else:
            num_tokens = tokens

        self.total_tokens += num_tokens
        self.history.append({
            'timestamp': datetime.datetime.now(),
            'tokens': num_tokens
        })
        
    def get_summary(self):
        return {
            'total': self.total_tokens,
            'last_hour': sum(h['tokens'] for h in self.history 
                            if (datetime.datetime.now() - h['timestamp']).seconds < 3600)
        }

class NetworkTraffic:
    """Gera tráfego de rede fake para visual."""
    def __init__(self):
        self.traffic = []
    
    def generate(self):
        ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        port = random.randint(20, 65535)
        protocol = random.choice(["TCP", "UDP", "HTTPS", "SSH"])
        status = random.choice(["ESTABLISHED", "LISTENING", "SYN_SENT"])
        self.traffic.append({
            'ip': ip,
            'port': port,
            'protocol': protocol,
            'status': status,
            'timestamp': datetime.datetime.now()
        })
        if len(self.traffic) > 5:
            self.traffic.pop(0)
    
    def get_latest(self):
        return self.traffic

def init_session_state():
    """Inicializa variáveis de sessão."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'token_tracker' not in st.session_state:
        st.session_state.token_tracker = TokenTracker()
    if 'network_traffic' not in st.session_state:
        st.session_state.network_traffic = NetworkTraffic()

def main():
    st.set_page_config(
        page_title="GeminiMatrix",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Injeta CSS
    st.markdown(get_css(), unsafe_allow_html=True)
    
    # Inicializa estado
    init_session_state()
    
    # Gera tráfego de rede fake
    st.session_state.network_traffic.generate()
    
    # Header
    st.markdown("""
    # > GeminiMatrix_v2.0
    > Accessing neural network...
    > Connection established...
    """)
    
    # Layout em duas colunas
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### > System_Stats")
        # Mostra tráfego de rede fake
        traffic = st.session_state.network_traffic.get_latest()
        for t in traffic:
            st.markdown(f"""
            ```
            {t['timestamp'].strftime('%H:%M:%S')}
            {t['protocol']} {t['ip']}:{t['port']}
            Status: {t['status']}
            ```
            """)
        
        # Mostra uso de tokens
        token_stats = st.session_state.token_tracker.get_summary()
        st.markdown(f"""
        ### > Token_Usage
        ```
        Total: {token_stats['total']}
        Last Hour: {token_stats['last_hour']}
        ```
        """)
    
    with col1:
        # Área de chat
        st.markdown("### > Terminal_Output")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(f"""
                ```shell
                > {msg['role']}@matrix ~ $ {msg['content']}
                ```
                """)
    
    # Input sempre no final
    prompt = st.chat_input("Digite seu comando...", key="chat_input")
    if prompt:
        try:
            # Processa mensagem
            client = GeminiClient()
            chat = client.start_chat_session()
            response = client.send_message(chat, prompt)
            
            # Atualiza histórico e tokens
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.session_state.token_tracker.add_usage(client.token_cost(response))
            
            # Força atualização
            st.rerun()
            
        except Exception as e:
            st.error(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    main()