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

TOKEN = os.getenv("BOT_TOKEN")
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1

# ================= UTILS =================
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    if a["fine"] is None:
        fine_txt = "⏳ In attesa della prima offerta"
    else:
        fine_txt = a["fine"].strftime("%d/%m %H:%M")

    return (
        f"📦 {a['titolo']}\n"
        f"🆔 Asta #{a['id']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine_txt}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )

def estrai_id_asta(testo):
    m = re.search(r"Asta #(\d+)", testo)
    return int(m.group(1)) if m else None

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ciao!\n\n"
        "Per creare un’asta:\n"
        "#vendita NOME PREZZO\n\n"
        "Esempio:\n"
        "#vendita Orologio 50€"
    )

# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message

    # ❗️IGNORA messaggi in risposta (sono offerte)
    if msg.reply_to_message:
        return

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
        "attiva": True,
        "fine": None,
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        await msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
    else:
        await msg.reply_text(testo_asta)

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

    testo_risposto = (
        msg.reply_to_message.caption
        if msg.reply_to_message.caption
        else msg.reply_to_message.text
    )

    if not testo_risposto:
        return

    id_asta = estrai_id_asta(testo_risposto)
    if not id_asta or id_asta not in aste:
        return

    asta = aste[id_asta]
    if not asta["attiva"]:
        return

    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if valore <= asta["attuale"]:
        return

    asta["attuale"] = valore

    nuovo_testo = render_asta(asta)

    try:
        await context.bot.edit_message_caption(
            chat_id=msg.chat_id,
            message_id=msg.reply_to_message.message_id,
            caption=nuovo_testo,
        )
    except:
        await context.bot.edit_message_text(
            chat_id=msg.chat_id,
            message_id=msg.reply_to_message.message_id,
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
        testo += f"#{a['id']} – {a['titolo']} | {a['attuale']}€\n"

    await update.message.reply_text(testo)

# ================= MAIN =================
def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN mancante")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    # ORDINE CORRETTO + FILTRI CORRETTI
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT, offerta))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.REPLY, vendita))

    app.run_polling()

if __name__ == "__main__":
    main()
