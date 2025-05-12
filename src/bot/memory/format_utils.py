# src/bot/memory/format_utils.py
import logging
import os

logger = logging.getLogger('FormatUtils')

def format_context_for_provider(ctx_messages, provider, system_prompt=None, user_message=None):
    """
    Formata mensagens pro formato que cada provedor entende.
    Finalmente uma função que não é uma merda! 🎉
    """
    if not ctx_messages:
        ctx_messages = []
    
    formatted = []
    
    # Pega as mensagens e formata direitinho
    for msg in ctx_messages:
        if not isinstance(msg, dict):
            continue
            
        # Extrai o role e content de jeito robusto
        role = msg.get('role', 'user')
        content = msg.get('content') or msg.get('page_content', '') or str(msg)
        
        if not content:
            continue
            
        if provider == 'gemini':
            # Gemini é dramático: quer "model" em vez de "assistant"
            if role == 'assistant':
                role = 'model'
            formatted.append({
                "role": role,
                "parts": [{"text": content}]
            })
        else:
            # OpenAI é de boa
            formatted.append({
                "role": role,
                "content": content
            })
    
    # Agora o system_prompt
    if provider == 'gemini':
        # Gemini - não injetamos o prompt aqui porque o GeminiClient já faz isso
        # Apenas adicionamos a mensagem do usuário se necessário
        if user_message:
            # Adiciona mensagem do usuário sem modificar
            formatted.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })
        # Convertemos role=system para o formato que o GeminiClient espera
        if system_prompt:
            formatted.insert(0, {
                "role": "system",
                "content": system_prompt
            })
    else:
        # OpenAI aceita system numa boa
        if system_prompt:
            formatted.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        if user_message:
            formatted.append({
                "role": "user",
                "content": user_message
            })
    
    return formatted