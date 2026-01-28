from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

import os

# Prendi token dalle variabili d'ambiente
TOKEN = os.environ.get('TOKEN')

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Ciao! Il bot è attivo e funzionante!")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
