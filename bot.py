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

# ========= TOKEN =========
TOKEN = os.environ.get("TOKEN")
# oppure (non consigliato):
# TOKEN = "INSERISCI_TOKEN"

# ========= ASTE IN MEMORIA =========
aste = {}
asta_id_counter = 1

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aste attivo\n"
        "Formato vendita:\n"
        "#vendita nome prezzo\n"
        "Per offrire: rispondi al messaggio dell’asta"
    )

# ========= SHOP =========
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE:\n\n"
    for a in aste.values():
        testo += (
            f"#{a['id']} • {a['nome']}\n"
            f"Base: {a['base']}€ | Attuale: {a['attuale']}€\n\n"
        )
    await update.message.reply_text(testo)

# ========= TESTO ASTA =========
def render_asta(a):
    return (
        f"🆕 ASTA #{a['id']}\n"
        f"📦 {a['nome']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"💵 Offerta attuale: {a['attuale']}€\n"
        f"👤 Venditore: {a['venditore']}\n\n"
        f"✍️ Rispondi a QUESTO messaggio per offrire"
    )

# ========= VENDITA =========
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global asta_id_counter

    msg = update.message
    testo = msg.caption or msg.text
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    match = re.match(r"#vendita\s+(.+)\s+(\d+)", testo.lower())
    if not match:
        await msg.reply_text("❌ Usa: #vendita nome prezzo")
        return

    nome = match.group(1)
    base = int(match.group(2))

    asta = {
        "id": asta_id_counter,
        "nome": nome,
        "base": base,
        "attuale": base,
        "venditore": msg.from_user.full_name,
        "chat_id": msg.chat_id,
        "message_id": None,
        "tipo": "foto" if msg.photo else "testo",
    }
    asta_id_counter += 1

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = await msg.chat.send_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta,
        )
    else:
        sent = await msg.chat.send_message(testo_asta)

    asta["message_id"] = sent.message_id
    aste[asta["id"]] = asta

# ========= OFFERTE =========
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return

    testo = msg.text.replace("€", "").strip()
    if not testo.isdigit():
        return

    valore = int(testo)
    reply = msg.reply_to_message

    asta = None
    for a in aste.values():
        if a["message_id"] == reply.message_id and a["chat_id"] == msg.chat_id:
            asta = a
            break

    if not asta:
        return

    if valore <= asta["attuale"]:
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    if asta["tipo"] == "foto":
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

# ========= AVVIO =========
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("shop", shop))

# 👇 NIENTE REGEX QUI
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))
app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))

app.run_polling()
