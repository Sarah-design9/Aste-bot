import os
import re
import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

aste = {}  # message_id -> dati asta


# ------------------------
# START
# ------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! Per mettere in vendita scrivi:\n\n"
        "#vendita\n"
        "Titolo oggetto\n"
        "Base 10"
    )


# ------------------------
# SHOP
# ------------------------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("Non ci sono aste attive.")
        return

    testo = "Aste attive:\n\n"
    for asta in aste.values():
        testo += (
            f"{asta['titolo']}\n"
            f"Prezzo attuale: {asta['prezzo']}€\n\n"
        )

    await update.message.reply_text(testo)


# ------------------------
# NUOVA VENDITA
# ------------------------
async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    testo = message.text if message.text else message.caption
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    righe = testo.split("\n")
    if len(righe) < 3:
        return

    titolo = righe[1].strip()

    base_match = re.search(r"base\s*(\d+)", testo.lower())
    if not base_match:
        return

    base = int(base_match.group(1))

    aste[message.message_id] = {
        "titolo": titolo,
        "prezzo": base,
        "base": base,
        "attiva": True,
        "scadenza": None,
    }

    await message.reply_text(
        f"Asta creata!\n\n"
        f"{titolo}\n"
        f"Base d'asta: {base}€"
    )


# ------------------------
# OFFERTE
# ------------------------
async def offerte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.reply_to_message:
        return

    asta_id = message.reply_to_message.message_id

    if asta_id not in aste:
        return

    asta = aste[asta_id]

    if not asta["attiva"]:
        return

    testo = message.text.strip()

    match = re.match(r"(\d+)", testo)
    if not match:
        return

    offerta = int(match.group(1))

    prezzo_attuale = asta["prezzo"]

    # OFFERTA TROPPO BASSA
    if offerta < prezzo_attuale:
        await message.reply_text(
            f"Offerta troppo bassa. Prezzo attuale: {prezzo_attuale}€"
        )
        return

    # OFFERTA UGUALE
    if offerta == prezzo_attuale and prezzo_attuale != asta["base"]:
        await message.reply_text(
            f"Offerta troppo bassa. Prezzo attuale: {prezzo_attuale}€"
        )
        return

    # OFFERTA VALIDA
    asta["prezzo"] = offerta

    # Se è la prima offerta (uguale alla base)
    if asta["scadenza"] is None:
        asta["scadenza"] = datetime.now() + timedelta(hours=24)

    await message.reply_text(
        f"Nuova offerta valida!\n"
        f"Prezzo attuale: {offerta}€"
    )


# ------------------------
# MAIN
# ------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            nuova_vendita
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.REPLY,
            offerte
        )
    )

    print("Bot avviato...")
    app.run_polling()


if __name__ == "__main__":
    main()
