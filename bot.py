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

# ===== MEMORIA ASTE (per ora in RAM) =====
aste = {}
asta_id_counter = 1

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot aste attivo e funzionante!")

# ===== SHOP =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE DISPONIBILI:\n\n"
    for aid, a in aste.items():
        stato = "🟢 ATTIVA" if a["attiva"] else "🟡 IN ATTESA"
        testo += (
            f"ID {aid} | {stato}\n"
            f"📦 {a['nome']}\n"
            f"💰 Prezzo: {a['prezzo']}€\n\n"
        )

    await update.message.reply_text(testo)

# ===== VENDITA =====
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
        "venditore": msg.from_user.id,
        "venditore_nome": msg.from_user.full_name,
        "miglior_offerente": None,
        "attiva": False,
        "message_id": None,
        "chat_id": msg.chat_id,
        "creata": time.time(),
    }

    testo_asta = (
        f"🆕 ASTA #{asta_id}\n"
        f"📦 {nome}\n"
        f"💰 Prezzo base: {prezzo}€\n"
        f"👤 Venditore: {msg.from_user.full_name}\n\n"
        f"💬 Rispondi a QUESTO messaggio per offrire"
    )

    if msg.photo:
        sent = await msg.chat.send_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta,
        )
    else:
        sent = await msg.chat.send_message(testo_asta)

    aste[asta_id]["message_id"] = sent.message_id

# ===== OFFERTE =====
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return

    testo = msg.text.replace("€", "").strip()
    if not testo.isdigit():
        return

    offerta = int(testo)
    reply = msg.reply_to_message

    # trova asta collegata al messaggio del bot
    asta = None
    for a in aste.values():
        if (
            a["message_id"] == reply.message_id
            and a["chat_id"] == msg.chat_id
        ):
            asta = a
            break

    if not asta:
        return

    if offerta <= asta["prezzo"]:
        return

    asta["prezzo"] = offerta
    asta["miglior_offerente"] = msg.from_user.full_name
    asta["attiva"] = True

    testo_aggiornato = (
        f"🆕 ASTA\n"
        f"📦 {asta['nome']}\n"
        f"💰 Prezzo attuale: {asta['prezzo']}€\n"
        f"👤 Miglior offerente: {asta['miglior_offerente']}\n\n"
        f"💬 Rispondi a QUESTO messaggio per offrire"
    )

    try:
        if reply.photo:
            await context.bot.edit_message_caption(
                chat_id=msg.chat_id,
                message_id=reply.message_id,
                caption=testo_aggiornato,
            )
        else:
            await context.bot.edit_message_text(
                chat_id=msg.chat_id,
                message_id=reply.message_id,
                text=testo_aggiornato,
            )
    except:
        pass

# ===== AVVIO BOT =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("shop", shop))
app.add_handler(MessageHandler(filters.Regex(r"^#vendita"), vendita))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, offerta))

app.run_polling()
