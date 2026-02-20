import os
import re
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")

aste = {}

# ------------------------
# /start
# ------------------------
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Ciao! Per mettere in vendita scrivi un post con FOTO e nel testo metti 'Vendita' e il prezzo.")

# ------------------------
# /shop
# ------------------------
def shop(update: Update, context: CallbackContext):
    if not aste:
        update.message.reply_text("Non ci sono aste attive.")
        return

    messaggio = "🛒 Aste attive:\n\n"
    for id_asta, dati in aste.items():
        messaggio += f"ID {id_asta} - {dati['titolo']} - Offerta attuale: {dati['prezzo']}€\n"

    update.message.reply_text(messaggio)

# ------------------------
# CREAZIONE ASTA (parser intelligente)
# ------------------------
def nuova_vendita(update: Update, context: CallbackContext):
    if not update.message.photo:
        return

    testo = update.message.caption
    if not testo:
        return

    if "vendita" not in testo.lower():
        return

    # Trova primo numero nel testo (prezzo base)
    match = re.search(r"\d+", testo.replace(".", ""))
    if not match:
        update.message.reply_text("Non trovo il prezzo base.")
        return

    prezzo_base = float(match.group())

    # Titolo = prima riga senza la parola vendita
    prima_riga = testo.split("\n")[0]
    titolo = prima_riga.lower().replace("vendita", "").replace(":", "").strip()
    if titolo == "":
        titolo = "Articolo"

    id_asta = len(aste) + 1

    aste[id_asta] = {
        "titolo": titolo,
        "prezzo": prezzo_base,
        "chat_id": update.message.chat_id,
        "message_id": update.message.message_id
    }

    nuovo_testo = f"🔥 ASTA ATTIVA 🔥\n\n📦 {titolo}\n💰 Offerta attuale: {prezzo_base}€"

    context.bot.edit_message_caption(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id,
        caption=nuovo_testo
    )

# ------------------------
# GESTIONE OFFERTE
# ------------------------
def offerta(update: Update, context: CallbackContext):
    if not update.message.reply_to_message:
        return

    testo = update.message.text
    if not testo:
        return

    match = re.search(r"\d+", testo.replace(".", ""))
    if not match:
        return

    offerta_valore = float(match.group())

    msg_id = update.message.reply_to_message.message_id

    for id_asta, dati in aste.items():
        if dati["message_id"] == msg_id:

            # ORA ACCETTA >=
            if offerta_valore >= dati["prezzo"]:
                dati["prezzo"] = offerta_valore

                nuovo_testo = f"🔥 ASTA ATTIVA 🔥\n\n📦 {dati['titolo']}\n💰 Offerta attuale: {offerta_valore}€"

                context.bot.edit_message_caption(
                    chat_id=dati["chat_id"],
                    message_id=dati["message_id"],
                    caption=nuovo_testo
                )
            else:
                update.message.reply_text("Offerta troppo bassa.")

            break

# ------------------------
# MAIN
# ------------------------
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("shop", shop))

    dp.add_handler(MessageHandler(Filters.photo & Filters.caption, nuova_vendita))
    dp.add_handler(MessageHandler(Filters.reply & Filters.text, offerta))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
