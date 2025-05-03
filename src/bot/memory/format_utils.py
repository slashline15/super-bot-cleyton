# src/bot/memory/format_utils.py
import logging
import os

logger = logging.getLogger('FormatUtils')

def format_context_for_provider(ctx_messages: list, provider: str, compat_mode: bool = False) -> list:
    """
    Converte mensagens do ChromaDB no formato adequado para cada provedor LLM.
    
    Args:
        ctx_messages: Lista de mensagens do contexto
        provider: Nome do provedor ('openai' ou 'gemini')
        compat_mode: Se está usando o modo de compatibilidade OpenAI do Gemini
        
    Returns:
        Lista formatada para o provedor especificado
    """
    if not ctx_messages:
        return []
        
    formatted_messages = []
    
    # Ordena mensagens por timestamp se disponível
    try:
        sorted_messages = sorted(
            ctx_messages, 
            key=lambda m: m.get('timestamp', '0') if isinstance(m, dict) else '0'
        )
    except Exception as e:
        logger.warning(f"Erro ao ordenar mensagens: {str(e)}")
        sorted_messages = ctx_messages
    
    for msg in sorted_messages:
        # Extrai role e content independente do formato
        if isinstance(msg, dict):
            role = msg.get('role', 'user')
            if 'content' in msg:
                content = msg.get('content', '')
            elif 'page_content' in msg:  # Formato que pode vir do ChromaDB
                content = msg.get('page_content', '')
            else:
                content = str(msg)
        else:
            # Tentativa de fallback se não for dict
            logger.warning(f"Formato de mensagem desconhecido: {type(msg)}")
            role = "user" 
            content = str(msg)
            
        # Adapta o papel e formato conforme o provedor
        if provider == 'gemini' and not compat_mode:
            if role == 'assistant':
                role = 'model'  # Gemini usa 'model' em vez de 'assistant'
            
            # Gemini usa parts em vez de content
            formatted_messages.append({"role": role, "parts": [{"text": content}]})
        else:
            # OpenAI ou modo compatibilidade
            formatted_messages.append({"role": role, "content": content})
    
    return formatted_messages