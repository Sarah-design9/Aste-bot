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

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


def render_asta(a):
    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n\n"
        f"👉 Rispondi a questo messaggio con un importo"
    )


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo")


# ================= HANDLER =================
async def gestore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message
    if not msg:
        return

    # ================= OFFERTA =================
    if msg.reply_to_message and msg.text:
        valore_raw = re.sub(r"[^\d]", "", msg.text)
        if not valore_raw:
            return

        valore = int(valore_raw)
        reply_id = msg.reply_to_message.message_id

        for asta in aste.values():
            if asta["message_id"] == reply_id:
                if valore <= asta["attuale"]:
                    await msg.reply_text("❌ Offerta troppo bassa")
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

    # ================= VENDITA =================
    testo = msg.caption if msg.photo else msg.text
    if not testo or not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        await msg.reply_text("❌ Usa: #vendita nome prezzo")
        return

    titolo = " ".join(parti[1:-1])
    base_raw = re.sub(r"[^\d]", "", parti[-1])
    if not base_raw:
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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestore))
    app.run_polling()


if __name__ == "__main__":
    main()
