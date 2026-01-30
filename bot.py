import os
import re
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

TOKEN = os.environ.get("TOKEN") or "INCOLLA_QUI_IL_TOKEN"

aste = {}
next_id = 1


def estrai_importo(testo):
    if not testo:
        return None
    m = re.search(r"(\d+)", testo)
    return int(m.group(1)) if m else None


def format_asta(a):
    stato = "🟢 ATTIVA" if a["attiva"] else "⏳ IN ATTESA"
    fine = a["fine"].strftime("%d/%m %H:%M") if a["fine"] else "-"
    return (
        f"📦 *Asta #{a['id']}*\n"
        f"📝 {a['oggetto']}\n"
        f"💰 Prezzo attuale: *{a['prezzo']}€*\n"
        f"👤 Miglior offerente: {a['offerente'] or '-'}\n"
        f"⏰ Fine: {fine}\n"
        f"{stato}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot aste attivo e funzionante")


async def vendita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id

    testo = update.message.caption or update.message.text
    if not testo.lower().startswith("#vendita"):
        return

    parti = testo.split(maxsplit=2)
    if len(parti) < 3:
        return

    oggetto = parti[1]
    base = estrai_importo(parti[2])
    if base is None:
        return

    asta_id = next_id
    next_id += 1

    aste[asta_id] = {
        "id": asta_id,
        "oggetto": oggetto,
        "prezzo": base,
        "venditore": update.message.from_user.mention_html(),
        "offerente": None,
        "attiva": False,
        "fine": None,
        "chat_id": update.message.chat_id,
        "msg_id": None,
        "has_photo": bool(update.message.photo)
    }

    testo_asta = format_asta(aste[asta_id])

    if update.message.photo:
        msg = await update.message.reply_photo(
            photo=update.message.photo[-1].file_id,
            caption=testo_asta,
            parse_mode="Markdown"
        )
    else:
        msg = await update.message.reply_text(
            testo_asta,
            parse_mode="Markdown"
        )

    aste[asta_id]["msg_id"] = msg.message_id


async def offerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    importo = estrai_importo(update.message.text)
    if importo is None:
        return

    reply_id = update.message.reply_to_message.message_id

    for a in aste.values():
        if a["msg_id"] != reply_id:
            continue

        if a["fine"] and datetime.now() > a["fine"]:
            return

        if importo <= a["prezzo"]:
            return

        if not a["attiva"]:
            a["attiva"] = True
            a["fine"] = datetime.now() + timedelta(hours=24)
            asyncio.create_task(chiudi_asta(a["id"], context))

        a["prezzo"] = importo
        a["offerente"] = update.message.from_user.mention_html()

        if a["has_photo"]:
            await context.bot.edit_message_caption(
                chat_id=a["chat_id"],
                message_id=a["msg_id"],
                caption=format_asta(a),
                parse_mode="Markdown"
            )
        else:
            await context.bot.edit_message_text(
                chat_id=a["chat_id"],
                message_id=a["msg_id"],
                text=format_asta(a),
                parse_mode="Markdown"
            )
        return


async def chiudi_asta(asta_id, context):
    await asyncio.sleep(24 * 3600)

    a = aste.get(asta_id)
    if not a:
        return

    testo = (
        f"🏁 *Asta #{a['id']} chiusa*\n"
        f"📦 {a['oggetto']}\n"
        f"💰 Prezzo finale: *{a['prezzo']}€*\n"
        f"👤 Vincitore: {a['offerente'] or 'nessuno'}"
    )

    await context.bot.send_message(
        chat_id=a["chat_id"],
        text=testo,
        parse_mode="Markdown"
    )

    del aste[asta_id]


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not aste:
        await update.message.reply_text("❌ Nessuna asta disponibile")
        return

    righe = []
    for a in aste.values():
        stato = "ATTIVA" if a["attiva"] else "IN ATTESA"
        righe.append(f"#{a['id']} • {a['oggetto']} • {a['prezzo']}€ • {stato}")

    await update.message.reply_text("🛒 *SHOP*\n" + "\n".join(righe), parse_mode="Markdown")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("shop", shop))

# VENDITA: testo + foto
app.add_handler(MessageHandler(filters.ALL, vendita))

# OFFERTE: reply a qualsiasi messaggio
app.add_handler(MessageHandler(filters.REPLY, offerta))

app.run_polling()
