"""LLMAgent - Roteador unificado para OpenAI ou Gemini.

Este módulo implementa uma abstração que permite usar diferentes modelos
de linguagem (OpenAI ou Gemini) com a mesma interface, simplificando
a troca entre provedores.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, Sequence

import tiktoken
from openai import OpenAI
import google.generativeai as genai

from src.bot.database.db_init import Database
from src.bot.memory.memory_manager import MemoryManager
from src.config.config import Config
from src.bot.utils.config_manager import ConfigManager
from src.bot.utils.token_tracker import TokenTracker
from src.bot.handlers.telegram_llm_handler import ConfigManager
from src.bot.memory.format_utils import format_context_for_provider
import logging 


logger = logging.getLogger("LLMAgent")

###############################################################################
# Generic contract / interface                                                #
###############################################################################
class LLMClient(Protocol):
    """Define a interface comum para qualquer provedor de LLM."""
    provider: str
    name: str

    async def chat(self, messages: Sequence[Dict[str, str]]) -> str: ...
    def count_tokens(self, text: str) -> int: ...

###############################################################################
# OpenAI implementation                                                       #
###############################################################################
class OpenAIClient:
    """Implementação da interface LLMClient para a OpenAI."""

    def __init__(self, model: str, api_key: str):
        """
        Inicializa um cliente OpenAI.
        
        Args:
            model: Nome do modelo (ex: 'gpt-4o')
            api_key: Chave de API da OpenAI
        """
        self.provider = "openai"
        self.name = model
        self._client = OpenAI(api_key=api_key)
        try:
            self._enc = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(
                f"Modelo '{model}' não encontrado em tiktoken; usando cl100k_base"
            )
            self._enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Conta tokens para o modelo específico da OpenAI."""
        if not text:
            return 0
        try:
            return len(self._enc.encode(text))
        except Exception:
            return math.ceil(len(text) / 3.8)

    async def chat(self, messages: Sequence[Dict[str, str]]) -> str:
        """Realiza uma chamada de chat completion com a OpenAI."""
        loop = asyncio.get_event_loop()
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: self._client.chat.completions.create(
                    model=self.name, messages=list(messages)
                ),
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na chamada à API OpenAI: {e}")
            raise

###############################################################################
# Gemini implementation                                                       #
###############################################################################
class GeminiClient:
    """Implementação da interface LLMClient para o Google Gemini."""

    def __init__(self, model: str, api_key: str):
        """
        Inicializa um cliente Gemini.
        
        Args:
            model: Nome do modelo (ex: 'gemini-1.5-pro')
            api_key: Chave de API do Gemini
        """
        self.provider = "gemini"
        self.name = model
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model if model.startswith("models/") else f"models/{model}"
        )

    def count_tokens(self, text: str) -> int:
        """Conta tokens para o modelo específico do Gemini."""
        if not text:
            return 0
        try:
            return self._model.count_tokens(text).total_tokens
        except Exception:
            return math.ceil(len(text) / 4)

    async def chat(self, messages: Sequence[Dict[str, str]]) -> str:
        """Realiza uma chamada de chat completion com Gemini."""
        loop = asyncio.get_event_loop()
        history = []
        user_prompt = ""
        system = ""
        for m in messages:
            role, content = m["role"], m["content"]
            if role == "system":
                system = content
            elif role == "assistant":
                history.append({"role": "model", "parts": [{"text": content}]})
            elif role == "user":
                user_prompt = content
                # Adiciona mensagens antigas do usuário ao histórico
                if history and history[-1]["role"] == "model":
                    history.append({"role": "user", "parts": [{"text": content}]})
        
        # Remove a última mensagem do usuário do histórico (será o prompt atual)
        if history and history[-1]["role"] == "user":
            history.pop()
            
        try:
            chat = self._model.start_chat(history=history)
            prompt = f"[SYSTEM] {system}\n\n{user_prompt}" if system else user_prompt
            resp = await loop.run_in_executor(None, lambda: chat.send_message(prompt))
            try:
                return resp.text
            except Exception as e:
                logger.error(f"Erro ao extrair texto da resposta Gemini: {e}")
                if hasattr(resp, "parts") and resp.parts:
                    return "".join(part.text for part in resp.parts)
                return "[Erro ao processar a resposta do Gemini]"
        except Exception as e:
            logger.error(f"Erro na chamada à API Gemini: {e}")
            raise

###############################################################################
# LLMAgent                                                                    #
###############################################################################
@dataclass
class LLMAgent:
    """
    Agente de processamento de linguagem natural usando diferentes modelos LLM.
    
    Esta classe gerencia interações com modelos LLM (OpenAI ou Gemini),
    mantendo contexto e histórico usando um sistema de memória persistente.
    """
    
    db: Database = field(default_factory=Database)
    memory: MemoryManager = field(default_factory=MemoryManager)
    system_prompt: str = field(default=Config.SYSTEM_PROMPT)
    _client: LLMClient = field(init=False)
    
    def __post_init__(self) -> None:
        """Inicializa o cliente LLM com base no provedor configurado."""
        config_manager = ConfigManager()
        provider = config_manager.get("llm_provider", Config.LLM_PROVIDER.lower())
        
        if provider == "openai":
            model = config_manager.get("model", Config.MODEL_NAME)
            self._client = OpenAIClient(model, Config.OPENAI_API_KEY)
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or getattr(Config, "GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY não definida")
            model = config_manager.get("model", Config.GEMINI_MODEL_NAME)
            self._client = GeminiClient(model, api_key)
        else:
            raise ValueError(f"Provider desconhecido: {provider}")
        
        # Carrega prompt personalizado, se existir
        custom_prompt = config_manager.get("custom_prompt")
        if custom_prompt:
            self.system_prompt = custom_prompt
                
        logger.info(f"LLMAgent inicializado com {self._client.provider}:{self._client.name}")


    def count_tokens(self, text: str) -> int:
        """Conta o número de tokens em um texto usando o cliente específico."""
        return self._client.count_tokens(text)

    @property
    def model(self):
        """Propriedade para compatibilidade com código legado."""
        return self._client.name
        
    async def get_context_messages(self, user_id: int, chat_id: int, query: str = "") -> List[Dict[str, str]]:
        """
        Recupera contexto combinando mensagens recentes e semanticamente relevantes.
        
        Args:
            user_id: ID do usuário
            chat_id: ID do chat
            query: Consulta atual para buscar contexto relevante
        """
        try:
            # 1. Mensagens recentes (memória de curto prazo)
            recent_messages = await self._fetch_recent_messages(
                user_id, chat_id, Config.MAX_CONTEXT_MESSAGES // 2
            )
            
            # 2. Busca semântica (se houver query)
            semantic_messages = []
            if query and len(query.strip()) > 0:
                semantic_context = await self.memory.get_relevant_context(
                    query=query,
                    user_id=user_id,
                    chat_id=chat_id,
                    limit=Config.MAX_CONTEXT_MESSAGES // 2,
                    time_window=365 * 24 * 60  # Um ano inteiro
                )
                
                for msg in semantic_context:
                    # Evita duplicações com mensagens recentes
                    if not any(r['content'] == msg['content'] for r in recent_messages):
                        semantic_messages.append({
                            "role": msg['role'],
                            "content": msg['content']
                        })
            
            # 3. Mensagens importantes
            important_messages = await self._fetch_important_messages(
                user_id, chat_id, Config.MAX_CONTEXT_MESSAGES // 4
            )
            
            # 4. Combina e filtra tudo
            all_context = recent_messages + semantic_messages + important_messages
            
            # Filtra duplicatas e controla tokens
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
            
            logger.info(
                f"Contexto recuperado: {len(unique_messages)} mensagens ("
                f"{len(recent_messages)} recentes, {len(semantic_messages)} semânticas, "
                f"{len(important_messages)} importantes)"
            )
            return unique_messages
            
        except Exception as e:
            logger.error(f"Erro ao recuperar contexto: {e}", exc_info=True)
            return []
            
    async def _fetch_recent_messages(self, user_id: int, chat_id: int, limit: int) -> List[Dict[str, str]]:
        """Busca mensagens recentes do banco de dados."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, limit))
                
                rows = cursor.fetchall()
                return [
                    {"role": row[0], "content": row[1]} 
                    for row in reversed(rows)
                ]
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens recentes: {e}")
            return []
            
    async def _fetch_important_messages(self, user_id: int, chat_id: int, limit: int) -> List[Dict[str, str]]:
        """Busca mensagens importantes com base no score de importância."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content 
                    FROM messages 
                    WHERE user_id = ? AND chat_id = ? AND importance >= 4
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, chat_id, limit))
                
                rows = cursor.fetchall()
                return [
                    {"role": row[0], "content": row[1]} 
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Erro ao buscar mensagens importantes: {e}")
            return []

    async def process_message(self, text: str, user_id: int, chat_id: int) -> str:
        """Processa uma mensagem sem fazer cagada"""
        try:
            # 1. Adiciona mensagem do usuário
            await self.memory.add_message(user_id, chat_id, text, role="user")
            
            # 2. Pega contexto
            raw_ctx = await self.get_context_messages(user_id, chat_id, query=text)
            
            # 3. Formata pra quem quer que seja o provedor
            messages = format_context_for_provider(
                ctx_messages=raw_ctx,
                provider=self._client.provider,
                system_prompt=self.system_prompt,
                user_message=text
            )
            
            # 4. Chama a API (sem firula)
            response = await self._client.chat(messages)
            
            # 5. Conta tokens (simplificado)
            input_tokens = sum(self.count_tokens(str(m)) for m in messages)
            output_tokens = self.count_tokens(response)
            
            # 6. Registra uso
            tracker = TokenTracker()
            tracker.track(
                provider=self._client.provider,
                model=self._client.name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                query=text
            )
            
            # 7. Salva resposta
            await self.memory.add_message(user_id, chat_id, response, role="assistant")
            
            return response
            
        except Exception as e:
            logger.error(f"Puta merda, deu erro: {e}")
            return "Deu uma treta aqui, mas tô vivo. Tenta de novo aí."

            
    async def categorize_text(self, text: str) -> tuple:
        """
        Categoriza um texto usando LLM.
        
        Args:
            text: Texto para categorizar
            
        Returns:
            Tupla (categoria, importância)
        """
        if not text or len(text.split()) < 5:
            return 'geral', 2
            
        prompt = f"""
        Analise a seguinte mensagem e determine:
        1. A CATEGORIA mais adequada (uma palavra ou pequena frase)
        2. O NÍVEL DE IMPORTÂNCIA (1 a 5, onde 5 é crucial e 1 é pouco relevante)
        
        Responda APENAS no formato JSON: {{"categoria": "nome_categoria", "importancia": número}}
        
        Mensagem: {text}
        """
        
        messages = [
            {"role": "system", "content": "Você é um assistente de categorização."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result_text = await self._client.chat(messages)
            
            # Extrai o JSON
            json_match = re.search(r'({.*?})', result_text.replace('\n', ' '))
            if json_match:
                result = json.loads(json_match.group(1))
                return (
                    result.get('categoria', 'geral').lower(), 
                    min(max(result.get('importancia', 3), 1), 5)
                )
            
            return 'geral', 3
        except Exception as e:
            logger.error(f"Erro ao categorizar texto: {e}")
            return 'geral', 3