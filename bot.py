import os
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")

aste = {}
contatore_id = 1


# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! Per mettere in vendita un oggetto scrivi un post con FOTO e nel testo metti:\n\n"
        "Vendita nomeoggetto\n"
        "Base d'asta: 10€"
    )


# =========================
# /shop
# =========================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("Non ci sono aste attive.")
        return

    testo = "📦 Aste attive:\n\n"
    for id_asta, dati in aste.items():
        testo += (
            f"ID: {id_asta}\n"
            f"Oggetto: {dati['titolo']}\n"
            f"Prezzo attuale: {dati['prezzo']}€\n\n"
        )

    await update.message.reply_text(testo)


# =========================
# NUOVA ASTA (parser intelligente)
# =========================
async def nuova_asta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contatore_id

    if not update.message.photo:
        return

    testo = update.message.caption
    if not testo:
        return

    testo_lower = testo.lower()

    if "vendita" not in testo_lower:
        return

    # Trova prezzo con regex (prende qualsiasi numero con o senza €)
    match = re.search(r"(\d+)\s*€?", testo)
    if not match:
        await update.message.reply_text("Non trovo il prezzo base.")
        return

    prezzo_base = float(match.group(1))

    # Titolo = riga che contiene vendita
    righe = testo.split("\n")
    titolo = ""
    for r in righe:
        if "vendita" in r.lower():
            titolo = r.lower().replace("vendita", "").strip()
            break

    if not titolo:
        titolo = "Oggetto"

    aste[contatore_id] = {
        "titolo": titolo,
        "prezzo": prezzo_base,
        "gruppo": update.effective_chat.id,
    }

    await update.message.reply_text(
        f"✅ Asta creata!\n\nID: {contatore_id}\n"
        f"Oggetto: {titolo}\n"
        f"Base d'asta: {prezzo_base}€"
    )

    contatore_id += 1


# =========================
# OFFERTE
# =========================
async def offerte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        return

    testo = update.message.text

    match = re.search(r"(\d+)\s*€?", testo)
    if not match:
        return

    offerta = float(match.group(1))

    if not aste:
        return

    # prende ultima asta
    ultimo_id = list(aste.keys())[-1]
    asta = aste[ultimo_id]

    if offerta >= asta["prezzo"]:
        asta["prezzo"] = offerta
        await update.message.reply_text(
            f"🔥 Nuova offerta valida: {offerta}€"
        )


# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(MessageHandler(filters.PHOTO, nuova_asta))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, offerte))

    print("Bot avviato...")
    app.run_polling()


if __name__ == "__main__":
    main()
