# handlers/telegram_llm_handler.py
from telegram import Update
from telegram.ext import Application, ContextTypes
from telegram.constants import ChatAction
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from src.bot.utils.config_manager import ConfigManager, EDITABLE_CONFIGS
from src.bot.agents.llm_agent import LLMAgent
from src.bot.utils.audio_utils import transcribe_audio  # mantenha só o que realmente é de áudio
from src.bot.utils.cnpj import busca_CNPJ, format_cnpj_info, CNPJError, validar_cnpj, escape_markdown # import das funções de CNPJ
from src.bot.utils.token_tracker import TokenTracker
import logging
import asyncio
import os
import json
import datetime
from src.bot.memory.format_utils import format_context_for_provider

logger = logging.getLogger('TelegramLLMHandler')

# Estados para o ConversationHandler
ESPERANDO_CNPJ = 0

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
            await update.message.chat.send_action(action=ChatAction.TYPING)
            response = await self.llm_agent.process_message(
                text=user_message,
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
            
            # Apaga a mensagem de processamento em caso de erro
            if 'processing_message' in locals() and processing_message:
                try:
                    await processing_message.delete()
                except:
                    pass
                    
            # MOVIDO PRA DENTRO DO EXCEPT (antes estava fora)
            await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua mensagem. O GPT o3 é FODAAA.")
            
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
            summary_response_text = await self.llm_agent._client.chat([
                {"role": "system", "content": "Você é um assistente que resume memórias sobre tópicos específicos."},
                {"role": "user", "content": summary_prompt}
            ])
            
            summary = summary_response_text
            
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

    async def handle_debug_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analisa e salva informações sobre o contexto atual enviado ao LLM"""
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

            # Mensagem opcional a ser usada como consulta
            # (usa argumentos do comando ou "test query" como padrão)
            query = " ".join(context.args) if context.args else "Esse é um teste de contexto. Por favor, analise meu contexto."

            # Avisa o usuário que estamos processando
            processing_msg = await update.message.reply_text("🔍 Analisando contexto...")

            # 1. Pega contexto do MemoryManager (como no processo normal)
            raw_ctx = await self.llm_agent.memory.get_context_messages(user_id, chat_id, query=query)

            # 2. Formata para o provedor atual
            messages = format_context_for_provider(
                ctx_messages=raw_ctx,
                provider=self.llm_agent._client.provider,
                system_prompt=self.llm_agent.system_prompt,
                user_message=query
            )

            # 3. Analisa os tokens
            token_counts = []
            total_tokens = 0

            # Conta tokens por mensagem
            for i, msg in enumerate(messages):
                content = msg.get("content", "")
                if not content and "parts" in msg:
                    # Para o Gemini, extrai o conteúdo da estrutura "parts"
                    parts = msg.get("parts", [])
                    content = parts[0].get("text", "") if parts else ""

                tokens = self.llm_agent.count_tokens(content)
                total_tokens += tokens

                role = msg.get("role", "unknown")
                token_counts.append({
                    "index": i,
                    "role": role,
                    "tokens": tokens,
                    "content_preview": content[:100] + "..." if len(content) > 100 else content
                })

            # 4. Prepara resposta para o usuário
            provider = self.llm_agent._client.provider
            model = self.llm_agent._client.name

            summary = f"📊 **Análise de Contexto** (Provedor: {provider}, Modelo: {model})\n\n"
            summary += f"📋 **Total de mensagens**: {len(messages)}\n"
            summary += f"🔢 **Total de tokens**: {total_tokens}\n\n"

            # Adiciona detalhes por tipo de mensagem
            system_count = sum(1 for m in messages if m.get("role") == "system")
            user_count = sum(1 for m in messages if m.get("role") == "user" or m.get("role") == "human")
            assistant_count = sum(1 for m in messages if m.get("role") == "assistant" or m.get("role") == "model")

            summary += f"🤖 **Mensagens system**: {system_count}\n"
            summary += f"👤 **Mensagens usuário**: {user_count}\n"
            summary += f"💬 **Mensagens assistente**: {assistant_count}\n\n"

            # 5. Salva o arquivo de debug
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = os.path.join("data", "debug")
            os.makedirs(debug_dir, exist_ok=True)

            debug_file = os.path.join(debug_dir, f"context_debug_{user_id}_{timestamp}.json")

            debug_data = {
                "metadata": {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "timestamp": timestamp,
                    "provider": provider,
                    "model": model,
                    "query": query
                },
                "stats": {
                    "total_messages": len(messages),
                    "total_tokens": total_tokens,
                    "system_count": system_count,
                    "user_count": user_count,
                    "assistant_count": assistant_count
                },
                "token_analysis": token_counts,
                "raw_context": [
                    {"role": msg.get("role", "unknown"),
                     "content": msg.get("content", "")
                      if "content" in msg else (
                        msg.get("parts", [{}])[0].get("text", "")
                        if "parts" in msg and msg.get("parts") else ""
                      )}
                    for msg in messages
                ],
                "full_messages": messages
            }

            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

            # 6. Atualiza a resposta para o usuário
            summary += f"📁 Arquivo de debug salvo em: `{debug_file}`\n\n"
            summary += "❓ Para ver mais detalhes, analise o arquivo JSON que contém:\n"
            summary += "- Contexto completo recuperado\n"
            summary += "- Análise detalhada de tokens\n"
            summary += "- Mensagens exatas enviadas ao LLM\n"

            await processing_msg.edit_text(summary, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro ao analisar contexto: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Erro ao analisar contexto: {str(e)}")
    
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
#---------------------------------------------------------------
# CNPJ
#---------------------------------------------------------------

async def cnpj_comando(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manipula o comando /cnpj."""
    args = context.args
    
    # Se o usuário já forneceu o CNPJ como argumento (/cnpj 12345678901234)
    if args and len(args) > 0:
        cnpj_texto = args[0]
        await processar_cnpj(update, context, cnpj_texto)
        return ConversationHandler.END
    
    # Se o usuário apenas digitou /cnpj sem argumentos
    await update.message.reply_text(
        "Por favor, digite o CNPJ que deseja consultar (só os números ou com pontuação):"
    )
    return ESPERANDO_CNPJ

async def receber_cnpj(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o CNPJ enviado pelo usuário após o pedido."""
    cnpj_texto = update.message.text
    await processar_cnpj(update, context, cnpj_texto)
    return ConversationHandler.END

async def processar_cnpj(update: Update, context: ContextTypes.DEFAULT_TYPE, cnpj_texto: str) -> None:
    """Processa o CNPJ fornecido, faz a consulta e envia a resposta."""
    message = update.effective_message
    
    # Mostra "digitando..." enquanto processa
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    try:
        # Valida o CNPJ antes de fazer a consulta
        cnpj_limpo = validar_cnpj(cnpj_texto)
        
        # Faz a busca
        dados = busca_CNPJ(cnpj_limpo)
        
        # Formatar para o Telegram (modifiquei o formato HTML para funcionar bem no Telegram)
        texto = format_cnpj_info(dados, formato="markdown")
        
        # Botões para outros formatos
        keyboard = [
            [
                InlineKeyboardButton("📄 Texto Simples", callback_data=f"cnpj_formato_{cnpj_limpo}_text"),
                InlineKeyboardButton("🔍 Detalhes", callback_data=f"cnpj_detalhe_{cnpj_limpo}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Escapa caracteres especiais para MarkdownV2
        texto_escapado = escape_markdown(texto)
        
        await message.reply_text(
            text=texto_escapado,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'  # Importante para o Telegram interpretar a formatação markdown
        )
        
    except CNPJError as e:
        await message.reply_text(f"❌ Erro: {str(e)}")
    except Exception as e:
        await message.reply_text(f"❌ Erro inesperado: {str(e)}")

async def botao_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde aos cliques de botão para mudar formato ou mostrar detalhes."""
    query = update.callback_query
    await query.answer()
    
    # Exemplo: cnpj_formato_43836352000194_text
    dados = query.data.split('_')
    
    if len(dados) < 4:
        return
    
    tipo = dados[1]  # formato ou detalhe
    cnpj = dados[2]  # o CNPJ
    
    try:
        if tipo == "formato":
            formato = dados[3]  # text, html, etc
            resultado = busca_CNPJ(cnpj)
            texto = format_cnpj_info(resultado, formato=formato)
            
            # Para texto, não usamos parse_mode
            if formato == "text":
                await query.edit_message_text(
                    text=texto,
                    reply_markup=query.message.reply_markup
                )
            else:
                await query.edit_message_text(
                    text=texto,
                    reply_markup=query.message.reply_markup,
                    parse_mode='MarkdownV2'
                )
                
        elif tipo == "detalhe":
            # Busca dados extras ou mostra informações específicas
            await query.message.reply_text(
                "🔍 *Detalhes adicionais*\n\n"
                "Para exportar os dados completos em outros formatos, use os comandos:\n"
                f"`/cnpj_html {cnpj}`\n"
                f"`/cnpj_json {cnpj}`",
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        await query.edit_message_text(
            text=f"❌ Erro ao processar sua solicitação: {str(e)}",
            reply_markup=query.message.reply_markup
        )

# Funções adicionais para exportação em outros formatos (opcional)
async def cnpj_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia os dados do CNPJ no formato HTML como arquivo."""
    args = context.args
    
    if not args or len(args) == 0:
        await update.message.reply_text("Use /cnpj_html seguido do número do CNPJ")
        return
    
    try:
        cnpj = validar_cnpj(args[0])
        dados = busca_CNPJ(cnpj)
        html = format_cnpj_info(dados, formato="html")
        
        # Criar arquivo temporário
        import tempfile
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
        temp.write(html)
        temp.close()
        
        # Enviar o arquivo
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(temp.name, 'rb'),
            filename=f"cnpj_{cnpj}.html",
            caption=f"Dados do CNPJ {cnpj} em formato HTML"
        )
        
        # Limpar
        import os
        os.unlink(temp.name)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")

async def cnpj_json(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia os dados do CNPJ no formato JSON como arquivo."""
    args = context.args
    
    if not args or len(args) == 0:
        await update.message.reply_text("Use /cnpj_json seguido do número do CNPJ")
        return
    
    try:
        cnpj = validar_cnpj(args[0])
        dados = busca_CNPJ(cnpj)
        json_str = format_cnpj_info(dados, formato="json")
        
        # Criar arquivo temporário
        import tempfile
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8')
        temp.write(json_str)
        temp.close()
        
        # Enviar o arquivo
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(temp.name, 'rb'),
            filename=f"cnpj_{cnpj}.json",
            caption=f"Dados do CNPJ {cnpj} em formato JSON"
        )
        
        # Limpar
        import os
        os.unlink(temp.name)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")

# Para registrar no bot:
def registrar_cnpj_handlers(application: Application) -> None:
    """Registra os handlers relacionados ao CNPJ."""
    
    # Handler para conversa quando usuário digita apenas /cnpj
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("cnpj", cnpj_comando)],
        states={
            ESPERANDO_CNPJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cnpj)],
        },
        fallbacks=[],
    )
    
    application.add_handler(conv_handler)
    
    # Handler para os botões de callback
    application.add_handler(CallbackQueryHandler(botao_callback, pattern="^cnpj_"))
    
    # Handlers para comandos de exportação
    application.add_handler(CommandHandler("cnpj_html", cnpj_html))
    application.add_handler(CommandHandler("cnpj_json", cnpj_json))






#---------------------------------------------------------------
telegram_llm_handler = TelegramLLMHandler()
# wm testes