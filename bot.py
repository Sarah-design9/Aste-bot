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

# ================= CONFIG =================
DURATA_ASTA_ORE = 24
CHECK_INTERVAL = 60  # controllo ogni minuto

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTILS =================
def estrai_importo(testo):
    if not testo:
        return None
    raw = re.sub(r"[^\d]", "", testo)
    return int(raw) if raw.isdigit() else None

def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"
    fine = (
        a["fine"].strftime("%d/%m %H:%M")
        if a["fine"]
        else "⏳ In attesa della prima offerta"
    )

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )

# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # TESTO DEL MESSAGGIO
    testo = msg.caption if msg.photo else msg.text

    # OFFERTA: risposta a un messaggio
    if msg.reply_to_message and msg.text:
        await offerta(update, context)
        return

    # VENDITA
    if testo and testo.lower().startswith("#vendita"):
        await vendita(update, context)
        return

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message

    testo = msg.caption if msg.photo else msg.text
    parti = testo.split()
    if len(parti) < 3:
        return

    titolo = " ".join(parti[1:-1])
    base = estrai_importo(parti[-1])
    if base is None:
        return

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

    testo_asta = render_asta(asta)

    try:
        if msg.photo:
            sent = await msg.reply_photo(
                photo=msg.photo[-1].file_id,
                caption=testo_asta
            )
        else:
            sent = await msg.reply_text(testo_asta)
    except Exception as e:
        logging.error(f"Errore vendita: {e}")
        return

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    valore = estrai_importo(msg.text)
    if valore is None:
        return

    asta = None
    for a in aste.values():
        if a["attiva"] and a["message_id"] == msg.reply_to_message.message_id:
            asta = a
            break

    if not asta:
        return

    # Prima offerta → parte il timer
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if valore < asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    if valore == asta["attuale"]:
        await msg.reply_text("⚠️ Offerta uguale alla corrente")
        return

    asta["attuale"] = valore
    asta["vincitore"] = msg.from_user

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

# ================= CHIUSURA AUTOMATICA =================
async def check_aste(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for a in aste.values():
        if a["attiva"] and a["fine"] and now > a["fine"]:
            a["attiva"] = False

            testo_finale = (
                f"🔴 ASTA TERMINATA\n\n"
                f"📦 {a['titolo']}\n"
                f"💰 Prezzo finale: {a['attuale']}€\n"
                f"🏆 Vincitore: {a['vincitore'].full_name if a['vincitore'] else 'Nessuno'}"
            )

            try:
                await context.bot.edit_message_caption(
                    chat_id=a["chat_id"],
                    message_id=a["message_id"],
                    caption=testo_finale
                )
            except:
                await context.bot.edit_message_text(
                    chat_id=a["chat_id"],
                    message_id=a["message_id"],
                    text=testo_finale
                )

            await context.bot.send_message(
                chat_id=a["chat_id"],
                text=f"🏁 Asta conclusa: {a['titolo']} – {a['attuale']}€"
            )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, router))

    app.job_queue.run_repeating(check_aste, interval=CHECK_INTERVAL, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
