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

# ---------------- CONFIG ----------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN mancante su Railway")

logging.basicConfig(level=logging.INFO)

# auctions[bot_message_id] = {...}
auctions = {}

# ---------------- UTILS ----------------
def parse_price(text: str):
    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else None


def auction_text(base, current, end):
    return (
        "🟢 **ASTA ATTIVA**\n\n"
        f"💰 **Base d'asta:** {base} €\n"
        f"📈 **Offerta attuale:** {current} €\n"
        f"⏰ **Fine asta:** {end.strftime('%d/%m/%Y %H:%M')}\n\n"
        "✍️ Rispondi a questo messaggio con il prezzo"
    )

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot aste attivo!\n\n"
        "Per vendere:\n"
        "• scrivi #vendita\n"
        "• inserisci la base d'asta\n"
        "• foto opzionale\n\n"
        "Le offerte devono essere risposte al post dell'asta."
    )


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auctions:
        await update.message.reply_text("❌ Nessuna asta attiva")
        return

    msg = "📦 **Aste attive:**\n\n"
    for a in auctions.values():
        msg += f"• {a['current']} € (base {a['base']} €)\n"

    await update.message.reply_text(msg)

# ---------------- VENDITA ----------------
async def handle_sale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.caption if msg.photo else msg.text

    if not text:
        return

    if "#vendita" not in text.lower():
        return

    base = parse_price(text)
    if base is None:
        await msg.reply_text("❌ Base d'asta non trovata")
        return

    end = datetime.now() + timedelta(hours=24)

    bot_msg = await msg.reply_text(
        auction_text(base, base, end),
        parse_mode="Markdown"
    )

    auctions[bot_msg.message_id] = {
        "chat_id": msg.chat_id,
        "base": base,
        "current": base,
        "end": end,
    }

    logging.info(f"Asta creata base {base}")

# ---------------- OFFERTE ----------------
async def handle_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message:
        return

    auction = auctions.get(msg.reply_to_message.message_id)
    if not auction:
        return

    bid = parse_price(msg.text or "")
    if bid is None:
        return

    if bid <= auction["current"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    auction["current"] = bid

    await context.bot.edit_message_text(
        chat_id=auction["chat_id"],
        message_id=msg.reply_to_message.message_id,
        text=auction_text(
            auction["base"],
            auction["current"],
            auction["end"]
        ),
        parse_mode="Markdown"
    )

    logging.info(f"Nuova offerta: {bid}")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.Caption) & filters.ChatType.GROUPS,
        handle_sale
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.ChatType.GROUPS,
        handle_bid
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
