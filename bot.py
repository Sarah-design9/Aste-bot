import logging
import re
import os
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


# ================= UTIL =================
def render_asta(a):
    fine = "⏳ Parte alla prima offerta" if a["fine"] is None else a["fine"].strftime("%d/%m %H:%M")
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine asta: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a QUESTO messaggio con un importo"
    )


# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    testo = msg.caption if msg.photo else msg.text

    if not testo or not testo.lower().startswith("#vendita"):
        return

    global next_id

    parti = testo.split()
    if len(parti) < 3:
        await msg.reply_text("❌ Usa: #vendita NomeOggetto prezzo")
        return

    titolo = " ".join(parti[1:-1])
    base_raw = re.sub(r"[^\d]", "", parti[-1])

    if not base_raw.isdigit():
        await msg.reply_text("❌ Prezzo non valido")
        return

    base = int(base_raw)

    asta = {
        "id": next_id,
        "titolo": titolo,
        "base": base,
        "attuale": base,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = await msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1


# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message or not msg.text:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return

    valore = int(valore_raw)
    reply_id = msg.reply_to_message.message_id

    asta = next((a for a in aste.values() if a["message_id"] == reply_id and a["attiva"]), None)
    if not asta:
        return

    if asta["fine"] is None:
        if valore < asta["base"]:
            await msg.reply_text("❌ Offerta troppo bassa")
            return
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        await msg.reply_text("⏰ Asta terminata")
        return

    if valore <= asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    try:
        await context.bot.edit_message_caption(asta["chat_id"], asta["message_id"], caption=nuovo_testo)
    except:
        await context.bot.edit_message_text(asta["chat_id"], asta["message_id"], nuovo_testo)


# ================= SHOP =================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attive = [a for a in aste.values() if a["attiva"]]

    if not attive:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in attive:
        testo += f"{a['titolo']} – {a['attuale']}€\n"

    await update.message.reply_text(testo)


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # ORDINE CORRETTO (FONDAMENTALE)
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, offerta))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, vendita))

    app.run_polling()


if __name__ == "__main__":
    main()
