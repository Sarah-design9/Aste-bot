from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import os

TOKEN = "INSERISCI_QUI_IL_TUO_TOKEN"

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if msg.reply_to_message:
        await msg.reply_text("✅ Ho ricevuto una RISPOSTA (reply)")
    else:
        await msg.reply_text("ℹ️ Messaggio normale ricevuto")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, debug))
app.run_polling()
