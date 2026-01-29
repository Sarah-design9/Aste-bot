import logging
import re
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# ================== CONFIG ==================

TOKEN = "INSERISCI_IL_TUO_TOKEN"

ASTA_DURATA_ORE = 24
CANCELLAZIONE_POST_GIORNI = 3

# ================== STORAGE ==================

aste = {}        # id_asta -> dati
contatore_aste = 1

# ================== LOG ==================

logging.basicConfig(level=logging.INFO)

# ================== UTIL ==================

def parse_vendita(text):
    """
    #vendita oggetto prezzo
    """
    match = re.match(r"#vendita\s+(.+?)\s+(\d+)", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1), int(match.group(2))

def user_link(user):
    name = user.first_name or "Utente"
    return f"[{name}](tg://user?id={user.id})"

# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot aste attivo\n\n"
        "Per vendere:\n"
        "#vendita oggetto prezzo\n\n"
        "Comandi:\n"
        "/shop – vedi aste"
    )

# ================== CREAZIONE ASTA ==================

async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global contatore_aste

    message = update.message
    text = message.caption or message.text
    parsed = parse_vendita(text)

    if not parsed:
        return

    oggetto, prezzo_base = parsed
    id_asta = contatore_aste
    contatore_aste += 1

    fine_asta = datetime.utcnow() + timedelta(hours=ASTA_DURATA_ORE)

    aste[id_asta] = {
        "oggetto": oggetto,
        "prezzo": prezzo_base,
        "venditore": message.from_user,
        "vincitore": None,
        "fine": fine_asta,
        "messaggio_id": message.message_id,
        "chat_id": message.chat_id,
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Offri", callback_data=f"offri_{id_asta}")]
    ])

    await message.reply_text(
        f"📦 *ASTA #{id_asta}*\n"
        f"Oggetto: {oggetto}\n"
        f"Prezzo base: {prezzo_base}\n"
        f"Fine: {fine_asta.strftime('%d/%m %H:%M')} UTC\n"
        f"Venditore: {user_link(message.from_user)}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    context.application.create_task(
        chiudi_asta(id_asta, context)
    )
    context.application.create_task(
        cancella_post(message.chat_id, message.message_id, context)
    )

# ================== OFFERTE ==================

async def bottone_offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    id_asta = int(query.data.split("_")[1])
    asta = aste.get(id_asta)

    if not asta:
        await query.message.reply_text("❌ Asta non trovata")
        return

    if datetime.utcnow() > asta["fine"]:
        await query.message.reply_text("⏰ Asta chiusa")
        return

    asta["prezzo"] += 1
    asta["vincitore"] = query.from_user

    await query.message.reply_text(
        f"💸 Nuova offerta!\n"
        f"Prezzo: {asta['prezzo']}\n"
        f"Offerente: {user_link(query.from_user)}",
        parse_mode="Markdown"
    )

# ================== SHOP ==================

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    text = "🛒 *ASTE DISPONIBILI*\n\n"
    keyboard = []

    for id_asta, a in aste.items():
        stato = "🟢 Attiva" if datetime.utcnow() < a["fine"] else "🔴 Chiusa"
        text += (
            f"#{id_asta} – {a['oggetto']}\n"
            f"Prezzo: {a['prezzo']}\n"
            f"Stato: {stato}\n\n"
        )
        if stato == "🟢 Attiva":
            keyboard.append([
                InlineKeyboardButton(
                    f"Offri su #{id_asta}",
                    callback_data=f"offri_{id_asta}"
                )
            ])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ================== CHIUSURA ASTA ==================

async def chiudi_asta(id_asta, context):
    await asyncio.sleep(ASTA_DURATA_ORE * 3600)

    asta = aste.pop(id_asta, None)
    if not asta:
        return

    venditore = asta["venditore"]
    vincitore = asta["vincitore"]

    if vincitore:
        testo = (
            f"🏁 *ASTA CHIUSA*\n"
            f"Oggetto: {asta['oggetto']}\n"
            f"Prezzo finale: {asta['prezzo']}\n\n"
            f"Venditore: {user_link(venditore)}\n"
            f"Vincitore: {user_link(vincitore)}"
        )

        await context.bot.send_message(
            venditore.id,
            "✅ La tua asta è terminata!\n\n"
            f"Vincitore: {user_link(vincitore)}",
            parse_mode="Markdown"
        )

        await context.bot.send_message(
            vincitore.id,
            "🎉 Hai vinto un’asta!\n\n"
            f"Venditore: {user_link(venditore)}",
            parse_mode="Markdown"
        )
    else:
        testo = f"🏁 *ASTA #{id_asta} CHIUSA*\nNessuna offerta."

    await context.bot.send_message(
        asta["chat_id"],
        testo,
        parse_mode="Markdown"
    )

# ================== CANCELLAZIONE POST ==================

async def cancella_post(chat_id, message_id, context):
    await asyncio.sleep(CANCELLAZIONE_POST_GIORNI * 86400)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(
        CallbackQueryHandler(bottone_offerta, pattern="^offri_")
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            nuova_vendita
        )
    )

    app.run_polling()

if __name__ == "__main__":
    main()
