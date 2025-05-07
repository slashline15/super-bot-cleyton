# python -m tests.test_bot

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters, CallbackQueryHandler
)
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TEST_SERCH")

# Estados para o ConversationHandler
ESPERANDO_CNPJ = 0

# Importar as funções que criamos
from src.bot.utils.cnpj import busca_CNPJ, format_cnpj_info, CNPJError, validar_cnpj

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
        
        await message.reply_text(
            text=texto,
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
    
def main():
    application = Application.builder().token(TOKEN).build()
    registrar_cnpj_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()
