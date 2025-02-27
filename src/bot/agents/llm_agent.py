# agents/llm_agent.py
from openai import OpenAI
import asyncio
import tiktoken
import logging
from datetime import datetime
from bot.database.db_init import Database
from bot.memory.memory_manager import MemoryManager
from config.config import Config

logger = logging.getLogger('LLMAgent')
SYSTEM_PROMPT = Config.SYSTEM_PROMPT

"""
Agente LLM principal para processamento de mensagens.

Este módulo implementa o agente principal baseado em Large Language Models,
gerenciando contexto, memória e interações com a API OpenAI.



Attributes:
    logger: Logger configurado para o módulo
    SYSTEM_PROMPT: Prompt do sistema carregado da configuração

Example:
    >>> agent = LLMAgent()
    >>> response = await agent.process_message("Análise este balancete", user_id=1, chat_id=1)
"""

class LLMAgent:
    """
    Agente de processamento de linguagem natural usando OpenAI.

    Esta classe gerencia interações com modelos LLM, mantendo contexto
    e histórico de conversas usando um sistema de memória persistente.

    Attributes:
        db: Conexão com o banco de dados
        memory: Gerenciador de memória para contexto
        client: Cliente OpenAI configurado
        model: Nome do modelo em uso
        encoding: Codificador de tokens
        system_prompt: Prompt do sistema

    Example:
        >>> agent = LLMAgent()
        >>> stats = await agent.get_memory_stats(user_id=1, chat_id=1)
        >>> print(f"Total de mensagens: {stats['total_messages']}")
    """

    def __init__(self):
        """
        Inicializa o agente LLM com configurações do arquivo config.py.

        Configura conexões com banco de dados, sistema de memória e cliente OpenAI.
        Carrega configurações como modelo e prompt do sistema.
        """
        logger.info("Inicializando LLMAgent")
        self.db = Database()
        self.memory = MemoryManager()
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.MODEL_NAME
        self.encoding = tiktoken.encoding_for_model(self.model)
        logger.debug(f"Modelo selecionado: {self.model}")
        
        # Prompt do sistema
        self.system_prompt = SYSTEM_PROMPT

    def count_tokens(self, text: str) -> int:
        """
        Conta o número de tokens em um texto usando o encoding do modelo atual.

        Args:
            text (str): Texto para contar tokens

        Returns:
            int: Número de tokens no texto

        Example:
            >>> tokens = agent.count_tokens("Olá, mundo!")
            >>> print(f"Número de tokens: {tokens}")
        """
        return len(self.encoding.encode(text))

    async def get_context_messages(self, user_id: int, chat_id: int) -> list:
        """
        Recupera mensagens de contexto relevantes para a conversa atual.

        Busca mensagens recentes e relevantes do histórico, respeitando
        limites de tokens e janela temporal.

        Args:
            user_id (int): ID do usuário
            chat_id (int): ID do chat

        Returns:
            list: Lista de mensagens formatadas para contexto

        Raises:
            Exception: Se houver erro ao recuperar mensagens
        """
        try:
            # Obtém últimas mensagens como contexto base
            recent_messages = await self.memory.get_relevant_context(
                query="",  # Vazio para pegar as mais recentes
                user_id=user_id,
                chat_id=chat_id,
                limit=Config.MAX_CONTEXT_MESSAGES,
                time_window=Config.CONTEXT_TIME_WINDOW
            )
            
            context_messages = []
            total_tokens = 0
            
            # Processa as mensagens mantendo controle de tokens
            for msg in reversed(recent_messages):
                tokens = self.count_tokens(msg['content'])
                if total_tokens + tokens > Config.MAX_TOKENS:
                    logger.warning(f"Limite de tokens atingido: {total_tokens}/{Config.MAX_TOKENS}")
                    break
                    
                context_messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
                total_tokens += tokens
            
            logger.debug(f"Contexto recuperado: {len(context_messages)} mensagens, {total_tokens} tokens")
            return context_messages
            
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {str(e)}", exc_info=True)
            return []

    async def process_message(self, message: str, user_id: int, chat_id: int) -> str:
        """
        Processa uma mensagem do usuário e gera uma resposta usando o modelo LLM.

        Gerencia o fluxo completo de processamento: adiciona a mensagem à memória,
        recupera contexto relevante, chama a API do OpenAI e armazena a resposta.

        Args:
            message (str): Mensagem do usuário para processar
            user_id (int): ID do usuário que enviou a mensagem
            chat_id (int): ID do chat onde a mensagem foi enviada

        Returns:
            str: Resposta gerada pelo modelo LLM

        Raises:
            Exception: Se houver erro no processamento da mensagem

        Example:
            >>> response = await agent.process_message("Qual o saldo do PC YR-027?", 1, 1)
            >>> print(response)
        """
        try:
            # Adiciona mensagem do usuário à memória
            await self.memory.add_message(
                user_id=user_id,
                chat_id=chat_id,
                content=message,
                role="user"
            )
            
            # Obtém contexto relevante
            context_messages = await self.get_context_messages(user_id, chat_id)
            
            # Prepara mensagens para o modelo
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(context_messages)
            messages.append({"role": "user", "content": message})
            
            # Chama a API
            response = await self._call_openai_api(messages)
            response_text = response.choices[0].message.content
            
            # Adiciona resposta à memória
            await self.memory.add_message(
                user_id=user_id,
                chat_id=chat_id,
                content=response_text,
                role="assistant"
            )
            
            return response_text
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}", exc_info=True)
            return "Desculpe, ocorreu um erro ao processar sua mensagem."

    async def _call_openai_api(self, messages: list):
        """
        Realiza chamada assíncrona à API do OpenAI.

        Encapsula a chamada da API em um executor para evitar bloqueio do loop de eventos.

        Args:
            messages (list): Lista de mensagens formatadas para a API OpenAI

        Returns:
            ChatCompletion: Resposta da API do OpenAI

        Raises:
            OpenAIError: Se houver erro na chamada da API
            asyncio.TimeoutError: Se a chamada exceder o timeout

        Example:
            >>> messages = [{"role": "user", "content": "Olá"}]
            >>> response = await agent._call_openai_api(messages)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
        )

    # def count_tokens(self, text: str) -> int:
    #     """Conta tokens em um texto"""
    #     return len(self.encoding.encode(text))

    async def get_memory_stats(self, user_id: int, chat_id: int) -> dict:
        """
        Recupera estatísticas da memória para um usuário e chat específicos.

        Coleta informações sobre categorias de mensagens e totais armazenados
        na memória do sistema.

        Args:
            user_id (int): ID do usuário
            chat_id (int): ID do chat

        Returns:
            dict: Dicionário contendo estatísticas da memória
                - categories: Lista de estatísticas por categoria
                - total_messages: Total de mensagens armazenadas

        Raises:
            Exception: Se houver erro ao acessar as estatísticas

        Example:
            >>> stats = await agent.get_memory_stats(1, 1)
            >>> print(f"Total de mensagens: {stats['total_messages']}")
        """
        try:
            stats = await self.memory.get_category_stats(user_id, chat_id)
            
            # Verifica se stats é um dicionário e tem a chave 'categories'
            if isinstance(stats, dict) and 'categories' in stats:
                categories = stats.get('categories', [])
                total_messages = sum(cat.get('total', 0) for cat in categories)
                return {
                    "categories": categories,
                    "total_messages": total_messages
                }
            return {
                "categories": [],
                "total_messages": 0
            }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}", exc_info=True)
            return {
                "categories": [],
                "total_messages": 0
            }