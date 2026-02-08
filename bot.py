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

# LOG
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")

# ======================
# MEMORIA ASTE
# ======================
# chat_id -> asta
aste = {}

# struttura asta:
# {
#   "post_id": int,
#   "base": int,
#   "attuale": int,
#   "attiva": bool,
#   "scadenza": datetime
# }

# ======================
# UTIL
# ======================
def estrai_prezzo(testo: str):
    match = re.search(r"(\d+)", testo)
    return int(match.group(1)) if match else None


# ======================
# VENDITA
# ======================
async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id

    if not msg.text:
        return

    if "#vendita" not in msg.text.lower():
        return

    base = estrai_prezzo(msg.text)
    if base is None:
        await msg.reply_text("❌ Prezzo base non valido.")
        return

    aste[chat_id] = {
        "post_id": msg.message_id,
        "base": base,
        "attuale": base,
        "attiva": False,
        "scadenza": None,
    }

    await msg.reply_text(
        f"📦 Vendita registrata!\n"
        f"💰 Base d'asta: {base}€\n"
        f"⏳ L'asta parte alla prima offerta UGUALE alla base."
    )


# ======================
# OFFERTE
# ======================
async def gestisci_offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = msg.chat_id

    if chat_id not in aste:
        return

    asta = aste[chat_id]

    prezzo = estrai_prezzo(msg.text)
    if prezzo is None:
        return

    # ASTA NON ANCORA PARTITA
    if not asta["attiva"]:
        if prezzo == asta["base"]:
            asta["attiva"] = True
            asta["attuale"] = prezzo
            asta["scadenza"] = datetime.utcnow() + timedelta(hours=24)

            await msg.reply_text(
                f"✅ Asta PARTITA!\n"
                f"💰 Prezzo attuale: {prezzo}€\n"
                f"⏰ Fine asta tra 24 ore."
            )
        else:
            # ignora silenziosamente
            return
        return

    # ASTA ATTIVA
    if prezzo > asta["attuale"]:
        asta["attuale"] = prezzo
        await msg.reply_text(f"⬆️ Nuova offerta valida: {prezzo}€")
    else:
        # più bassa o uguale → ignorata
        return


# ======================
# CONTROLLO SCADENZE
# ======================
async def controlla_scadenze(context: ContextTypes.DEFAULT_TYPE):
    ora = datetime.utcnow()

    for chat_id, asta in list(aste.items()):
        if asta["attiva"] and asta["scadenza"] and ora >= asta["scadenza"]:
            await context.bot.send_message(
                chat_id,
                f"🏁 ASTA TERMINATA!\n"
                f"💰 Prezzo finale: {asta['attuale']}€"
            )
            del aste[chat_id]


# ======================
# SHOP
# ======================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("🛒 Nessuna vendita attiva.")
        return

    testo = "🛒 Vendite attive:\n"
    for asta in aste.values():
        stato = "ATTIVA" if asta["attiva"] else "IN ATTESA"
        testo += f"- {asta['attuale']}€ ({stato})\n"

    await update.message.reply_text(testo)


# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, nuova_vendita))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, gestisci_offerta))

    # job ogni 60 secondi
    app.job_queue.run_repeating(controlla_scadenze, interval=60, first=60)

    app.run_polling()


if __name__ == "__main__":
    main()
