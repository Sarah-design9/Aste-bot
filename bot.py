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

BOT_TOKEN = "INSERISCI_IL_TUO_TOKEN"

# aste attive
aste = {}
next_asta_id = 1


def estrai_prezzo(testo: str):
    if not testo:
        return None
    testo = testo.lower().replace("€", "").replace("#offerta", "").strip()
    match = re.search(r"\d+", testo)
    return int(match.group()) if match else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot aste attivo\n"
        "Usa #vendita nome prezzo\n"
        "E rispondi all’asta con un numero per fare un’offerta"
    )


async def nuova_vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_asta_id

    msg = update.message
    testo = msg.caption if msg.photo else msg.text

    if not testo:
        return

    parti = testo.split()
    if len(parti) < 3:
        return

    nome = " ".join(parti[1:-1])
    prezzo_base = estrai_prezzo(parti[-1])
    if prezzo_base is None:
        return

    asta_id = next_asta_id
    next_asta_id += 1

    aste[asta_id] = {
        "nome": nome,
        "prezzo": prezzo_base,
        "venditore": msg.from_user,
        "messaggio_id": None,
        "chat_id": msg.chat_id,
        "fine": time.time() + 86400,
    }

    testo_asta = (
        f"🆔 Asta #{asta_id}\n"
        f"📦 {nome}\n"
        f"💰 Prezzo attuale: {prezzo_base}€\n\n"
        f"↩️ Rispondi a QUESTO messaggio con l’offerta"
    )

    if msg.photo:
        sent = await msg.reply_photo(msg.photo[-1].file_id, caption=testo_asta)
    else:
        sent = await msg.reply_text(testo_asta)

    aste[asta_id]["messaggio_id"] = sent.message_id


async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # deve essere una risposta
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

            await msg.reply_text(
                f"🔥 Nuova offerta!\n"
                f"🆔 Asta #{asta_id}\n"
                f"💰 {prezzo}€ da {msg.from_user.first_name}"
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
            filters.Regex(r"^#vendita") & (filters.TEXT | filters.PHOTO),
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
