import os
import logging
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# LOG
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# TOKEN da Railway (NON nel codice)
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN non trovato nelle variabili Railway")

# --- COMANDI ---

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🤖 Bot aste attivo!\n\n"
        "Usa nel gruppo:\n"
        "#vendita nome prezzo\n\n"
        "Esempio:\n"
        "#vendita PS5 100"
    )

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("Comandi disponibili: /start")

# --- VENDITA ---

def vendita(update: Update, context: CallbackContext):
    text = update.message.text.lower()

    if not text.startswith("#vendita"):
        return

    parti = update.message.text.split(maxsplit=2)
    if len(parti) < 3:
        update.message.reply_text(
            "❌ Formato errato\n"
            "Usa: #vendita nome prezzo"
        )
        return

    nome = parti[1]
    prezzo = parti[2]

    msg = (
        "📢 NUOVA ASTA\n\n"
        f"🧾 Oggetto: {nome}\n"
        f"💰 Base d'asta: {prezzo}€\n"
        "📈 Offerta attuale: nessuna\n"
        "⏰ Fine asta: alla prima offerta + 24h"
    )

    update.message.reply_text(msg)

# --- AVVIO ---

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, vendita))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
