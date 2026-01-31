import logging
import re
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import os

# ===== CONFIG =====
TOKEN = os.environ.get("TOKEN")
logging.basicConfig(level=logging.INFO)

# ===== STORAGE =====
aste = {}
next_id = 1

# ===== UTILS =====
def render_asta(a):
    return (
        f"📦 {a['titolo']}\n"
        f"🆔 ID asta: {a['id']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"🟢 Stato: ATTIVA\n\n"
        f"👉 Rispondi a questo messaggio con un importo per offrire"
    )

# ===== VENDITA =====
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id

    msg = update.message
    if not msg:
        return

    testo = msg.caption if msg.photo else msg.text
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        await msg.reply_text("❌ Formato: #vendita nome prezzo")
        return

    titolo = " ".join(parti[1:-1])
    prezzo_raw = re.sub(r"[^\d]", "", parti[-1])

    if not prezzo_raw.isdigit():
        await msg.reply_text("❌ Prezzo non valido")
        return

    base = int(prezzo_raw)

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta
        )
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ===== OFFERTE =====
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text or not msg.reply_to_message:
        return

    # estrai numero
    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return

    valore = int(valore_raw)

    # trova asta
    asta = None
    for a in aste.values():
        if a["message_id"] == msg.reply_to_message.message_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    if valore <= asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    # aggiorna messaggio (caption o testo)
    try:
        await context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=nuovo_testo
        )
    except:
        await context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=nuovo_testo
        )

# ===== SHOP =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("🛒 Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in aste.values():
        testo += (
            f"#{a['id']} – {a['titolo']}\n"
            f"💰 {a['attuale']}€\n\n"
        )

    await update.message.reply_text(testo)

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))

    app.run_polling()

if __name__ == "__main__":
    main()
