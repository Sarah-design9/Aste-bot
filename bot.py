import logging
import os
import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTILS =================
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 ASTA TERMINATA"
    fine = a["fine"].strftime("%d/%m %H:%M") if a["fine"] else "⏳ In attesa di offerte"

    testo = (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}"
    )

    if not a["attiva"]:
        testo += f"\n\n🏆 Vincitore: {a['vincitore']}\n💵 Prezzo finale: {a['attuale']}€"
    else:
        testo += "\n\n👉 Rispondi a questo messaggio con un importo per offrire"

    return testo


async def aggiorna_post(context: ContextTypes.DEFAULT_TYPE, asta):
    try:
        await context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=render_asta(asta)
        )
    except:
        await context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=render_asta(asta)
        )

# ================= CHIUSURA ASTA =================
async def chiudi_asta(context: ContextTypes.DEFAULT_TYPE):
    asta_id = context.job.data
    asta = aste.get(asta_id)

    if not asta or not asta["attiva"]:
        return

    asta["attiva"] = False
    await aggiorna_post(context, asta)

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message
    testo = msg.caption if msg.photo else msg.text

    if not testo or not testo.lower().startswith("#vendita"):
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
        "venditore": msg.from_user.id,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,
        "vincitore": None,
    }

    try:
        if msg.photo:
            sent = await msg.reply_photo(
                photo=msg.photo[-1].file_id,
                caption=render_asta(asta)
            )
        else:
            sent = await msg.reply_text(render_asta(asta))
    except Exception as e:
        logging.error(e)
        return

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

    asta = None
    for a in aste.values():
        if a["message_id"] == msg.reply_to_message.message_id:
            asta = a
            break

    if not asta or not asta["attiva"]:
        return

    # prima offerta → parte il countdown
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)
        context.job_queue.run_once(
            chiudi_asta,
            when=DURATA_ASTA_ORE * 3600,
            data=asta["id"]
        )

    if valore < asta["base"]:
        return

    if valore < asta["attuale"]:
        return

    asta["attuale"] = valore
    asta["vincitore"] = msg.from_user.first_name

    await aggiorna_post(context, asta)

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
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))

    app.run_polling()

if __name__ == "__main__":
    main()
