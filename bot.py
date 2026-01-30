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

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"

logging.basicConfig(level=logging.INFO)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo e funzionante")


# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    testo = msg.caption if msg.photo else msg.text
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        await msg.reply_text("❌ Usa: #vendita nome prezzo")
        return

    titolo = " ".join(parti[1:-1])
    prezzo = re.sub(r"[^\d]", "", parti[-1])
    if not prezzo:
        await msg.reply_text("❌ Prezzo non valido")
        return

    risposta = (
        f"📦 {titolo}\n"
        f"💰 Base d’asta: {prezzo}€\n\n"
        f"✅ Asta creata correttamente"
    )

    if msg.photo:
        await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=risposta,
        )
    else:
        await msg.reply_text(risposta)


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))

    app.run_polling()


if __name__ == "__main__":
    main()
