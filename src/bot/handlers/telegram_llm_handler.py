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
        """Processa o comando /memoria com visualização melhorada de categorias"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Busca estatísticas de memória diretamente do memory_manager
            memory_stats = await self.llm_agent.get_memory_stats(user_id, chat_id)
            categories = memory_stats.get("categories", [])
            total_messages = memory_stats.get("total_messages", 0)
            
            # Agrupa por importância
            high_importance = []
            medium_importance = []
            low_importance = []
            
            # Organiza as categorias por importância
            for cat in categories:
                if not isinstance(cat, dict):  # Skip if not a dictionary
                    continue
                    
                category = cat.get("category", "desconhecida")
                count = cat.get("total", 0)
                importance = cat.get("avg_importance", 0)
                last_message = cat.get("last_message", "desconhecida")
                
                cat_info = f"{category} ({count} msgs)"
                
                if importance >= 4:
                    high_importance.append(cat_info)
                elif importance >= 3:
                    medium_importance.append(cat_info)
                else:
                    low_importance.append(cat_info)
            
            # Monta resposta
            response = f"🧠 *Memória do Assistente*\n\n"
            response += f"🔢 Total de mensagens: {total_messages}\n\n"
            
            if high_importance:
                response += "⭐ *Alta Importância:*\n"
                response += "\n".join([f"  • {cat}" for cat in high_importance]) + "\n\n"
                
            if medium_importance:
                response += "📝 *Média Importância:*\n"
                response += "\n".join([f"  • {cat}" for cat in medium_importance]) + "\n\n"
                
            if low_importance:
                response += "📌 *Baixa Importância:*\n"
                response += "\n".join([f"  • {cat}" for cat in low_importance]) + "\n\n"
            
            response += "\nDica: Para buscar informações específicas, pergunte diretamente sobre o assunto."
                
            # Enviar com markdown
            # Procura onde tá o problema - caracteres especiais nos nomes das categorias
            response = response.replace('*', '').replace('_', '')  # Remove caracteres markdown problemáticos
            # Ou simplesmente desative o markdown:
            # await update.message.reply_text(response, parse_mode=None)
            await update.message.reply_text(response, parse_mode='Markdown')
            
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
            
    async def handle_lembrar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa o comando /lembrar [tópico]"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            
            # Extrai o tópico da mensagem
            message_text = update.message.text
            topic = message_text.replace('/lembrar', '').strip()
            
            if not topic:
                await update.message.reply_text("🧠 Por favor, especifique um tópico para eu lembrar.\nExemplo: /lembrar projeto XYZ")
                return
                
            # Avisa que está buscando
            processing_msg = await update.message.reply_text(f"🔍 Buscando memórias sobre: {topic}...")
            
            # Busca no sistema de memória
            relevant_memories = await self.llm_agent.memory.get_relevant_context(
                query=topic,
                user_id=user_id,
                chat_id=chat_id,
                limit=5,
                time_window=365 * 24 * 60  # Um ano inteiro
            )
            
            if not relevant_memories:
                await processing_msg.edit_text(f"🤔 Não encontrei memórias específicas sobre '{topic}'.")
                return
                
            # Gera um resumo usando o LLM
            memories_text = "\n\n".join([f"{mem['role']}: {mem['content']}" for mem in relevant_memories])
            
            summary_prompt = f"""
            Estas são memórias recuperadas sobre o tópico '{topic}':
            
            {memories_text}
            
            Por favor, resuma o que sabemos sobre este tópico de forma concisa e natural.
            Inclua detalhes específicos, datas, números e outras informações concretas que foram mencionadas.
            Se houver divergências ou evolução do assunto ao longo do tempo, indique isso.
            """
            
            # Gera o resumo
            summary_response = await self.llm_agent._call_openai_api([
                {"role": "system", "content": "Você é um assistente que resume memórias sobre tópicos específicos."},
                {"role": "user", "content": summary_prompt}
            ])
            
            summary = summary_response.choices[0].message.content
            
            # Formata a resposta final
            response = f"🧠 **Memórias sobre '{topic}'**\n\n{summary}"
            
            # Envia o resumo
            await processing_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao processar comando /lembrar: {e}", exc_info=True)
            await update.message.reply_text("Erro ao buscar memórias. Tente novamente!")

# Instância global do handler
telegram_llm_handler = TelegramLLMHandler()