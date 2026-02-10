import logging
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ================= CONFIG =================
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTILS =================
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    if a["fine"] is None:
        fine_text = "⏳ Parte alla prima offerta"
    else:
        fine_text = a["fine"].strftime("%d/%m %H:%M")

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine_text}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a QUESTO messaggio con un importo"
    )

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message

    testo = msg.caption if msg.photo else msg.text
    if not testo:
        return

    if not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    titolo = " ".join(parti[1:-1])
    base_raw = re.sub(r"[^\d]", "", parti[-1])
    if not base_raw.isdigit():
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
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta
        )
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ================= OFFERTE =================
async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    # deve essere una risposta
    if not msg.reply_to_message:
        return

    # deve essere numero
    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return

    valore = int(valore_raw)

    # trova asta
    asta = None
    for a in aste.values():
        if (
            a["attiva"]
            and a["chat_id"] == msg.chat_id
            and a["message_id"] == msg.reply_to_message.message_id
        ):
            asta = a
            break

    if not asta:
        return

    # prima offerta → parte timer
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    # asta scaduta
    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        return

    # offerta troppo bassa
    if valore <= asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

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

# ================= SHOP =================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attive = [a for a in aste.values() if a["attiva"]]

    if not attive:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for a in attive:
        testo += f"#{a['id']} – {a['titolo']} | 💰 {a['attuale']}€\n"

    await update.message.reply_text(testo)

# ================= MAIN =================
def main():
    import os
    TOKEN = os.environ.get("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))

    # VENDITE
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))

    # OFFERTE (TUTTI i messaggi)
    app.add_handler(MessageHandler(filters.TEXT, gestisci_messaggi))

    app.run_polling()

if __name__ == "__main__":
    main()
