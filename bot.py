import os
import re
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN mancante su Railway")

logging.basicConfig(level=logging.INFO)

ASTE = {}  # key = message_id del messaggio del BOT

# ================= UTILS =================
def estrai_prezzo(testo: str):
    if not testo:
        return None
    m = re.search(r"\b(\d+)\b", testo)
    return int(m.group(1)) if m else None


def testo_asta(a):
    testo = (
        f"📦 ASTA ATTIVA\n\n"
        f"💰 Base d'asta: {a['base']} €\n"
        f"🔥 Offerta attuale: {a['attuale']} €\n"
    )

    if a["fine"]:
        testo += f"⏰ Fine asta: {a['fine'].strftime('%d/%m %H:%M')}\n"
    else:
        testo += "⏳ Fine asta: alla prima offerta\n"

    testo += "\n✍️ Rispondi a QUESTO messaggio con l'importo"
    return testo

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aste attivo\n\n"
        "#vendita nome-oggetto prezzo\n"
        "(foto opzionale)\n\n"
        "Le offerte devono essere RISPOSTE al messaggio dell’asta."
    )

# ================= VENDITA (TESTO) =================
async def vendita_testo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.text or "#vendita" not in msg.text.lower():
        return

    base = estrai_prezzo(msg.text)
    if base is None:
        return

    asta = {
        "base": base,
        "attuale": base,
        "fine": None,
        "chat_id": msg.chat_id,
    }

    bot_msg = await msg.reply_text(testo_asta(asta))
    ASTE[bot_msg.message_id] = asta

    logging.info("Vendita senza foto creata")

# ================= VENDITA (FOTO) =================
async def vendita_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.caption or "#vendita" not in msg.caption.lower():
        return

    base = estrai_prezzo(msg.caption)
    if base is None:
        return

    asta = {
        "base": base,
        "attuale": base,
        "fine": None,
        "chat_id": msg.chat_id,
    }

    bot_msg = await msg.reply_photo(
        photo=msg.photo[-1].file_id,
        caption=testo_asta(asta)
    )

    ASTE[bot_msg.message_id] = asta
    logging.info("Vendita con foto creata")

# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return

    asta = ASTE.get(msg.reply_to_message.message_id)
    if not asta:
        return

    prezzo = estrai_prezzo(msg.text)
    if prezzo is None:
        return

    if prezzo <= asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=24)

    asta["attuale"] = prezzo

    await context.bot.edit_message_text(
        chat_id=asta["chat_id"],
        message_id=msg.reply_to_message.message_id,
        text=testo_asta(asta)
    )

    logging.info(f"Nuova offerta valida: {prezzo}")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, vendita_testo))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, vendita_foto))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY & filters.ChatType.GROUPS, offerta))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
