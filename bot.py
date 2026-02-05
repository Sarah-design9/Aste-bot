import os
import re
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Stato aste attive
aste = {}
# struttura:
# aste[message_id] = {
#   "base": int,
#   "attuale": int,
#   "autore": int,
#   "fine": datetime,
#   "post_id": int,
#   "chat_id": int
# }

BASE_RE = re.compile(r"base\s*[:\-]?\s*(\d+)", re.IGNORECASE)
OFFERTA_RE = re.compile(r"^(\d+)\s*€?$")


# --------- VENDITA ---------
async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text and not msg.caption:
        return

    testo = msg.text or msg.caption
    if "#vendita" not in testo.lower():
        return

    match = BASE_RE.search(testo)
    if not match:
        await msg.reply_text("❌ Base d'asta non trovata (scrivi: base 10)")
        return

    base = int(match.group(1))

    aste[msg.message_id] = {
        "base": base,
        "attuale": base,
        "autore": msg.from_user.id,
        "fine": datetime.utcnow() + timedelta(hours=24),
        "post_id": msg.message_id,
        "chat_id": msg.chat_id,
    }

    await msg.reply_text(
        f"✅ Asta avviata!\n"
        f"💰 Base d'asta: {base}€\n"
        f"⏰ Fine tra 24 ore"
    )


# --------- OFFERTE ---------
async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    match = OFFERTA_RE.match(msg.text.strip())
    if not match:
        return

    valore = int(match.group(1))

    # cerca asta collegata (risposta o ultimo messaggio)
    asta = None
    asta_id = None

    if msg.reply_to_message and msg.reply_to_message.message_id in aste:
        asta_id = msg.reply_to_message.message_id
        asta = aste[asta_id]
    else:
        for k, v in aste.items():
            if v["chat_id"] == msg.chat_id:
                asta_id = k
                asta = v

    if not asta:
        return

    # asta scaduta
    if datetime.utcnow() > asta["fine"]:
        await msg.reply_text("⛔ Asta terminata")
        return

    if valore < asta["attuale"]:
        await msg.reply_text("❌ Offerta troppo bassa")
        return

    if valore == asta["attuale"]:
        await msg.reply_text("⚠️ Offerta uguale all'attuale")
        return

    # offerta valida
    asta["attuale"] = valore

    await context.bot.edit_message_text(
        chat_id=asta["chat_id"],
        message_id=asta["post_id"],
        text=(
            f"📢 ASTA IN CORSO\n"
            f"💰 Offerta attuale: {valore}€\n"
            f"⏰ Fine: {asta['fine'].strftime('%H:%M %d/%m')}"
        ),
    )


# --------- CONTROLLO SCADENZA ---------
async def controlla_aste(app):
    while True:
        now = datetime.utcnow()
        da_chiudere = []

        for mid, asta in aste.items():
            if now > asta["fine"]:
                da_chiudere.append(mid)

        for mid in da_chiudere:
            asta = aste.pop(mid)
            await app.bot.send_message(
                chat_id=asta["chat_id"],
                text=f"🏁 ASTA TERMINATA\n💰 Prezzo finale: {asta['attuale']}€"
            )

        await asyncio.sleep(60)


# --------- MAIN ---------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, vendita))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, offerta))

    asyncio.create_task(controlla_aste(app))

    print("🤖 Bot avviato")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
