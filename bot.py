from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
import os
import re
import time

TOKEN = os.environ.get("TOKEN")

aste = {}
asta_id_counter = 1

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot aste attivo!")

# ---------- SHOP ----------
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE:\n\n"
    for aid, a in aste.items():
        testo += f"#{aid} • {a['nome']} • {a['prezzo']}€\n"
    await update.message.reply_text(testo)

# ---------- VENDITA ----------
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global asta_id_counter

    msg = update.message
    testo = msg.caption if msg.caption else msg.text
    if not testo:
        return

    match = re.match(r"#vendita\s+(.+)\s+(\d+)", testo.lower())
    if not match:
        return

    nome = match.group(1)
    prezzo = int(match.group(2))

    asta_id = asta_id_counter
    asta_id_counter += 1

    aste[asta_id] = {
        "nome": nome,
        "prezzo": prezzo,
        "venditore": msg.from_user.full_name,
        "message_id": None,
        "chat_id": msg.chat_id,
    }

    testo_asta = (
        f"🆕 ASTA #{asta_id}\n"
        f"📦 {nome}\n"
        f"💰 Prezzo: {prezzo}€\n"
        f"👤 Venditore: {msg.from_user.full_name}\n\n"
        f"✍️ Rispondi a QUESTO messaggio per offrire"
    )

    if msg.photo:
        sent = await msg.chat.send_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta,
        )
    else:
        sent = await msg.chat.send_message(testo_asta)

    aste[asta_id]["message_id"] = sent.message_id

# ---------- OFFERTE ----------
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return

    testo = msg.text.replace("€", "").strip()
    if not testo.isdigit():
        return

    offerta = int(testo)
    reply = msg.reply_to_message

    asta = None
    for a in aste.values():
        if a["message_id"] == reply.message_id:
            asta = a
            break

    if not asta:
        return

    if offerta <= asta["prezzo"]:
        return

    asta["prezzo"] = offerta

    nuovo_testo = (
        f"🆕 ASTA\n"
        f"📦 {asta['nome']}\n"
        f"💰 Prezzo attuale: {asta['prezzo']}€\n\n"
        f"✍️ Rispondi a QUESTO messaggio per offrire"
    )

    if reply.photo:
        await context.bot.edit_message_caption(
            chat_id=msg.chat_id,
            message_id=reply.message_id,
            caption=nuovo_testo,
        )
    else:
        await context.bot.edit_message_text(
            chat_id=msg.chat_id,
            message_id=reply.message_id,
            text=nuovo_testo,
        )

# ---------- AVVIO ----------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("shop", shop))

# 🔥 QUESTO È IL PEZZO CHIAVE
app.add_handler(MessageHandler(
    filters.TEXT | filters.PHOTO,
    vendita
))

app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    offerta
))

app.run_polling()
