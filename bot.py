from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

TOKEN = os.environ.get("TOKEN")

# Stato semplice dell'asta (solo per test)
current_item = None
current_price = 0
current_winner = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo e funzionante!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_item, current_price, current_winner

    # Testo del messaggio o didascalia della foto
    text = update.message.text or update.message.caption or ""
    text = text.strip()

    username = update.message.from_user.first_name

    # --- VENDITA ---
    if text.startswith("#vendita"):
        description = text[len("#vendita"):].strip()

        current_item = description
        current_price = 0
        current_winner = None

        if update.message.photo:
            await update.message.reply_text(
                f"📸 OGGETTO IN VENDITA (con foto)\n"
                f"{description}\n\n"
                f"💰 Offerte aperte!"
            )
        else:
            await update.message.reply_text(
                f"🛒 OGGETTO IN VENDITA\n"
                f"{description}\n\n"
                f"💰 Offerte aperte!"
            )

    # --- OFFERTA ---
    elif text.startswith("#offerta"):
        if current_item is None:
            await update.message.reply_text("❌ Nessuna asta attiva.")
            return

        try:
            offer = int(text[len("#offerta"):].strip())
        except ValueError:
            await update.message.reply_text("❌ Offerta non valida. Usa: #offerta 50")
            return

        if offer <= current_price:
            await update.message.reply_text(
                f"❌ Offerta troppo bassa. Prezzo attuale: {current_price}€"
            )
            return

        current_price = offer
        current_winner = username

        await update.message.reply_text(
            f"🔥 NUOVA OFFERTA!\n"
            f"👤 {username}\n"
            f"💶 {offer}€"
        )

    # --- CHIUSURA ASTA ---
    elif text.startswith("#chiudi"):
        if current_item is None:
            await update.message.reply_text("❌ Nessuna asta da chiudere.")
            return

        if current_winner:
            await update.message.reply_text(
                f"🏁 ASTA CHIUSA!\n\n"
                f"🛒 Oggetto: {current_item}\n"
                f"👤 Vincitore: {current_winner}\n"
                f"💶 Prezzo finale: {current_price}€"
            )
        else:
            await update.message.reply_text(
                f"🏁 ASTA CHIUSA!\n\n"
                f"🛒 Oggetto: {current_item}\n"
                f"❌ Nessuna offerta ricevuta."
            )

        current_item = None
        current_price = 0
        current_winner = None


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
