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

logging.basicConfig(level=logging.INFO)

DURATA_ASTA_ORE = 24
aste = {}
next_id = 1

# ================= RENDER =================
def render_asta(a):
    fine = "⏳ Parte alla prima offerta" if a["fine"] is None else a["fine"].strftime("%d/%m %H:%M")
    stato = "🟢 ATTIVA" if a["attiva"] else "🔴 CHIUSA"

    return (
        f"📦 {a['titolo']}\n"
        f"💰 Base d’asta: {a['base']}€\n"
        f"🔥 Offerta attuale: {a['attuale']}€\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}\n\n"
        f"👉 Rispondi a QUESTO messaggio con un importo"
    )

# ================= CHIUSURA ASTA =================
async def chiudi_asta(context: ContextTypes.DEFAULT_TYPE):
    asta_id = context.job.data
    asta = aste.get(asta_id)

    if not asta or not asta["attiva"]:
        return

    asta["attiva"] = False

    testo_finale = render_asta(asta) + "\n\n🏆 ASTA CHIUSA!"

    try:
        if asta["foto"]:
            await context.bot.edit_message_caption(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                caption=testo_finale
            )
        else:
            await context.bot.edit_message_text(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                text=testo_finale
            )

        await context.bot.send_message(
            chat_id=asta["chat_id"],
            text=f"🏆 Asta chiusa! Vince con {asta['attuale']}€"
        )

    except Exception as e:
        logging.error(e)

# ================= GESTIONE MESSAGGI =================
async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    msg = update.message
    if not msg:
        return

    # ===== VENDITA =====
    testo = msg.caption if msg.photo else msg.text
    if testo and testo.lower().startswith("#vendita"):
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
            "foto": bool(msg.photo),
        }

        testo_asta = render_asta(asta)

        if msg.photo:
            sent = await msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
        else:
            sent = await msg.reply_text(testo_asta)

        asta["message_id"] = sent.message_id
        aste[next_id] = asta
        next_id += 1
        return

    # ===== OFFERTE =====
    if not msg.text or not msg.reply_to_message:
        return

    valore_raw = re.sub(r"[^\d]", "", msg.text)
    if not valore_raw.isdigit():
        return

    valore = int(valore_raw)

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

    # PRIMA OFFERTA
    if asta["fine"] is None:
        if valore < asta["base"]:
            await msg.reply_text("❌ Offerta troppo bassa")
            return

        asta["attuale"] = valore
        asta["fine"] = datetime.now() + timedelta(hours=DURATA_ASTA_ORE)

        # PROGRAMMA CHIUSURA
        context.job_queue.run_once(
            chiudi_asta,
            when=DURATA_ASTA_ORE * 3600,
            data=asta["id"]
        )

    # OFFERTE SUCCESSIVE
    else:
        if valore <= asta["attuale"]:
            await msg.reply_text("❌ Offerta troppo bassa")
            return

        asta["attuale"] = valore

    # AGGIORNA POST
    testo_aggiornato = render_asta(asta)

    try:
        if asta["foto"]:
            await context.bot.edit_message_caption(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                caption=testo_aggiornato
            )
        else:
            await context.bot.edit_message_text(
                chat_id=asta["chat_id"],
                message_id=asta["message_id"],
                text=testo_aggiornato
            )
    except Exception as e:
        logging.error(e)

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
    TOKEN = os.environ["BOT_TOKEN"]

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))

    app.run_polling()

if __name__ == "__main__":
    main()
