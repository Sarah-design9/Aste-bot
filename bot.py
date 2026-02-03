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

DURATA_ASTA_ORE = 24

logging.basicConfig(level=logging.INFO)

aste = {}
next_id = 1


# ================= RENDER =================
def render_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    fine = (
        "⏳ Parte alla prima offerta"
        if a["fine"] is None
        else a["fine"].strftime("%d/%m %H:%M")
    )

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine asta: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi con un importo per offrire"
    )


# ================= VENDITA =================
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # 🔴 MAI intercettare le risposte
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

    global next_id
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
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if not msg.reply_to_message or not msg.text:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        await msg.reply_text("❌ Inserisci solo numeri")
        return

    valore = int(valore_raw)
    reply_id = msg.reply_to_message.message_id

    asta = None
    for a in aste.values():
        if a["message_id"] == reply_id and a["attiva"]:
            asta = a
            break

    if not asta:
        return

    # ⛔ ASTA SCADUTA
    if asta["fine"] and datetime.now() > asta["fine"]:
        asta["attiva"] = False
        await msg.reply_text("⏰ Asta terminata")
        return

    # ===== PRIMA OFFERTA =====
    if asta["fine"] is None:
        if valore < asta["base"]:
            await msg.reply_text(
                f"❌ Offerta troppo bassa. Base: {asta['base']}€"
            )
            return

        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)
        asta["attuale"] = valore

    # ===== OFFERTE SUCCESSIVE =====
    else:
        if valore <= asta["attuale"]:
            await msg.reply_text(
                f"❌ Offerta troppo bassa. Attuale: {asta['attuale']}€"
            )
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
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()

    # ⚠️ ORDINE FONDAMENTALE
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, offerta))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, vendita))

    app.run_polling()


if __name__ == "__main__":
    main()
