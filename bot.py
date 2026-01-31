import logging
import re
from datetime import datetime, timedelta

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from telegram import Update

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTIL =================
def render_asta(a):
    fine = (
        "⏳ In attesa della prima offerta"
        if a["fine"] is None
        else a["fine"].strftime("%d/%m %H:%M")
    )

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine asta: {fine}\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )

# ================= START =================
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bot aste attivo")

# ================= OFFERTE =================
def offerta(update: Update, context: CallbackContext):
    msg = update.message

    if not msg.reply_to_message:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text or "")
    if not valore_raw:
        return

    valore = int(valore_raw)
    reply_id = msg.reply_to_message.message_id

    for asta in aste.values():
        if asta["message_id"] == reply_id and asta["attiva"]:

            if asta["fine"] is None:
                asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

            if valore < asta["attuale"]:
                return

            asta["attuale"] = valore
            testo = render_asta(asta)

            try:
                if asta["foto"]:
                    context.bot.edit_message_caption(
                        chat_id=asta["chat_id"],
                        message_id=asta["message_id"],
                        caption=testo
                    )
                else:
                    context.bot.edit_message_text(
                        chat_id=asta["chat_id"],
                        message_id=asta["message_id"],
                        text=testo
                    )
            except Exception as e:
                logging.error(e)

            return

# ================= VENDITA =================
def vendita(update: Update, context: CallbackContext):
    global next_id
    msg = update.message

    if msg.reply_to_message:
        return

    testo = msg.caption if msg.photo else msg.text
    if not testo or not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    titolo = " ".join(parti[1:-1])
    base = int(re.sub(r"[^\d]", "", parti[-1]))

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,
        "foto": bool(msg.photo),
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
    else:
        sent = msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ================= SHOP =================
def shop(update: Update, context: CallbackContext):
    attive = [a for a in aste.values() if a["attiva"]]
    if not attive:
        update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in attive:
        testo += f"{a['titolo']} – {a['attuale']}€\n"

    update.message.reply_text(testo)

# ================= MAIN =================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("shop", shop))

    # ⚠️ QUESTO ORDINE È FONDAMENTALE
    dp.add_handler(MessageHandler(Filters.reply & Filters.text & ~Filters.command, offerta))
    dp.add_handler(MessageHandler((Filters.text | Filters.photo) & ~Filters.reply, vendita))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
