import os
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

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN non trovato nelle variabili d'ambiente")

# =========================
# STORAGE IN MEMORIA
# =========================
aste = {}
next_id = 1

# =========================
# UTILS
# =========================
def render_asta(a):
    fine = (
        "⏳ In attesa della prima offerta"
        if a["fine"] is None
        else a["fine"].strftime("%d/%m %H:%M")
    )

    return (
        f"🆔 Asta #{a['id']}\n"
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine asta: {fine}\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )

def estrai_importo(text):
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None

# =========================
# COMANDI
# =========================
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Ciao!\n"
        "Per creare un’asta scrivi:\n\n"
        "#vendita titolo, base\n\n"
        "Oppure invia una foto con la stessa descrizione."
    )

# =========================
# CREAZIONE ASTA
# =========================
def vendita(update: Update, context: CallbackContext):
    global next_id

    msg = update.message
    testo = msg.caption if msg.photo else msg.text
    if not testo or "#vendita" not in testo.lower():
        return

    m = re.search(r"#vendita\s+(.+?),\s*(\d+)", text, re.IGNORECASE)
    if not m:
        return

    titolo = m.group(1).strip()
    base = int(m.group(2))

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "fine": None,
        "attiva": True,
        "chat_id": msg.chat_id,
        "message_id": None,
        "foto": msg.photo[-1].file_id if msg.photo else None,
    }

    aste[next_id] = asta
    next_id += 1

    testo = render_asta(asta)

    if asta["foto"]:
        sent = msg.reply_photo(photo=asta["foto"], caption=testo)
    else:
        sent = msg.reply_text(testo)

    asta["message_id"] = sent.message_id

# =========================
# OFFERTA
# =========================
def offerta(update: Update, context: CallbackContext):
    msg = update.message

    if not msg.reply_to_message:
        return

    testo_reply = (
        msg.reply_to_message.caption
        or msg.reply_to_message.text
        or ""
    )

    m = re.search(r"Asta #(\d+)", testo_reply)
    if not m:
        return

    asta_id = int(m.group(1))
    asta = aste.get(asta_id)

    if not asta or not asta["attiva"]:
        return

    valore = estrai_importo(msg.text)
    if valore is None:
        return

    if valore <= asta["attuale"]:
        msg.reply_text("❌ Offerta troppo bassa.")
        return

    asta["attuale"] = valore

    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=24)

    nuovo_testo = render_asta(asta)

    if msg.reply_to_message.photo:
        context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=nuovo_testo,
        )
    else:
        context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=nuovo_testo,
        )

# =========================
# MAIN
# =========================
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(
        Filterr"text & Filters.regex(r"(?i)^#vendita")) |  Filters.photo,
        vendita
    ))
    dp.add_handler(MessageHandler(Filters.reply & Filters.text, offerta))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
