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

# ================= CONFIG =================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
DURATA_ORE = 24

# aste per chat
aste = {}

# ================= UTILS =================
def estrai_importo(testo):
    if not testo:
        return None
    m = re.search(r"(\d+)", testo)
    return int(m.group(1)) if m else None

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    testo = msg.caption if msg.photo else msg.text
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    base = estrai_importo(testo)
    if base is None:
        await msg.reply_text("❌ Base d'asta non valida")
        return

    aste[msg.chat_id] = {
        "base": base,
        "attuale": base,
        "attiva": False,
        "fine": None,
        "post_id": msg.message_id,
    }

    await msg.reply_text(
        f"📦 Vendita registrata\n"
        f"💰 Base d’asta: {base}€\n"
        f"👉 L'asta parte alla prima offerta UGUALE alla base"
    )

# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.text:
        return

    if msg.chat_id not in aste:
        return

    asta = aste[msg.chat_id]
    valore = estrai_importo(msg.text)
    if valore is None:
        return

    # asta non partita
    if not asta["attiva"]:
        if valore == asta["base"]:
            asta["attiva"] = True
            asta["fine"] = datetime.utcnow() + timedelta(hours=DURATA_ORE)
            asta["attuale"] = valore

            await msg.reply_text(
                f"✅ ASTA PARTITA!\n"
                f"💰 Prezzo attuale: {valore}€\n"
                f"⏰ Fine tra 24 ore"
            )
        return

    # asta attiva
    if valore > asta["attuale"]:
        asta["attuale"] = valore
        await msg.reply_text(f"⬆️ Nuova offerta valida: {valore}€")

# ================= SHOP =================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("🛒 Nessuna asta attiva")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in aste.values():
        stato = "ATTIVA" if a["attiva"] else "IN ATTESA"
        testo += f"💰 {a['attuale']}€ ({stato})\n"

    await update.message.reply_text(testo)

# ================= SCADENZE =================
async def controlla_scadenze(context: ContextTypes.DEFAULT_TYPE):
    ora = datetime.utcnow()
    for chat_id, asta in list(aste.items()):
        if asta["attiva"] and asta["fine"] and ora >= asta["fine"]:
            await context.bot.send_message(
                chat_id,
                f"🏁 ASTA TERMINATA\n💰 Prezzo finale: {asta['attuale']}€"
            )
            del aste[chat_id]

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.ALL, vendita))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, offerta))

    app.job_queue.run_repeating(controlla_scadenze, interval=60, first=60)

    app.run_polling()

if __name__ == "__main__":
    main()
