import os
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.environ.get("TOKEN")

auctions = {}
auction_counter = 1

# ---------- UTIL ----------
def user_link(user):
    if user.username:
        return f"@{user.username}"
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot aste attivo e funzionante!")

# ---------- SHOP ----------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not auctions:
        await update.message.reply_text("🛒 Nessun oggetto in vendita.")
        return

    text = "🛍️ <b>SHOP</b>\n\n"
    for aid, a in auctions.items():
        stato = "🛒 In vendita"
        prezzo = a["base_price"]

        if a["active"]:
            stato = "⚡ Asta attiva"
            prezzo = a["current_price"]

        text += (
            f"<b>{aid}</b> – {a['description']}\n"
            f"{stato}\n"
            f"Prezzo: {prezzo}€\n\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")

# ---------- VENDITA ----------
async def process_sale(msg, context: ContextTypes.DEFAULT_TYPE):
    global auction_counter

    text = msg.text or msg.caption
    if not text or not text.lower().startswith("#vendita"):
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.reply_text("❌ Usa: #vendita DESCRIZIONE PREZZO_BASE")
        return

    description = parts[1]

    try:
        base_price = int(parts[2])
    except ValueError:
        await msg.reply_text("❌ Il prezzo base deve essere un numero.")
        return

    aid = f"A{auction_counter}"
    auction_counter += 1

    auctions[aid] = {
        "id": aid,
        "description": description,
        "base_price": base_price,
        "current_price": base_price,
        "seller": msg.from_user,
        "winner": None,
        "active": False,
        "end_time": None,
        "chat_id": msg.chat_id,
    }

    caption = (
        f"🛒 <b>OGGETTO IN VENDITA</b>\n"
        f"ID: <b>{aid}</b>\n"
        f"{description}\n"
        f"Prezzo base: {base_price}€\n\n"
        f"👉 Prima offerta valida avvia l’asta"
    )

    # invio messaggio e salvo message_id
    if msg.photo:
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )
    else:
        sent = await msg.reply_text(caption, parse_mode="HTML")

    # pianifico cancellazione dopo 3 giorni
    asyncio.create_task(delete_message_later(
        context,
        sent.chat_id,
        sent.message_id,
        delay_hours=72
    ))

# ---------- CANCELLAZIONE POST ----------
async def delete_message_later(context, chat_id, message_id, delay_hours):
    await asyncio.sleep(delay_hours * 3600)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass  # se già cancellato o permessi mancanti

# ---------- HANDLER TESTO ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_sale(update.message, context)

# ---------- HANDLER FOTO ----------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_sale(update.message, context)

# ---------- OFFERTA ----------
async def handle_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    parts = msg.text.split()

    if len(parts) != 3:
        await msg.reply_text("❌ Usa: #offerta ID PREZZO")
        return

    aid = parts[1]

    try:
        price = int(parts[2])
    except ValueError:
        await msg.reply_text("❌ Il prezzo deve essere un numero.")
        return

    if aid not in auctions:
        await msg.reply_text("❌ Asta inesistente.")
        return

    auction = auctions[aid]

    if not auction["active"]:
        if price < auction["base_price"]:
            await msg.reply_text("❌ Offerta sotto il prezzo base.")
            return

        auction["active"] = True
        auction["current_price"] = price
        auction["winner"] = msg.from_user
        auction["end_time"] = datetime.utcnow() + timedelta(hours=24)

        await msg.reply_text(
            f"⚡ <b>ASTA AVVIATA</b>\n"
            f"ID: {aid}\n"
            f"Offerta iniziale: {price}€\n"
            f"Da: {user_link(msg.from_user)}",
            parse_mode="HTML"
        )

        asyncio.create_task(close_auction_later(context, aid))
        return

    if datetime.utcnow() > auction["end_time"]:
        await msg.reply_text("⛔ Asta chiusa.")
        return

    if price <= auction["current_price"]:
        await msg.reply_text("❌ Offerta troppo bassa.")
        return

    old = auction["winner"]
    auction["current_price"] = price
    auction["winner"] = msg.from_user

    try:
        await context.bot.send_message(
            old.id,
            f"⚠️ La tua offerta per {aid} è stata superata."
        )
    except:
        pass

    await msg.reply_text(
        f"✅ Nuova offerta: {price}€ da {user_link(msg.from_user)}",
        parse_mode="HTML"
    )

# ---------- CHIUSURA ASTA ----------
async def close_auction_later(context, aid):
    auction = auctions[aid]
    wait = (auction["end_time"] - datetime.utcnow()).total_seconds()
    await asyncio.sleep(max(wait, 0))

    if not auction["active"]:
        return

    auction["active"] = False
    winner = auction["winner"]
    seller = auction["seller"]

    await context.bot.send_message(
        auction["chat_id"],
        (
            f"🏁 <b>ASTA CHIUSA</b>\n"
            f"ID: {aid}\n"
            f"Vincitore: {user_link(winner)}\n"
            f"Prezzo: {auction['current_price']}€"
        ),
        parse_mode="HTML"
    )

    await context.bot.send_message(
        winner.id,
        f"🎉 Hai vinto l’asta {aid}\nVenditore: {user_link(seller)}",
        parse_mode="HTML"
    )

    await context.bot.send_message(
        seller.id,
        f"✅ Asta {aid} conclusa\nVincitore: {user_link(winner)}",
        parse_mode="HTML"
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^#offerta"), handle_offer))

    app.run_polling()

if __name__ == "__main__":
    main()
