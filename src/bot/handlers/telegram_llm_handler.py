# handlers/telegram_llm_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from bot.agents.llm_agent import LLMAgent
import logging
import asyncio

logger = logging.getLogger('TelegramLLMHandler')

class TelegramLLMHandler:
    def __init__(self):
        self.llm_agent = LLMAgent()
        logger.info("TelegramLLMHandler inicializado")

    async def handle_memoria(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa o comando /memoria"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Obtém estatísticas
            stats = await self.llm_agent.get_memory_stats(user_id, chat_id)
            
            # Formata a mensagem
            response = "📊 **Estatísticas da Memória**\n\n"
            
            if stats and stats.get('categories'):
                categories = stats['categories']
                if not categories:  # Se a lista estiver vazia
                    response = "Ainda não há mensagens registradas."
                else:
                    for cat in categories:
                        # Verifica se todos os campos necessários existem
                        total = cat.get('total', 0)
                        avg_importance = cat.get('avg_importance', 0)
                        last_message = cat.get('last_message', 'N/A')
                        category = cat.get('category', 'desconhecida')
                        
                        response += f"**{category}**:\n"
                        response += f"- Total mensagens: {total}\n"
                        response += f"- Importância média: {avg_importance:.1f}\n"
                        response += f"- Última mensagem: {last_message}\n\n"
                    
                    total_messages = stats.get('total_messages', sum(c.get('total', 0) for c in categories))
                    response += f"**Total de mensagens**: {total_messages}\n"
            else:
                response = "Nenhuma mensagem encontrada ainda."

            logger.info(f"Estatísticas obtidas com sucesso para user_id={user_id}, chat_id={chat_id}")
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao processar comando /memoria: {e}", exc_info=True)
            error_response = (
                "Desculpe, ocorreu um erro ao buscar as estatísticas.\n"
                "Por favor, tente novamente em alguns instantes."
            )
            await update.message.reply_text(error_response)
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Processa mensagens de texto e áudio do Telegram
        """
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            if update.message.text:
                # Processa mensagem de texto
                user_message = update.message.text
                logger.info(f"Mensagem de texto recebida: {user_message[:50]}...")
                
            elif update.message.voice:
                # Processa mensagem de voz
                logger.info("Mensagem de voz recebida, iniciando transcrição...")
                await update.message.reply_text("🎤 Processando seu áudio...")
                
                voice = update.message.voice
                audio_file = await voice.get_file()
                
                # Baixa o arquivo de áudio
                audio_path = f"temp_audio_{user_id}.ogg"
                await audio_file.download_to_drive(audio_path)
                
                # # Transcreve o áudio
                # user_message = await transcribe_audio(audio_path)
                # logger.info(f"Áudio transcrito: {user_message[:50]}...")
                
                # Remove o arquivo temporário
                import os
                os.remove(audio_path)
                
            else:
                await update.message.reply_text("Desculpe, só processo mensagens de texto e áudio.")
                return
            
            # Processa a mensagem com o LLM
            response = await self.llm_agent.process_message(
                message=user_message,
                user_id=user_id,
                chat_id=chat_id
            )
            
            # Envia a resposta
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
            await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua mensagem.")

# Instância global do handler
telegram_llm_handler = TelegramLLMHandler()