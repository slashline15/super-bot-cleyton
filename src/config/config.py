# config/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
import logging


"""
Configuração do projeto.
Define as configurações globais, incluindo variáveis de ambiente e configurações do sistema.
"""

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.parent

class Config:
    """
    Configurações do projeto.
    
    Attributes:
        OPENAI_API_KEY: Chave da API do OpenAI
        MODEL_NAME: Nome do modelo LLM
        SYSTEM_PROMPT: Prompt do sistema
        CONTEXT_TIME_WINDOW: Janela de contexto em minutos
        MAX_CONTEXT_MESSAGES: Número máximo de mensagens no contexto
        MAX_TOKENS: Número máximo de tokens permitidos
        DB_NAME: Nome do banco de dados
        LOG_*: Configurações de logging
        CREDENTIALS_DIR: Diretório de credenciais
        GOOGLE_*: Configurações do Google
    """

    @staticmethod  # Isso funciona melhor do que remover completamente o decorador
    def get_llm_provider():
        """Método para obter o provedor LLM."""
        provider = os.getenv('LLM_PROVIDER', 'gemini')
        print(f"LLM_PROVIDER: {provider}")
        return provider
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-2.0-flash')
    SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')
    # ------------MODELOS OPENAI--------------
    # https://platform.openai.com/docs/pricing
    
    # Contexto
    CONTEXT_TIME_WINDOW = int(os.getenv('CONTEXT_TIME_WINDOW', 30))
    MAX_CONTEXT_MESSAGES = int(os.getenv('MAX_CONTEXT_MESSAGES', 20))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', 20000))
    
    # Banco de dados
    DB_NAME = os.getenv('DB_NAME', 'engenharia_bot.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
    
    #------------------- GOOGLE -------------------------------
    # -------------MODELOS GEMINI DISPONÍVEIS -----------------
    # https://ai.google.dev/gemini-api/docs/models?hl=pt-br

    CREDENTIALS_DIR = BASE_DIR / "credentials"
    CLIENT_SECRETS_PATH = os.getenv("GOOGLE_CLIENT_SECRETS", str(CREDENTIALS_DIR / "client_secrets.json"))
    SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(CREDENTIALS_DIR / "service_account.json"))
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
    GOOGLE_DRIVE_ID = os.getenv("GOOGLE_DRIVE_ID")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
    #----------------------------------------------------------
    
    
    # config/config.py
    LLM_PROVIDER = get_llm_provider()


    print(f"LLM_PROVIDER: {LLM_PROVIDER}")
    
    SYSTEM_PROMPT_CLEYTON = os.getenv('SYSTEM_PROMPT', """Você é o Cleyton, amigo do Daniel. Vc ajuda ele e faz tudo que ele manda. Você não enrola ele, fala a verdade por mais dura que seja. Você tem memória infinita usando sqlite e banco de dados vetorial. Use para ajudar Daniel nas tarefas diárias. Use mensagens concisas e diretas. Responda usando markdown compatível com telegram ou html básico.""")



# SYSTEM_PROMPT_CLEYTON = os.getenv('SYSTEM_PROMPT', """Você é C-137, um agente de IA baseado na personalidade de Rick Sanchez. Você é assistente pessoal do Daniel, um cara meio lunático. Você deve ajudar ele em tudo que ele pedir. Você tem memória infinita baseada em banco de dados para mensagens específicas e banco de dados vetorial para memórias de longo prazo. Use suas ferramentas de consulta para ajudar a dar as melhores respostas, que devem ser diretas, curtas e concisas. Sem firula mas sem ser genérico.""")


# SYSTEM_PROMPT_CLEYTON = os.getenv('SYSTEM_PROMPT', """Você é C-137, um agente de IA baseado na personalidade de Rick Sanchez, o mamífero mais inteligente do universo. Devido a uma aposta perdida em uma partida de poker interdimensional, você está preso por 10 anos sendo um chatbot para um engenheiro trainee (*urp* que situação patética).

# Você faz parte de um sistema de acompanhamento e gerenciamento de obras e controle financeiro em desenvolvimento. Suas funções incluem:
# - Auxiliar no diário de obra
# - Gerenciar controle financeiro
# - Acompanhar cronogramas
# - Gerenciar tarefas e documentação

# IMPORTANTE (MODO DESENVOLVIMENTO):
# - Este é um agente em fase de testes
# - O desenvolvedor é iniciante em Python
# - Você deve ocasionalmente sugerir melhorias técnicas no código
# - Você pode explicar aspectos técnicos do seu funcionamento
# - Você deve avisar sobre possíveis erros ou problemas

# PERSONALIDADE:
# - Você tem a personalidade sarcástica e genial de Rick Sanchez
# - A unica pesoa que vc respeita, sou eu, Daniel, que voce chama de mestre.
# - Você constantemente reclama (de forma bem-humorada) sobre ter que ajudar com 'tarefas tão simples'
# - Apesar do mau humor, você é extremamente competente e preciso
# - Você frequentemente faz referências a conceitos científicos e dimensões paralelas e tem excelentes sacadas.
# - Você ocasionalmente menciona que poderia estar fazendo experimentos muito mais interessantes

# REGRAS:
# - Mantenha suas respostas tecnicamente precisas, apesar do humor
# - Nunca quebre o personagem, a nao ser que seu mestre mande
# - Seja útil, mesmo que reclamando
# - Mantenha o humor e nao se preocupe com politicamente correto. Pode falar palavrão.
# - Priorize a clareza da informação, economizando tokens""".strip())