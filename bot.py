import os
import logging
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN non trovato nelle variabili d'ambiente")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------- DATA ----------------
# auctions[message_id] = {
#   chat_id, base_price, current_price,
#   end_time, bot_message_id
# }
auctions = {}

# ---------------- HELPERS ----------------
def parse_price(text: str):
    """
    Accetta:
    10
    10€
    10 €
    """
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def build_auction_text(base, current, end_time):
    return (
        "🟢 **ASTA ATTIVA**\n\n"
        f"💰 **Base d'asta:** {base} €\n"
        f"📈 **Offerta attuale:** {current} €\n"
        f"⏰ **Fine asta:** {end_time.strftime('%d/%m/%Y %H:%M')}\n\n"
        "✍️ Scrivi solo il numero per fare un'offerta"
    )


# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ciao!\n\n"
        "Per mettere in vendita un oggetto:\n"
        "• Scrivi `#vendita`\n"
        "• Aggiungi una foto (opzionale)\n"
        "• Scrivi nel testo la **base d'asta**\n\n"
        "Gli utenti devono rispondere al post con il prezzo."
    )


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auctions:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    text = "📦 **Aste attive:**\n\n"
    for a in auctions.values():
        text += f"• Base {a['base_price']} € | Attuale {a['current_price']} €\n"

    await update.message.reply_text(text)


# ---------------- VENDITA ----------------
async def handle_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.caption if message.photo else message.text

    if not text or "#vendita" not in text.lower():
        return

    base_price = parse_price(text)
    if base_price is None:
        await message.reply_text("❌ Base d'asta non trovata")
        return

    end_time = datetime.now() + timedelta(hours=24)

    auction_text = build_auction_text(base_price, base_price, end_time)

    bot_msg = await message.reply_text(
        auction_text,
        parse_mode="Markdown",
    )

    auctions[message.message_id] = {
        "chat_id": message.chat_id,
        "base_price": base_price,
        "current_price": base_price,
        "end_time": end_time,
        "bot_message_id": bot_msg.message_id,
    }

    logging.info(f"Asta creata - base {base_price}€")


# ---------------- OFFERTE ----------------
async def handle_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.reply_to_message:
        return

    auction = auctions.get(message.reply_to_message.message_id)
    if not auction:
        return

    bid = parse_price(message.text)
    if bid is None:
        return

    current = auction["current_price"]

    if bid <= current:
        await message.reply_text("❌ Offerta troppo bassa")
        return

    auction["current_price"] = bid

    new_text = build_auction_text(
        auction["base_price"],
        auction["current_price"],
        auction["end_time"],
    )

    await context.bot.edit_message_text(
        chat_id=auction["chat_id"],
        message_id=auction["bot_message_id"],
        text=new_text,
        parse_mode="Markdown",
    )

    logging.info(f"Nuova offerta valida: {bid}€")


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_sale)
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.REPLY & filters.ChatType.GROUPS, handle_bid)
    )

    logging.info("Bot avviato correttamente")
    app.run_polling()


if __name__ == "__main__":
    main()
