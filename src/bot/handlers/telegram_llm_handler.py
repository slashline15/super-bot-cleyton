# handlers/telegram_llm_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from src.bot.utils.config_manager import ConfigManager, EDITABLE_CONFIGS
from src.bot.agents.llm_agent import LLMAgent
from src.bot.utils.audio_utils import transcribe_audio
from src.bot.utils.token_tracker import TokenTracker
import logging
import asyncio
import os

logger = logging.getLogger('TelegramLLMHandler')

# Estados para a conversa de configuração
CONFIG_SELECT, CONFIG_EDIT = range(2)

class TelegramLLMHandler:
    def __init__(self):
        self.llm_agent = LLMAgent()
        # Guarda config de debug por usuário
        self.debug_users = {}
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
        """Processa mensagens de texto e áudio do Telegram"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            processing_message = None
            
            if update.message.text:
                # Processa mensagem de texto
                user_message = update.message.text
                logger.info(f"Recebendo mensagem. User ID: {user_id}, Chat ID: {chat_id}")
                logger.info(f"Conteúdo: {user_message[:50]}...")
                
            elif update.message.voice:
                # Processa mensagem de voz
                logger.info("Mensagem de voz recebida, iniciando transcrição...")
                processing_message = await update.message.reply_text("🎤 Processando seu áudio...")
                
                voice = update.message.voice
                audio_file = await voice.get_file()
                
                # Baixa o arquivo de áudio
                audio_path = f"temp_audio_{user_id}.ogg"
                await audio_file.download_to_drive(audio_path)
                
                # Transcreve o áudio
                user_message = await transcribe_audio(audio_path)
                logger.info(f"Áudio transcrito: {user_message[:50]}...")
                
                # Remove o arquivo temporário
                import os
                os.remove(audio_path)
                
            else:
                await update.message.reply_text("Desculpe, só processo mensagens de texto e áudio.")
                return
            
            # Processa a mensagem com o LLM
            logger.info("Iniciando processamento com LLM...")
            response = await self.llm_agent.process_message(
                text=user_message,  # CORRIGIDO aqui
                user_id=user_id,
                chat_id=chat_id
            )
            logger.info("Processamento LLM concluído")
            
            # Apaga a mensagem de processamento, se existir
            if processing_message:
                await processing_message.delete()
            
            # Envia a resposta
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
            
            # Apaga a mensagem de processamento em caso de erro também
            if 'processing_message' in locals() and processing_message:
                try:
                    await processing_message.delete()
                except:
                    pass
                
        await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua mensagem. Desculpa é o caralho. O GPT é um bosta. Só o o3 que salva (e muito) a primeira geração.")
            
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
            
    async def handle_debug(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Liga/desliga o modo debug"""
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            # Sem argumento mostra estado atual
            is_debug = self.debug_users.get(user_id, False)
            await update.message.reply_text(
                f"🛠 Modo debug está {'ATIVADO ✅' if is_debug else 'DESATIVADO ❌'}\n"
                f"Use /debug on para ativar ou /debug off para desativar."
            )
            return
        
        command = args[0].lower()
        if command == "on":
            self.debug_users[user_id] = True
            await update.message.reply_text("🛠 Modo debug ATIVADO! Vou mostrar logs detalhados durante o processamento.")
        elif command == "off":
            self.debug_users[user_id] = False
            await update.message.reply_text("🛠 Modo debug DESATIVADO! Logs suprimidos.")
        else:
            await update.message.reply_text("🛠 Uso: /debug on para ativar ou /debug off para desativar.")
    
    async def handle_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Envia um resumo dos logs da sessão atual."""
        try:
            from src.bot.utils.log_config import export_log_summary
            
            # Avisa que está gerando o resumo
            processing_msg = await update.message.reply_text("📊 Gerando resumo de logs...")
            
            # Exporta o resumo
            log_file = export_log_summary()
            
            # Envia o arquivo
            with open(log_file, 'rb') as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=file,
                    filename=os.path.basename(log_file),
                    caption="📝 Resumo dos logs da sessão atual"
                )
            
            # Atualiza a mensagem
            await processing_msg.edit_text("✅ Logs enviados com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro ao enviar logs: {e}", exc_info=True)
            await update.message.reply_text("❌ Erro ao gerar resumo de logs.")

    async def handle_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra estatísticas de uso de tokens"""
        try:
            tracker = TokenTracker()
            daily_stats = tracker.get_daily_stats()
            session_stats = tracker.get_session_stats()
            
            # Formata valores monetários
            daily_cost = f"${daily_stats['total_cost']:.4f}"
            session_cost = f"${session_stats['cost']:.4f}"
            
            # Monta resposta
            response = "📊 *Estatísticas de Uso*\n\n"
            
            # Sessão atual
            response += "*Sessão Atual:*\n"
            response += f"• Tokens: {session_stats['total_tokens']:,}\n"
            response += f"• Custo: {session_cost}\n"
            response += f"• Mensagens: {session_stats['requests']}\n\n"
            
            # Uso diário
            response += "*Uso Diário:*\n"
            response += f"• Tokens totais: {daily_stats['total_tokens']:,}\n"
            response += f"• Tokens de entrada: {daily_stats['input_tokens']:,}\n"
            response += f"• Tokens de saída: {daily_stats['output_tokens']:,}\n"
            response += f"• Custo total: {daily_cost}\n\n"
            
            # Uso por provedor
            response += "*Uso por Provedor:*\n"
            for provider, data in daily_stats["providers"].items():
                provider_cost = f"${data['total_cost']:.4f}"
                provider_tokens = data["total_tokens"]["input"] + data["total_tokens"]["output"]
                response += f"• {provider.upper()}: {provider_tokens:,} tokens, {provider_cost}\n"
            
            await update.message.reply_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Erro ao exibir estatísticas de uso: {e}")
            await update.message.reply_text("❌ Ocorreu um erro ao buscar estatísticas.")

    async def handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manipula o comando /config para gerenciar configurações"""
        config_manager = ConfigManager()
        current_configs = config_manager.get_all()
        
        # Cria um teclado inline com as opções de configuração
        keyboard = []
        for key, value in current_configs.items():
            # Formata o valor para exibição
            if key == "custom_prompt" and value:
                display_value = f"{value[:20]}..." if len(value) > 20 else value
            else:
                display_value = str(value)
                
            keyboard.append([InlineKeyboardButton(
                f"{key}: {display_value}",
                callback_data=f"config_{key}"
            )])
        
        # Adiciona botão para redefinir tudo
        keyboard.append([InlineKeyboardButton("🔄 Reset All", callback_data="config_reset_all")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔧 *Configurações do Bot*\n\n"
            "Clique em uma opção para editá-la:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIG_SELECT

    async def config_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa botões do menu de configuração"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        config_manager = ConfigManager()
        
        if data == "config_reset_all":
            # Reseta todas as configurações
            config_manager.reset()
            await query.edit_message_text(
                "✅ Todas as configurações foram redefinidas para valores padrão.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Extrai a chave de configuração
        config_key = data.replace("config_", "")
        
        if config_key in EDITABLE_CONFIGS:
            # Prepara para editar esta configuração
            config_def = EDITABLE_CONFIGS[config_key]
            current_value = config_manager.get(config_key)
            
            # Texto de instrução baseado no tipo
            instruction_text = ""
            if config_def["type"] == "select":
                options = config_def["options"]
                keyboard = []
                for option in options:
                    keyboard.append([InlineKeyboardButton(
                        f"{'✓ ' if option == current_value else ''}{option}",
                        callback_data=f"set_{config_key}_{option}"
                    )])
                keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="config_back")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔧 *Editar {config_key}*\n\n"
                    f"*Descrição:* {config_def['description']}\n"
                    f"*Valor atual:* `{current_value}`\n\n"
                    f"Selecione uma opção:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return CONFIG_EDIT
            
            elif config_def["type"] == "bool":
                # Para boolean, oferecemos botões Sim/Não
                keyboard = [
                    [
                        InlineKeyboardButton("✓ Sim", callback_data=f"set_{config_key}_true"),
                        InlineKeyboardButton("❌ Não", callback_data=f"set_{config_key}_false")
                    ],
                    [InlineKeyboardButton("🔙 Voltar", callback_data="config_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🔧 *Editar {config_key}*\n\n"
                    f"*Descrição:* {config_def['description']}\n"
                    f"*Valor atual:* `{current_value}`\n\n"
                    f"Selecione uma opção:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return CONFIG_EDIT
            
            else:
                # Para outros tipos, pedimos entrada de texto
                instruction_text = f"Digite o novo valor para *{config_key}*:\n\n"
                
                if config_def["type"] == "float":
                    min_val = config_def.get("min", "-∞")
                    max_val = config_def.get("max", "∞")
                    instruction_text += f"*Tipo:* Número decimal entre {min_val} e {max_val}\n"
                
                elif config_def["type"] == "int":
                    min_val = config_def.get("min", "-∞")
                    max_val = config_def.get("max", "∞")
                    instruction_text += f"*Tipo:* Número inteiro entre {min_val} e {max_val}\n"
                
                elif config_def.get("multiline", False):
                    instruction_text += "*Tipo:* Texto (múltiplas linhas permitidas)\n"
                
                else:
                    instruction_text += "*Tipo:* Texto\n"
                
                instruction_text += f"\n*Valor atual:* `{current_value}`\n\n"
                instruction_text += "Responda com o novo valor ou /cancel para cancelar."
                
                # Salva a configuração sendo editada no contexto
                context.user_data["editing_config"] = config_key
                
                await query.edit_message_text(
                    instruction_text,
                    parse_mode='Markdown'
                )
                return CONFIG_EDIT
        
        elif config_key == "back":
            # Volta para o menu principal
            await self.handle_config(update, context)
            return CONFIG_SELECT
        
        return ConversationHandler.END

    async def config_set_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa valores digitados pelo usuário"""
        if "editing_config" not in context.user_data:
            await update.message.reply_text("❌ Erro: nenhuma configuração sendo editada.")
            return ConversationHandler.END
        
        config_key = context.user_data["editing_config"]
        new_value = update.message.text
        
        # Verifica se o usuário cancelou
        if new_value.lower() == "/cancel":
            await update.message.reply_text("🔄 Edição cancelada.")
            return ConversationHandler.END
        
        # Tenta definir o novo valor
        config_manager = ConfigManager()
        if config_manager.set(config_key, new_value):
            await update.message.reply_text(
                f"✅ Configuração *{config_key}* atualizada para *{new_value}*.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Valor inválido para *{config_key}*. Tente novamente ou use /cancel.",
                parse_mode='Markdown'
            )
            return CONFIG_EDIT
        
        return ConversationHandler.END

    async def config_callback_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks de botões para definir valores"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("set_"):
            # Formato: set_config_key_value
            parts = data.split("_", 2)
            if len(parts) >= 3:
                config_key = parts[1]
                config_value = parts[2]
                
                # Casos especiais para boolean
                if config_value == "true":
                    config_value = True
                elif config_value == "false":
                    config_value = False
                
                # Tenta definir o valor
                config_manager = ConfigManager()
                if config_manager.set(config_key, config_value):
                    await query.edit_message_text(
                        f"✅ Configuração *{config_key}* atualizada para *{config_value}*.",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Erro ao definir *{config_key}*.",
                        parse_mode='Markdown'
                    )
        
        return ConversationHandler.END

def setup_config_handlers(application):
        """Configura os handlers para o comando de configuração"""
        handler = ConversationHandler(
            entry_points=[CommandHandler("config", telegram_llm_handler.handle_config)],
            states={
                CONFIG_SELECT: [
                    CallbackQueryHandler(telegram_llm_handler.config_button, pattern=r'^config_')
                ],
                CONFIG_EDIT: [
                    CallbackQueryHandler(telegram_llm_handler.config_callback_set, pattern=r'^set_'),
                    CallbackQueryHandler(telegram_llm_handler.config_button, pattern=r'^config_'),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_llm_handler.config_set_value)
                ]
            },
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
        )
        application.add_handler(handler)


telegram_llm_handler = TelegramLLMHandler()
# wm testes