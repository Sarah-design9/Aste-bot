import re
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

BOT_TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"

aste = {}
next_asta_id = 1


def estrai_prezzo(testo):
    if not testo:
        return None
    testo = testo.lower().replace("€", "").replace("#offerta", "").strip()
    m = re.search(r"\d+", testo)
    return int(m.group()) if m else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot aste attivo\n"
        "• #vendita nome prezzo\n"
        "• Rispondi al messaggio con un numero"
    )


async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_asta_id

    msg = update.message
    testo = msg.caption if msg.caption else msg.text

    if not testo or not testo.lower().startswith("#vendita"):
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    nome = " ".join(parti[1:-1])
    prezzo = estrai_prezzo(parti[-1])
    if prezzo is None:
        return

    asta_id = next_asta_id
    next_asta_id += 1

    testo_asta = (
        f"🆔 Asta #{asta_id}\n"
        f"📦 {nome}\n"
        f"💰 Prezzo attuale: {prezzo}€\n\n"
        f"↩️ Rispondi a QUESTO messaggio con l’offerta"
    )

    # 🔥 NON creare un nuovo messaggio
    if msg.photo:
        await msg.edit_caption(caption=testo_asta)
        tipo = "photo"
        message_id = msg.message_id
    else:
        await msg.edit_text(testo_asta)
        tipo = "text"
        message_id = msg.message_id

    aste[asta_id] = {
        "nome": nome,
        "prezzo": prezzo,
        "venditore": msg.from_user,
        "chat_id": msg.chat_id,
        "messaggio_id": message_id,
        "tipo": tipo,
        "fine": time.time() + 86400,
    }


async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message:
        return

    prezzo = estrai_prezzo(msg.text)
    if prezzo is None:
        return

    for asta_id, asta in aste.items():
        if (
            msg.reply_to_message.message_id == asta["messaggio_id"]
            and msg.chat_id == asta["chat_id"]
        ):
            if prezzo <= asta["prezzo"]:
                await msg.reply_text("❌ Offerta troppo bassa")
                return

            asta["prezzo"] = prezzo

            nuovo_testo = (
                f"🆔 Asta #{asta_id}\n"
                f"📦 {asta['nome']}\n"
                f"💰 Prezzo attuale: {prezzo}€\n\n"
                f"↩️ Rispondi a QUESTO messaggio con l’offerta"
            )

            if asta["tipo"] == "photo":
                await context.bot.edit_message_caption(
                    chat_id=asta["chat_id"],
                    message_id=asta["messaggio_id"],
                    caption=nuovo_testo
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=asta["chat_id"],
                    message_id=asta["messaggio_id"],
                    text=nuovo_testo
                )
            return


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    testo = "🛒 ASTE ATTIVE\n\n"
    for i, a in aste.items():
        testo += f"#{i} • {a['nome']} – {a['prezzo']}€\n"

    await update.message.reply_text(testo)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^#vendita"),
            nuova_vendita,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO & filters.CaptionRegex(r"^#vendita"),
            nuova_vendita,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.REPLY,
            offerta,
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
