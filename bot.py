import logging
import re
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"
DATA_FILE = "data.json"

ASTA_DURATA_ORE = 24
CANCELLAZIONE_POST_GIORNI = 3

# ================= STORAGE =================

def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"contatore": 1, "aste": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ================= LOG =================

logging.basicConfig(level=logging.INFO)

# ================= UTILS =================

def parse_vendita(text):
    match = re.match(r"#vendita\s+(.+?)\s+(\d+)", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1), int(match.group(2))

def user_link(user):
    name = user.first_name or "Utente"
    return f"[{name}](tg://user?id={user.id})"

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot aste attivo\n\n"
        "Usa:\n"
        "#vendita oggetto prezzo\n"
        "/shop – vedi aste"
    )

# ================= NUOVA ASTA =================

async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.caption or message.text
    parsed = parse_vendita(text)

    if not parsed:
        return

    oggetto, prezzo = parsed

    id_asta = str(data["contatore"])
    data["contatore"] += 1

    fine = (datetime.utcnow() + timedelta(hours=ASTA_DURATA_ORE)).isoformat()

    data["aste"][id_asta] = {
        "oggetto": oggetto,
        "prezzo": prezzo,
        "venditore_id": message.from_user.id,
        "venditore_nome": message.from_user.first_name,
        "vincitore_id": None,
        "fine": fine,
        "chat_id": message.chat_id,
    }

    save_data()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Offri", callback_data=f"offri_{id_asta}")]
    ])

    await message.reply_text(
        f"📦 *ASTA #{id_asta}*\n"
        f"Oggetto: {oggetto}\n"
        f"Prezzo base: {prezzo}\n"
        f"Venditore: {user_link(message.from_user)}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    context.application.create_task(chiudi_asta(id_asta, context))
    context.application.create_task(
        cancella_post(message.chat_id, message.message_id, context)
    )

# ================= OFFERTE =================

async def bottone_offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    id_asta = query.data.split("_")[1]
    asta = data["aste"].get(id_asta)

    if not asta:
        await query.message.reply_text("❌ Asta non trovata")
        return

    if datetime.utcnow() > datetime.fromisoformat(asta["fine"]):
        await query.message.reply_text("⏰ Asta chiusa")
        return

    asta["prezzo"] += 1
    asta["vincitore_id"] = query.from_user.id
    save_data()

    await query.message.reply_text(
        f"💸 Nuova offerta!\n"
        f"Prezzo: {asta['prezzo']}\n"
        f"Offerente: {user_link(query.from_user)}",
        parse_mode="Markdown"
    )

# ================= SHOP =================

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["aste"]:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    text = "🛒 *ASTE*\n\n"
    keyboard = []

    for id_asta, a in data["aste"].items():
        attiva = datetime.utcnow() < datetime.fromisoformat(a["fine"])
        stato = "🟢 Attiva" if attiva else "🔴 Chiusa"

        text += (
            f"#{id_asta} – {a['oggetto']}\n"
            f"Prezzo: {a['prezzo']}\n"
            f"Stato: {stato}\n\n"
        )

        if attiva:
            keyboard.append([
                InlineKeyboardButton(
                    f"Offri su #{id_asta}",
                    callback_data=f"offri_{id_asta}"
                )
            ])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= CHIUSURA ASTA =================

async def chiudi_asta(id_asta, context):
    await asyncio.sleep(ASTA_DURATA_ORE * 3600)

    asta = data["aste"].pop(id_asta, None)
    if not asta:
        return

    save_data()

    venditore_id = asta["venditore_id"]
    vincitore_id = asta["vincitore_id"]

    if vincitore_id:
        await context.bot.send_message(
            venditore_id,
            f"✅ Asta chiusa!\nVincitore: [clicca](tg://user?id={vincitore_id})",
            parse_mode="Markdown"
        )

        await context.bot.send_message(
            vincitore_id,
            f"🎉 Hai vinto!\nVenditore: [clicca](tg://user?id={venditore_id})",
            parse_mode="Markdown"
        )

# ================= CANCEL POST =================

async def cancella_post(chat_id, message_id, context):
    await asyncio.sleep(CANCELLAZIONE_POST_GIORNI * 86400)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CallbackQueryHandler(bottone_offerta, pattern="^offri_"))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, nuova_vendita))

    app.run_polling()

if __name__ == "__main__":
    main()
