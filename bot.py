import os
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

aste = {}   # message_id -> dati asta


# ───────────── START ─────────────
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Ciao!\n"
        "Per mettere un oggetto in vendita scrivi:\n\n"
        "📌 Nome oggetto\n"
        "💰 Base d'asta\n\n"
        "Puoi anche allegare una foto."
    )


# ───────────── VENDITA ─────────────
def vendita(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat_id

    if message.reply_to_message:
        return

    text = message.caption if message.photo else message.text
    if not text:
        return

    righe = text.split("\n")
    if len(righe) < 2:
        return

    nome = righe[0].strip()

    try:
        base = float(righe[1].replace("€", "").strip())
    except:
        return

    testo = (
        f"🛒 **{nome}**\n\n"
        f"💰 Base d'asta: {base:.2f}€\n"
        f"📈 Offerta attuale: {base:.2f}€\n"
        f"⏳ Fine asta: in attesa della prima offerta"
    )

    if message.photo:
        sent = context.bot.send_photo(
            chat_id=chat_id,
            photo=message.photo[-1].file_id,
            caption=testo,
            parse_mode="Markdown"
        )
    else:
        sent = context.bot.send_message(
            chat_id=chat_id,
            text=testo,
            parse_mode="Markdown"
        )

    aste[sent.message_id] = {
        "nome": nome,
        "base": base,
        "prezzo": base,
        "fine": None,
        "chat_id": chat_id,
    }


# ───────────── OFFERTE ─────────────
def offerta(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        return

    mid = message.reply_to_message.message_id
    if mid not in aste:
        return

    try:
        valore = float(message.text.replace("€", "").strip())
    except:
        return

    asta = aste[mid]

    if valore <= asta["prezzo"]:
        return

    asta["prezzo"] = valore

    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=24)

    fine_txt = asta["fine"].strftime("%d/%m %H:%M")

    testo = (
        f"🛒 **{asta['nome']}**\n\n"
        f"💰 Base d'asta: {asta['base']:.2f}€\n"
        f"📈 Offerta attuale: {asta['prezzo']:.2f}€\n"
        f"⏳ Fine asta: {fine_txt}"
    )

    try:
        context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=mid,
            caption=testo,
            parse_mode="Markdown"
        )
    except:
        context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=mid,
            text=testo,
            parse_mode="Markdown"
        )


# ───────────── SHOP ─────────────
def shop(update: Update, context: CallbackContext):
    if not aste:
        update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "📦 **Aste attive**:\n\n"
    for a in aste.values():
        testo += f"• {a['nome']} – {a['prezzo']:.2f}€\n"

    update.message.reply_text(testo, parse_mode="Markdown")


# ───────────── MAIN ─────────────
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # ⚠️ ORDINE FONDAMENTALE ⚠️
    dp.add_handler(MessageHandler(Filters.reply & Filters.text, offerta))
    dp.add_handler(MessageHandler(Filters.photo, vendita))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.reply, vendita))

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("shop", shop))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
