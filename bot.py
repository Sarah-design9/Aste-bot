from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

TOKEN = os.environ.get("TOKEN")

# ===== DATI ASTE =====
auctions = {}  # id -> dati asta
auction_id_counter = 1


# ===== /START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT ASTE ATTIVO!\n\n"
        "📌 Comandi disponibili:\n"
        "#vendita Nome oggetto - Prezzo base\n"
        "#offerta ID prezzo\n"
        "#chiudi ID\n"
        "/shop"
    )


# ===== GESTIONE MESSAGGI =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auction_id_counter

    text = update.message.text or update.message.caption or ""
    text = text.strip()
    user = update.message.from_user.first_name

    # ---------- VENDITA ----------
    if text.startswith("#vendita"):
        description = text[len("#vendita"):].strip()

        auction_id = auction_id_counter
        auction_id_counter += 1

        auctions[auction_id] = {
            "description": description,
            "price": 0,
            "winner": None,
            "active": True,
        }

        await update.message.reply_text(
            f"📣 BOT ASTE – NUOVO OGGETTO\n\n"
            f"🆔 #{auction_id}\n"
            f"{description}\n\n"
            f"💰 Offerte aperte!\n"
            f"✍️ Scrivi: #offerta {auction_id} prezzo"
        )

    # ---------- OFFERTA ----------
    elif text.startswith("#offerta"):
        parts = text.split()

        if len(parts) != 3:
            await update.message.reply_text(
                "❌ Formato errato.\nUsa: #offerta ID prezzo"
            )
            return

        try:
            auction_id = int(parts[1])
            offer = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ ID o prezzo non valido.")
            return

        auction = auctions.get(auction_id)

        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Asta non trovata o già chiusa.")
            return

        if offer <= auction["price"]:
            winner = auction["winner"] or "Nessuno"
            await update.message.reply_text(
                f"❌ OFFERTA RIFIUTATA\n\n"
                f"🆔 Oggetto #{auction_id}\n"
                f"💶 Offerta proposta: {offer}€\n"
                f"📈 Prezzo attuale: {auction['price']}€\n"
                f"👤 Miglior offerente: {winner}"
            )
            return

        auction["price"] = offer
        auction["winner"] = user

        await update.message.reply_text(
            f"🔥 NUOVA OFFERTA REGISTRATA!\n\n"
            f"🆔 Oggetto #{auction_id}\n"
            f"👤 {user}\n"
            f"💶 {offer}€"
        )

    # ---------- CHIUSURA ----------
    elif text.startswith("#chiudi"):
        parts = text.split()

        if len(parts) != 2:
            await update.message.reply_text("❌ Usa: #chiudi ID")
            return

        try:
            auction_id = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ ID non valido.")
            return

        auction = auctions.get(auction_id)

        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Asta non trovata o già chiusa.")
            return

        auction["active"] = False

        if aucti
