# handlers/telegram_llm_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.agents.llm_agent import LLMAgent
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
            
            # Busca mensagens direto do banco
            with self.llm_agent.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as total FROM messages 
                    WHERE user_id = ? AND chat_id = ?
                ''', (user_id, chat_id))
                total = cursor.fetchone()[0]
                
                # Busca categorias se houver mensagens
                categories = []
                if total > 0:
                    cursor.execute('''
                        SELECT category, COUNT(*) as count 
                        FROM messages 
                        WHERE user_id = ? AND chat_id = ?
                        GROUP BY category
                    ''', (user_id, chat_id))
                    categories = cursor.fetchall()
            
            # Monta resposta SEM MARKDOWN
            response = "📊 Estatísticas da Memória\n\n"
            response += f"Total de mensagens: {total}\n\n"
            
            if categories:
                response += "Categorias:\n"
                for cat in categories:
                    cat_name = cat['category'] or 'geral'
                    response += f"- {cat_name}: {cat['count']} mensagens\n"
            else:
                response += "Nenhuma categoria encontrada."
                
            # Enviar SEM MARKDOWN!
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Erro ao processar comando /memoria: {e}", exc_info=True)
            await update.message.reply_text("Erro ao buscar estatísticas. Tente novamente!")
            
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
                logger.info(f"Recebendo mensagem. User ID: {user_id}, Chat ID: {chat_id}")
                logger.info(f"Conteúdo: {user_message[:50]}...")
                
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
            logger.info("Iniciando processamento com LLM...")
            response = await self.llm_agent.process_message(
                message=user_message,
                user_id=user_id,
                chat_id=chat_id
            )
            logger.info("Processamento LLM concluído")
            
            # Envia a resposta
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
            await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua mensagem.")

# Instância global do handler
telegram_llm_handler = TelegramLLMHandler()