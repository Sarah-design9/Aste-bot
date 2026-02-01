import logging
import os
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTILS =================
def render_asta(a):
    fine_txt = (
        "⏳ In attesa della prima offerta"
        if a["fine"] is None
        else a["fine"].strftime("%d/%m %H:%M")
    )

    return (
        f"📦 {a['titolo']}\n"
        f"🆔 Asta #{a['id']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine_txt}\n\n"
        f"👉 Rispondi a QUESTO messaggio con un importo"
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT ASTE ATTIVO\n\n"
        "Crea un’asta con:\n"
        "#vendita nome prezzo\n\n"
        "Esempio:\n"
        "#vendita Scarpe 10€"
    )

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "con_foto": bool(msg.photo),
        "fine": None,
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = await msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[(asta["chat_id"], asta["message_id"])] = asta
    next_id += 1

# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not msg.text:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return
    valore = int(valore_raw)

    key = (msg.chat_id, msg.reply_to_message.message_id)
    if key not in aste:
        return

    asta = aste[key]

    # PRIMA OFFERTA
    if asta["fine"] is None:
        if valore < asta["base"]:
            return
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)
    else:
        if valore <= asta["attuale"]:
            return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    try:
        if asta["con_foto"]:
            await context.bot.edit_message_caption(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                caption=nuovo_testo,
            )
        else:
            await context.bot.edit_message_text(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                text=nuovo_testo,
            )
    except Exception as e:
        logging.error(f"Aggiornamento fallito: {e}")

# ================= SHOP =================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in aste.values():
        testo += f"#{a['id']} – {a['titolo']} | {a['attuale']}€\n"

    await update.message.reply_text(testo)

# ================= MAIN =================
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN mancante")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, offerta))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.REPLY, vendita))

    app.run_polling()

if __name__ == "__main__":
    main()
