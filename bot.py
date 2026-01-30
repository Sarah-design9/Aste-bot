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

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"
DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


def render_asta(a):
    if a["fine"] is None:
        fine_text = "⏳ Parte alla prima offerta"
    else:
        fine_text = a["fine"].strftime("%d/%m %H:%M")

    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine_text}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )


# ================= SHOP =================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attive = [a for a in aste.values() if a["attiva"]]
    if not attive:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE DISPONIBILI\n\n"
    for a in attive:
        testo += f"#{a['id']} – {a['titolo']} | 💰 {a['attuale']}€\n"

    await update.message.reply_text(testo)


# ================= HANDLER UNICO =================
async def gestore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message

    # ===== OFFERTA =====
    if msg.reply_to_message and msg.text:
        valore_raw = re.sub(r"[^\d]", "", msg.text)
        if not valore_raw:
            return

        valore = int(valore_raw)
        reply_id = msg.reply_to_message.message_id

        for asta in aste.values():
            if asta["message_id"] == reply_id and asta["attiva"]:

                # prima offerta → parte il timer
                if asta["fine"] is None:
                    asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

                # asta scaduta
                if datetime.now() > asta["fine"]:
                    asta["attiva"] = False
                    return

                # offerta troppo bassa
                if valore <= asta["attuale"]:
                    return

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
                return

    # ===== VENDITA =====
    testo = msg.caption if msg.photo else msg.text
    if not testo or not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    titolo = " ".join(parti[1:-1])
    base_raw = re.sub(r"[^\d]", "", parti[-1])
    if not base_raw:
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
            caption=testo_asta,
        )
    else:
        sent = await msg.reply_text(testo_asta)

    asta["message_id"] = sent.message_id
    aste[next_id] = asta
    next_id += 1


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.ALL, gestore))
    app.run_polling()


if __name__ == "__main__":
    main()
