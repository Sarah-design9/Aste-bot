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
# In alternativa (non consigliato):
# TOKEN = "INSERISCI_TOKEN"

# ========= MEMORIA ASTE =========
aste = {}
asta_id_counter = 1

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aste attivo!\n"
        "Usa:\n"
        "#vendita nome prezzo\n"
        "Offerte: rispondi al messaggio dell’asta"
    )

# ========= SHOP =========
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("📭 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE:\n\n"
    for aid, a in aste.items():
        testo += (
            f"#{aid} • {a['nome']}\n"
            f"Base: {a['prezzo_base']}€ | Attuale: {a['prezzo_attuale']}€\n\n"
        )
    await update.message.reply_text(testo)

# ========= TESTO ASTA =========
def testo_asta(a):
    return (
        f"🆕 ASTA #{a['id']}\n"
        f"📦 {a['nome']}\n"
        f"💰 Base d’asta: {a['prezzo_base']}€\n"
        f"💵 Offerta attuale: {a['prezzo_attuale']}€\n"
        f"👤 Venditore: {a['venditore']}\n\n"
        f"✍️ Rispondi a QUESTO messaggio per offrire"
    )

# ========= VENDITA =========
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global asta_id_counter

    msg = update.message
    testo = msg.caption or msg.text
    if not testo or not testo.lower().startswith("#vendita"):
        return

    match = re.match(r"#vendita\s+(.+)\s+(\d+)", testo.lower())
    if not match:
        await msg.reply_text("❌ Usa: #vendita nome prezzo")
        return

    nome = match.group(1)
    prezzo_base = int(match.group(2))

    asta = {
        "id": asta_id_counter,
        "nome": nome,
        "prezzo_base": prezzo_base,
        "prezzo_attuale": prezzo_base,
        "venditore": msg.from_user.full_name,
        "chat_id": msg.chat_id,
        "message_id": None,
        "con_foto": bool(msg.photo),
    }
    asta_id_counter += 1

    testo_msg = testo_asta(asta)

    if msg.photo:
        sent = await msg.chat.send_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_msg,
        )
    else:
        sent = await msg.chat.send_message(testo_msg)

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

    offerta = int(testo)
    reply = msg.reply_to_message

    asta = None
    for a in aste.values():
        if a["message_id"] == reply.message_id and a["chat_id"] == msg.chat_id:
            asta = a
            break

    if not asta:
        return

    if offerta <= asta["prezzo_attuale"]:
        return

    asta["prezzo_attuale"] = offerta
    nuovo_testo = testo_asta(asta)

    # ✅ LOGICA CORRETTA FOTO / TESTO
    if asta["con_foto"]:
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

app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO) & filters.Regex(r"^#vendita"),
        vendita,
    )
)

app.add_handler(
    MessageHandler(filters.TEXT & filters.REPLY, offerta)
)

app.run_polling()
