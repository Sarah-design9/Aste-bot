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
CHECK_INTERVAL = 60  # secondi

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= RENDER =================
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 ASTA TERMINATA"
    fine = a["fine"].strftime("%d/%m %H:%M") if a["fine"] else "⏳ Parte alla prima offerta"

    testo = (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine asta: {fine}\n"
        f"{stato}"
    )

    if not a["attiva"]:
        testo += f"\n\n🏆 Vincitore: {a['vincitore']}\n💵 Prezzo finale: {a['attuale']}€"
    else:
        testo += "\n\n👉 Rispondi con un importo per offrire"

    return testo


async def aggiorna_post(context, asta):
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

# ================= CONTROLLO ASTE =================
async def controllo_aste(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()

    for asta in aste.values():
        if asta["attiva"] and asta["fine"] and now >= asta["fine"]:
            asta["attiva"] = False

            await aggiorna_post(context, asta)

            await context.bot.send_message(
                chat_id=asta["chat_id"],
                text=(
                    f"🔔 ASTA TERMINATA\n\n"
                    f"📦 {asta['titolo']}\n"
                    f"🏆 Vincitore: {asta['vincitore']}\n"
                    f"💰 Prezzo finale: {asta['attuale']}€"
                )
            )

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
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,
        "vincitore": None,
    }

    if msg.photo:
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=render_asta(asta)
        )
    else:
        sent = await msg.reply_text(render_asta(asta))

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

    # Prima offerta → parte il timer
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    # Offerta più bassa o uguale
    if valore <= asta["attuale"]:
        await msg.reply_text(
            f"❌ Offerta non valida\n💰 Offerta attuale: {asta['attuale']}€"
        )
        return

    # Offerta valida
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

    app.job_queue.run_repeating(controllo_aste, interval=CHECK_INTERVAL, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
