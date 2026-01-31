import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import os

# ===== CONFIG =====
TOKEN = os.environ.get("TOKEN")  # usa variabile Railway
logging.basicConfig(level=logging.INFO)

# ===== STORAGE =====
aste = {}
next_id = 1

# ===== UTILS =====
def render_asta(a):
    return (
        f"📦 {a['titolo']}\n"
        f"🆔 ID asta: {a['id']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"🟢 Stato: IN ATTESA DI OFFERTE\n\n"
        f"👉 Per offrire rispondi a QUESTO messaggio (step 2)"
    )

# ===== VENDITA =====
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id

    msg = update.message
    if not msg:
        return

    testo = msg.caption if msg.photo else msg.text
    if not testo:
        return

    testo = testo.strip()
    if not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        await msg.reply_text("❌ Formato corretto: #vendita nomeoggetto prezzo")
        return

    titolo = " ".join(parti[1:-1])
    prezzo_raw = re.sub(r"[^\d]", "", parti[-1])

    if not prezzo_raw.isdigit():
        await msg.reply_text("❌ Prezzo non valido")
        return

    base = int(prezzo_raw)

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "chat_id": msg.chat_id,
        "message_id": None,
    }

    testo_asta = render_asta(asta)

    try:
        if msg.photo:
            sent = await msg.reply_photo(
                photo=msg.photo[-1].file_id,
                caption=testo_asta
            )
        else:
            sent = await msg.reply_text(testo_asta)
    except Exception as e:
        logging.error(f"Errore invio asta: {e}")
        return

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ===== SHOP =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("🛒 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE DISPONIBILI\n\n"
    for a in aste.values():
        testo += (
            f"#{a['id']} – {a['titolo']}\n"
            f"💰 {a['attuale']}€\n\n"
        )

    await update.message.reply_text(testo)

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))

    app.run_polling()

if __name__ == "__main__":
    main()
