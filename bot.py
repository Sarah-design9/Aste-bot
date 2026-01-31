import logging
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

TOKEN = "USA_VARIABILE_AMBIENTE"
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"
    fine = a["fine"].strftime("%d/%m %H:%M") if a["fine"] else "⏳ Nessuna offerta"

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi con un importo per offrire"
    )


# ================= START =================
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Ciao!\n\n"
        "Per mettere in vendita:\n"
        "#vendita NOME PREZZO\n\n"
        "Esempio:\n"
        "#vendita Playstation 5 200€\n\n"
        "Puoi aggiungere anche una foto 📸"
    )


# ================= VENDITA =================
def vendita(update: Update, context: CallbackContext):
    global next_id
    msg = update.message

    testo = msg.caption if msg.photo else msg.text
    if not testo or not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    titolo = " ".join(parti[1:-1])
    base_raw = re.sub(r"[^\d]", "", parti[-1])
    if not base_raw.isdigit():
        return

    base = int(base_raw)

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta
        )
    else:
        sent = msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1


# ================= OFFERTE =================
def offerta(update: Update, context: CallbackContext):
    msg = update.message
    if not msg.reply_to_message or not msg.text:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return

    valore = int(valore_raw)

    asta = None
    for a in aste.values():
        if a["message_id"] == msg.reply_to_message.message_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        return

    if valore <= asta["attuale"]:
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    try:
        context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=nuovo_testo
        )
    except:
        context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=nuovo_testo
        )


# ================= SHOP =================
def shop(update: Update, context: CallbackContext):
    attive = [a for a in aste.values() if a["attiva"]]
    if not attive:
        update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in attive:
        testo += f"#{a['id']} – {a['titolo']} | 💰 {a['attuale']}€\n"

    update.message.reply_text(testo)


# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("shop", shop))

    dp.add_handler(MessageHandler(Filters.photo | Filters.text, vendita))
    dp.add_handler(MessageHandler(Filters.reply & Filters.text, offerta))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
