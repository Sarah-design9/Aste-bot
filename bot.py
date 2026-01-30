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

TOKEN = "INSERISCI_QUI_IL_TUO_TOKEN"
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


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
        f"👉 Rispondi con un importo per offrire"
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
        "venditore": msg.from_user.id,
        "chat_id": msg.chat_id,
        "message_id": None,
        "attiva": True,
        "fine": None,          # ⬅️ parte alla prima offerta
        "has_photo": bool(msg.photo),
    }

    testo_asta = render_asta(asta)

    if msg.photo:
        sent = await msg.reply_photo(
            photo=msg.photo[-1].file_id,
            caption=testo_asta,
        )
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
    reply = msg.reply_to_message

    asta = None
    for a in aste.values():
        if a["message_id"] == reply.message_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    # prima offerta → avvia il timer
    if asta["fine"] is None:
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

    if datetime.now() > asta["fine"]:
        asta["attiva"] = False
        return

    if valore <= asta["attuale"]:
        return

    asta["attuale"] = valore
    nuovo_testo = render_asta(asta)

    # 🔑 QUI È LA PARTE CHE SISTEMA IL BUG FOTO
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
        testo += (
            f"#{a['id']} – {a['titolo']}\n"
            f"💰 {a['attuale']}€\n\n"
        )

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
