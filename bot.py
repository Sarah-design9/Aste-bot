from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os

TOKEN = os.environ.get("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo e funzionante!")

# Nuovo handler per i messaggi di asta
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("#vendita"):
        await update.message.reply_text(f"Oggetto messo in vendita: {text[8:].strip()}")
    elif text.startswith("#offerta"):
        await update.message.reply_text(f"Nuova offerta: {text[7:].strip()}")
    elif text.startswith("#chiudi"):
        await update.message.reply_text("Asta chiusa!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

# Aggiungi handler per tutti i messaggi di testo
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
