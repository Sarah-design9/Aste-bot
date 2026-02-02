import logging
import re
from datetime import datetime, timedelta
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ========= CONFIG =========
TOKEN = os.getenv("TOKEN")  # DEVE stare su Railway
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ========= UTILS =========
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"
    fine = a["fine"].strftime("%d/%m %H:%M") if a["fine"] else "⏳ In attesa prima offerta"

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi con un importo per offrire"
    )

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ciao!\n"
        "Per vendere scrivi:\n"
        "#vendita NomeOggetto 10€\n"
        "Puoi allegare una foto."
    )

# ========= VENDITA =========
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if not base_raw:
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
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta
        )
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ========= OFFERTE =========
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message or not msg.text:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw:
        return

    valore = int(valore_raw)

    asta = None
    for a in aste.values():
        if a["message_id"] == msg.reply_to_message.message_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    # prima offerta → set fine asta
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        return

    if valore <= asta["attuale"]:
        return  # offerta più bassa ignorata SENZA crash

    asta["attuale"] = valore
    testo = render_asta(asta)

    try:
        await context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=testo
        )
    except:
        await context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=testo
        )

# ========= SHOP =========
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attive = [a for a in aste.values() if a["attiva"]]
    if not attive:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in attive:
        testo += f"#{a['id']} – {a['titolo']} | 💰 {a['attuale']}€\n"

    await update.message.reply_text(testo)

# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.REPLY, vendita))
    app.add_handler(MessageHandler(filters.PHOTO, vendita))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))

    app.run_polling()

if __name__ == "__main__":
    main()
