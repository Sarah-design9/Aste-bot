import logging
import os
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
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN non trovato nelle variabili Railway")

DURATA_ASTA_ORE = 24

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ================= STORAGE =================
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
        f"👉 Rispondi con un importo per offrire"
    )

def estrai_importo(testo):
    if not testo:
        return None
    valore = re.sub(r"[^\d]", "", testo)
    return int(valore) if valore.isdigit() else None

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

    base = estrai_importo(parti[-1])
    if base is None:
        return

    titolo = " ".join(parti[1:-1])

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

    try:
        if msg.photo:
            sent = await msg.reply_photo(
                photo=msg.photo[-1].file_id,
                caption=testo_asta,
            )
        else:
            sent = await msg.reply_text(testo_asta)
    except Exception as e:
        logging.error(f"Errore invio vendita: {e}")
        return

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1

# ================= OFFERTE =================
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.text or not msg.reply_to_message:
        return

    valore = estrai_importo(msg.text)
    if valore is None:
        return

    reply_id = msg.reply_to_message.message_id
    asta = None

    for a in aste.values():
        if a["message_id"] == reply_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    # prima offerta → avvia timer
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    # asta scaduta
    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        return

    # offerta troppo bassa
    if valore <= asta["attuale"]:
        await msg.reply_text(
            f"❌ Offerta non valida.\n"
            f"L’offerta attuale è {asta['attuale']}€"
        )
        return

    # aggiorna asta
    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    try:
        await context.bot.edit_message_caption(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            caption=nuovo_testo,
        )
    except:
        await context.bot.edit_message_text(
            chat_id=asta["chat_id"],
            message_id=asta["message_id"],
            text=nuovo_testo,
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
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))

    logging.info("🤖 Bot avviato correttamente")
    app.run_polling()

if __name__ == "__main__":
    main()
