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

class LLMAgent:
    def __init__(self):
        """Inicializa o agente LLM com configurações do arquivo config.py"""
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
        """Conta tokens em um texto"""
        return len(self.encoding.encode(text))

    async def get_context_messages(self, user_id: int, chat_id: int) -> list:
        """
        Recupera mensagens de contexto usando o MemoryManager
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
        Processa uma mensagem do usuário usando o contexto do MemoryManager
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
        Faz a chamada à API do OpenAI de forma assíncrona
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
        )

    def count_tokens(self, text: str) -> int:
        """Conta tokens em um texto"""
        return len(self.encoding.encode(text))

    async def get_memory_stats(self, user_id: int, chat_id: int) -> dict:
        """
        Retorna estatísticas da memória
        """
        try:
            stats = await self.memory.get_category_stats(user_id, chat_id)
            return {
                "categories": stats,
                "total_messages": sum(stat['total'] for stat in stats)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}", exc_info=True)
            return {}