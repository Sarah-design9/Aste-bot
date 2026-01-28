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

# ====== STRUTTURA DATI ======
auctions = {}  # id -> dict
auction_id_counter = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aste attivo!\n\n"
        "Usa:\n"
        "#vendita Nome - Prezzo\n"
        "#offerta ID prezzo\n"
        "#chiudi ID\n"
        "/shop"
    )


# ====== GESTIONE MESSAGGI ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auction_id_counter

    text = update.message.text or update.message.caption or ""
    text = text.strip()
    user = update.message.from_user.first_name

    # -------- VENDITA --------
    if text.startswith("#vendita"):
        description = text[len("#vendita"):].strip()
        auction_id = auction_id_counter
        auction_id_counter += 1

        auctions[auction_id] = {
            "description": description,
            "price": 0,
            "winner": None,
            "active": True,
        }

        msg = (
            f"🆕 OGGETTO #{auction_id}\n"
            f"{description}\n\n"
            f"💰 Offerte aperte!\n"
            f"Scrivi: #offerta {auction_id} prezzo"
        )

        await update.message.reply_text(msg)

    # -------- OFFERTA --------
    elif text.startswith("#offerta"):
        parts = text.split()

        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Formato errato.\nUsa: #offerta ID prezzo"
            )
            return

        try:
            auction_id = int(parts[1])
            offer = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ ID o prezzo non valido.")
            return

        auction = auctions.get(auction_id)

        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Asta non trovata o chiusa.")
            return

        if offer <= auction["price"]:
    winner = auction["winner"] or "Nessuno"
    await update.message.reply_text(
        f"❌ OFFERTA RIFIUTATA\n\n"
        f"🆔 Oggetto #{auction_id}\n"
        f"💶 Offerta proposta: {offer}€\n"
        f"📈 Prezzo attuale: {auction['price']}€\n"
        f"👤 Miglior offerente: {winner}"
    )
    return

        auction["price"] = offer
        auction["winner"] = user

        await update.message.reply_text(
            f"🔥 NUOVA OFFERTA!\n"
            f"🆔 Oggetto #{auction_id}\n"
            f"👤 {user}\n"
            f"💶 {offer}€"
        )

    # -------- CHIUSURA --------
    elif text.startswith("#chiudi"):
        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text("❌ Usa: #chiudi ID")
            return

        try:
            auction_id = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ ID non valido.")
            return

        auction = auctions.get(auction_id)

        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Asta non trovata o già chiusa.")
            return

        auction["active"] = False

        if auction["winner"]:
            await update.message.reply_text(
                f"🏁 ASTA CHIUSA\n\n"
                f"🆔 Oggetto #{auction_id}\n"
                f"{auction['description']}\n"
                f"👤 Vincitore: {auction['winner']}\n"
                f"💶 Prezzo finale: {auction['price']}€"
            )
        else:
            await update.message.reply_text(
                f"🏁 ASTA CHIUSA\n\n"
                f"🆔 Oggetto #{auction_id}\n"
                f"{auction['description']}\n"
                f"❌ Nessuna offerta."
            )


# ====== SHOP ======
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active = [
        (aid, a)
        for aid, a in auctions.items()
        if a["active"]
    ]

    if not active:
        await update.message.reply_text("🛍️ Nessun oggetto in vendita.")
        return

    message = "🛍️ OGGETTI IN VENDITA\n\n"

    for aid, a in active:
        price = a["price"] if a["price"] > 0 else "Nessuna offerta"
        message += f"🆔 #{aid} — {a['description']}\n💶 {price}\n\n"

    message += "📌 Per offrire:\n#offerta ID prezzo"

    await update.message.reply_text(message)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
