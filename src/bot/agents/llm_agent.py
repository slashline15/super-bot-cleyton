# agents/llm_agent.py
from openai import OpenAI
import asyncio
import tiktoken
import logging
from datetime import datetime
from src.bot.database.db_init import Database
from src.bot.memory.memory_manager import MemoryManager
from src.config.config import Config
from dotenv import load_dotenv
from os import getenv

load_dotenv()


logger = logging.getLogger('LLMAgent')

SYSTEM_PROMPT = getenv("SYSTEM_PROMPT")
SYSTEM_PROMPT = Config.SYSTEM_PROMPT_CLEYTON

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

    
    async def get_context_messages(self, user_id: int, chat_id: int, query: str = "") -> list:
        """
        Recupera contexto combinando mensagens recentes e semanticamente relevantes
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            query: Consulta atual para buscar contexto relevante
            
        Returns:
            list: Lista de mensagens formatadas para o contexto
        """
        try:
            # 1. Pega as mensagens recentes (memória de curto prazo)
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, Config.MAX_CONTEXT_MESSAGES // 2))  # Usa metade do limite para mensagens recentes
                
                recent_messages = cursor.fetchall()
            
            # 2. Busca mensagens semanticamente relevantes (se tiver query)
            semantic_messages = []
            if query and len(query.strip()) > 0:
                relevant_context = await self.memory.get_relevant_context(
                    query=query,
                    user_id=user_id,
                    chat_id=chat_id,
                    limit=Config.MAX_CONTEXT_MESSAGES // 2,  # Outra metade para relevantes
                    time_window=365 * 24 * 60  # Um ano inteiro!
                )
                
                # Converte para o formato esperado
                for msg in relevant_context:
                    # Evita duplicações com as mensagens recentes
                    if msg['id'] not in [recent['id'] for recent in recent_messages if 'id' in recent]:
                        semantic_messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            # 3. Busca mensagens importantes de qualquer época
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ? AND importance >= 4
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, Config.MAX_CONTEXT_MESSAGES // 4))  # Um quarto para mensagens importantes
                
                important_messages = cursor.fetchall()
            
            # Converte mensagens recentes para o formato esperado
            recent_context = []
            for row in reversed(recent_messages):
                role, content = row
                recent_context.append({
                    "role": role,
                    "content": content
                })
            
            # Converte mensagens importantes para o formato esperado
            important_context = []
            for row in important_messages:
                role, content = row
                # Evita duplicações
                if {"role": role, "content": content} not in recent_context and {"role": role, "content": content} not in semantic_messages:
                    important_context.append({
                        "role": role,
                        "content": content
                    })
            
            # Combina todas as fontes de contexto
            all_context = recent_context + semantic_messages + important_context
            
            # Filtra duplicatas e limita o tamanho total
            unique_messages = []
            seen_contents = set()
            total_tokens = 0
            
            for msg in all_context:
                content_hash = hash(msg['content'])
                if content_hash not in seen_contents:
                    tokens = self.count_tokens(msg['content'])
                    if total_tokens + tokens <= Config.MAX_TOKENS:
                        unique_messages.append(msg)
                        seen_contents.add(content_hash)
                        total_tokens += tokens
                    else:
                        break
            
            logger.info(f"Contexto recuperado: {len(unique_messages)} mensagens ({len(recent_context)} recentes, {len(semantic_messages)} semânticas, {len(important_context)} importantes)")
            return unique_messages
                    
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
            
            # Obtém contexto relevante, usando a mensagem atual como query
            context_messages = await self.get_context_messages(user_id, chat_id, query=message)
            
            # Resto do código continua igual...
            
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