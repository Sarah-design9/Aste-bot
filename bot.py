import os
import time
import threading
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

TOKEN = os.environ.get("TOKEN")

bot = Bot(TOKEN)
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# aste attive
auctions = {}
# formato:
# "id_asta": {
#   "oggetto": str,
#   "prezzo": int,
#   "utente": str,
#   "fine": timestamp
# }

def start_auction(update: Update, context: CallbackContext):
    try:
        # FORMATO:
        # ASTA oggetto | prezzo_iniziale | minuti
        testo = update.message.text.replace("ASTA", "").strip()
        oggetto, prezzo, minuti = testo.split("|")
        prezzo = int(prezzo.strip())
        minuti = int(minuti.strip())

        end_time = time.time() + minuti * 60
        auction_id = str(time.time())

        auctions[auction_id] = {
            "oggetto": oggetto.strip(),
            "prezzo": prezzo,
            "utente": update.message.from_user.username,
            "fine": end_time
        }

        update.message.reply_text(
            f"📢 ASTA INIZIATA\n"
            f"Oggetto: {oggetto}\n"
            f"Prezzo iniziale: {prezzo}€\n"
            f"Durata: {minuti} minuti\n\n"
            f"Scrivete SOLO NUMERI per fare offerte"
        )

        threading.Thread(target=close_auction, args=(auction_id, update.message.chat_id)).start()

    except:
        update.message.reply_text(
            "❌ Formato errato.\n"
            "Usa: ASTA oggetto | prezzo | minuti"
        )

def close_auction(auction_id, chat_id):
    while True:
        if time.time() >= auctions[auction_id]["fine"]:
            a = auctions[auction_id]
            bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⏰ ASTA TERMINATA\n"
                    f"Oggetto: {a['oggetto']}\n"
                    f"Vincitore: @{a['utente']}\n"
                    f"Prezzo finale: {a['prezzo']}€"
                )
            )
            del auctions[auction_id]
            break
        time.sleep(5)

def bid(update: Update, context: CallbackContext):
    if not update.message.text.isdigit():
        return

    offerta = int(update.message.text)
    utente = update.message.from_user.username

    for a in auctions.values():
        if offerta > a["prezzo"]:
            a["prezzo"] = offerta
            a["utente"] = utente
            update.message.reply_text(f"💰 Nuova offerta: {offerta}€ da @{utente}")
            break

dispatcher.add_handler(MessageHandler(Filters.regex("^ASTA"), start_auction))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bid))

updater.start_polling()
updater.idle()
