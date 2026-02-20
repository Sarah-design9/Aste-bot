import json
import os
import asyncio
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "7998174738:AAHChHqy0hicxVPr5kWZ5xf61T-akl1bCYw"

aste = {}
next_id = 1
FILE_ASTE = "aste.json"

# ------------------ SALVATAGGIO ------------------

def salva_aste():
    with open(FILE_ASTE, "w") as f:
        json.dump({
            "aste": aste,
            "next_id": next_id
        }, f)

def carica_aste():
    global aste, next_id
    if os.path.exists(FILE_ASTE):
        with open(FILE_ASTE, "r") as f:
            dati = json.load(f)
            aste = {int(k): v for k, v in dati["aste"].items()}
            next_id = dati["next_id"]

# ------------------ CREAZIONE ASTA ------------------

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id

    if update.message.photo:
        testo = update.message.caption

        if testo and testo.lower().startswith("vendita"):
            parti = testo.split("\n")

            try:
                titolo = parti[0].replace("Vendita", "").strip()
                prezzo_base = float(parti[1].replace("Base d'asta:", "").replace("€", "").strip())
            except:
                return

            asta = {
                "titolo": titolo,
                "prezzo_base": prezzo_base,
                "offerta_attuale": prezzo_base,
                "miglior_offerente": None,
                "attiva": True,
                "chat_id": update.effective_chat.id,
                "message_id": None,
                "photo_file_id": update.message.photo[-1].file_id
            }

            caption = (
                f"🔥 ASTA #{next_id}\n\n"
                f"📦 {titolo}\n"
                f"💰 Base d'asta: {prezzo_base}€\n"
                f"🏆 Offerta attuale: {prezzo_base}€\n"
                f"👤 Nessuna offerta\n\n"
                f"Scrivi: Offerta X"
            )

            sent = await update.message.reply_photo(
                photo=asta["photo_file_id"],
                caption=caption
            )

            asta["message_id"] = sent.message_id
            aste[next_id] = asta
            next_id += 1

            salva_aste()

            return

    if update.message.text:
        testo = update.message.text.lower()

        if testo.startswith("offerta"):
            try:
                import re
                match = re.search(r"offerta\s+(\d+)", testo)
                if not match:
                    return
                importo = float(match.group(1))
            except:
                return

            # cerca ultima asta attiva
            asta_id = None
            for id_asta in sorted(aste.keys(), reverse=True):
                if aste[id_asta]["attiva"]:
                    asta_id = id_asta
                    break

            if not asta_id:
                return

            asta = aste[asta_id]

            if importo < asta["offerta_attuale"]:
                await update.message.reply_text("❌ Offerta troppo bassa.")
                return

            # accetta anche offerta uguale alla base d'asta se prima offerta
            if importo == asta["prezzo_base"] and asta["miglior_offerente"] is None:
                pass
            elif importo <= asta["offerta_attuale"]:
                await update.message.reply_text("❌ Offerta troppo bassa.")
                return

            asta["offerta_attuale"] = importo
            asta["miglior_offerente"] = update.message.from_user.full_name

            caption = (
                f"🔥 ASTA #{asta_id}\n\n"
                f"📦 {asta['titolo']}\n"
                f"💰 Base d'asta: {asta['prezzo_base']}€\n"
                f"🏆 Offerta attuale: {asta['offerta_attuale']}€\n"
                f"👤 Miglior offerente: {asta['miglior_offerente']}\n\n"
                f"Scrivi: Offerta X"
            )

            try:
                await context.bot.edit_message_caption(
                    chat_id=asta["chat_id"],
                    message_id=asta["message_id"],
                    caption=caption
                )
            except:
                pass

            salva_aste()

# ------------------ SHOP ------------------

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attive = [ (id_, a) for id_, a in aste.items() if a["attiva"] ]

    if not attive:
        await update.message.reply_text("🛒 Nessuna asta disponibile.")
        return

    testo = "🛒 ASTE ATTIVE:\n\n"
    for id_, a in attive:
        testo += (
            f"🔹 #{id_} - {a['titolo']}\n"
            f"💰 {a['offerta_attuale']}€\n\n"
        )

    await update.message.reply_text(testo)

# ------------------ AVVIO ------------------

def main():
    carica_aste()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, gestisci_messaggi))

    app.run_polling()

if __name__ == "__main__":
    main()
