# src/bot/agents/gemini/client.py

"""
Cliente para interação com o modelo Gemini.

Este módulo fornece uma interface para interagir com o modelo Gemini da Google,
oferecendo funcionalidades como processamento de texto, gerenciamento de chat
e configuração flexível.

Attributes:
    load_dotenv: Carrega variáveis de ambiente do arquivo .env

Example:
    >>> from src.bot.agents.gemini import GeminiClient
    >>> client = GeminiClient()
    >>> response = client.send_message(chat_session, "Olá!")
"""

import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from .config import GeminiConfig  # Importa do mesmo diretório

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


class GeminiClient:
    """
    Cliente para interação com o modelo Gemini com configuração flexível.

    Esta classe gerencia a conexão e interação com a API do Gemini,
    permitindo configuração dinâmica e processamento de diferentes tipos de entrada.

    Args:
        api_key (str, optional): Chave da API Gemini. Se não fornecida, busca em GEMINI_API_KEY
        model_name (str): Nome do modelo Gemini a ser usado
        system_instruction (str, optional): Instrução de sistema para o modelo
        config (GeminiConfig, optional): Configurações personalizadas para o cliente

    Attributes:
        model: Instância do modelo Gemini configurado
        config: Configurações atuais do cliente

    Example:
        >>> client = GeminiClient(model_name="gemini-1.5-pro")
        >>> chat = client.start_chat_session()
        >>> response = client.send_message(chat, "Como posso ajudar?")
    """

    def __init__(
        self, 
        api_key=None, 
        model_name="gemini-1.5-pro", 
        system_instruction=None,  # Mudou de "" para None
        config: GeminiConfig = None
    ):
        """
        Inicializa o cliente do Gemini.

        Args:
            api_key: Chave da API (se não fornecida, busca em GEMINI_API_KEY nas variáveis de ambiente)
            model_name: Nome do modelo a ser usado
            system_instruction: Instrução de sistema para o modelo (opcional)
            config: Instância de GeminiConfig com as configurações desejadas
        """
        # Configuração da API
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("A chave da API não foi fornecida. Verifique a variável GEMINI_API_KEY.")
        
        genai.configure(api_key=self.api_key)
        
        # Configurações do modelo
        self.model_name = model_name
        self.system_instruction = system_instruction  # Pode ser None
        self.config = config or GeminiConfig()
        
        # Inicializa o modelo
        self._initialize_model()
    
    def _initialize_model(self):
        """
        Inicializa ou reinicializa o modelo com as configurações atuais.

        Este método é chamado internamente durante a inicialização e
        quando as configurações são atualizadas.

        Raises:
            ValueError: Se as configurações forem inválidas
            RuntimeError: Se houver erro na inicialização do modelo
        """
        model_params = {
            "model_name": self.model_name,
            "generation_config": self.config.to_dict(),
        }
        
        # Só adiciona system_instruction se não for None
        if self.system_instruction is not None:
            model_params["system_instruction"] = self.system_instruction
            
        self.model = genai.GenerativeModel(**model_params)
    
    def update_config(self, new_config: GeminiConfig):
        """
        Atualiza a configuração do cliente e reinicializa o modelo.
        
        Args:
            new_config (GeminiConfig): Nova configuração a ser aplicada

        Raises:
            ValueError: Se a nova configuração for inválida

        Example:
            >>> new_config = GeminiConfig(temperature=0.8)
            >>> client.update_config(new_config)
        """
        self.config = new_config
        self._initialize_model()
    
    def get_current_config(self) -> GeminiConfig:
        """
        Retorna a configuração atual do cliente.

        Returns:
            GeminiConfig: Configuração atual em uso

        Example:
            >>> config = client.get_current_config()
            >>> print(f"Temperatura atual: {config.temperature}")
        """
        return self.config

    def upload_file(self, file_path, mime_type="text/plain"):
        """
        Faz upload de um arquivo para processamento pelo Gemini.

        Args:
            file_path (str): Caminho do arquivo a ser enviado
            mime_type (str): Tipo MIME do arquivo (default: "text/plain")

        Returns:
            object: Objeto do arquivo processado pela API

        Raises:
            FileNotFoundError: Se o arquivo não for encontrado
            ValueError: Se o arquivo estiver vazio ou inválido

        Example:
            >>> file = client.upload_file("documento.txt")
            >>> print(f"Arquivo processado: {file.name}")
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
        file = genai.upload_file(file_path, mime_type=mime_type)
        print(f"Arquivo '{file.display_name}' enviado com URI: {file.uri}")
        return file

    def wait_for_file_active(self, file, polling_interval=10):
        """
        Aguarda o processamento do arquivo até que ele esteja ativo.

        Args:
            file: Objeto retornado pelo upload
            polling_interval: Intervalo entre as verificações (em segundos)
            
        Returns:
            O objeto de arquivo atualizado quando estiver ativo
        """
        print(f"Aguardando o processamento do arquivo: {file.display_name}")
        current_file = genai.get_file(file.name)
        
        while current_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(polling_interval)
            current_file = genai.get_file(file.name)
            
        if current_file.state.name != "ACTIVE":
            raise Exception(
                f"O arquivo {file.name} falhou ao processar "
                f"(estado: {current_file.state.name})."
            )
            
        print("\nArquivo processado e ativo!")
        return current_file

    def start_chat_session(self, history=None):
        """
        Inicia uma nova sessão de chat com histórico opcional.

        Args:
            history (List[Dict], optional): Lista de mensagens anteriores
                Cada mensagem deve ter 'role' e 'parts'

        Returns:
            ChatSession: Nova sessão de chat inicializada

        Raises:
            ValueError: Se o histórico fornecido for inválido

        Example:
            >>> history = [{"role": "user", "parts": ["Olá"]}]
            >>> chat = client.start_chat_session(history)
        """
        return self.model.start_chat(history=history or [])

    def send_message(self, chat_session, message):
        """
        Envia uma mensagem para a sessão de chat.

        Args:
            chat_session: Objeto da sessão de chat
            message: Mensagem a ser enviada
            
        Returns:
            Resposta do modelo
        """
        if not message or not isinstance(message, str):
            raise ValueError(f"Mensagem inválida. Recebido: {repr(message)}")
        
        if not message.strip():
            raise ValueError("A mensagem não pode estar vazia")
            
        return chat_session.send_message(message)

    @staticmethod
    def token_cost(response):
        """
        Calcula o custo em tokens da resposta.

        Args:
            response (Response): Objeto de resposta do modelo

        Returns:
            str: Informação sobre uso de tokens ou "N/A"

        Example:
            >>> response = client.send_message(chat, "Olá")
            >>> cost = client.token_cost(response)
            >>> print(f"Custo: {cost}")
        """
        try:
            # Tenta diferentes atributos que podem conter informação de tokens
            if hasattr(response, 'token_count'):
                return response.token_count.prompt_tokens
            elif hasattr(response, 'candidates') and response.candidates:
                return f"Resposta gerada com {len(response.text)} caracteres"
            return "N/A (informação de tokens não disponível)"
        except Exception:
            return "N/A (informação de tokens não disponível)"