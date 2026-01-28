from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os
import time

TOKEN = os.environ.get("TOKEN")

# ===== DATI ASTE =====
auctions = {}  # id -> dati asta
auction_id_counter = 1

# Lista username admin (Telegram username senza @)
ADMINS = ["tuo_username"]  # sostituisci con i tuoi admin reali

# Durata asta in secondi (24h = 86400)
AUCTION_DURATION = 24 * 3600


# ===== /START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT ASTE ATTIVO!\n\n"
        "Comandi:\n"
        "#vendita descrizione (solo admin, puoi aggiungere foto)\n"
        "#offerta ID prezzo\n"
        "#chiudi ID (solo admin)\n"
        "/shop"
    )


# ===== FUNZIONE DI CONTROLLO ADMIN =====
def is_admin(username: str):
    return username in ADMINS


# ===== FUNZIONE CHIUSURA AUTOMATICA =====
def check_auction_timeout():
    now = time.time()
    for aid, auction in list(auctions.items()):
        if auction["active"] and (now - auction["start_time"]) >= AUCTION_DURATION:
            auction["active"] = False


# ===== GESTIONE MESSAGGI =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auction_id_counter

    # Controllo chiusura aste scadute
    check_auction_timeout()

    text = update.message.text or update.message.caption or ""
    text = text.strip()
    user = update.message.from_user.username or update.message.from_user.first_name

    # ---------- VENDITA ----------
    if text.startswith("#vendita"):
        if not is_admin(user):
            await update.message.reply_text("❌ Solo gli admin possono aprire aste")
            return

        description = text.replace("#vendita", "").strip()
        auction_id = auction_id_counter
        auction_id_counter += 1

        photo_file_id = update.message.photo[-1].file_id if update.message.photo else None

        auctions[auction_id] = {
            "description": description,
            "price": 0,
            "winner": None,
            "active": True,
            "photo": photo_file_id,
            "start_time": time.time()
        }

        msg = (
            f"📣 NUOVO OGGETTO\nID: {auction_id}\n{description}\n"
            f"💰 Offerte aperte per 24h!\nScrivi: #offerta {auction_id} prezzo"
        )

        if photo_file_id:
            await update.message.reply_photo(photo=photo_file_id, caption=msg)
        else:
            await update.message.reply_text(msg)

    # ---------- OFFERTA ----------
    elif text.startswith("#offerta"):
        parts = text.split()
        if len(parts) != 3:
            await update.message.reply_text("❌ Formato corretto: #offerta ID prezzo")
            return

        try:
            auction_id = int(parts[1])
            offer = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ ID o prezzo non valido")
            return

        auction = auctions.get(auction_id)
        if not auction:
            await update.message.reply_text("❌ Asta non trovata")
            return

        # Controllo se asta è chiusa
        if not auction["active"]:
            await update.message.reply_text("❌ Asta chiusa, non puoi offrire")
            return

        # Controllo durata 24h
        if (time.time() - auction["start_time"]) >= AUCTION_DURATION:
            auction["active"] = False
            await update.message.reply_text("❌ Asta chiusa, fuori tempo")
            return

        min_offer = auction["price"] + 1  # incremento minimo +1€
        if offer < min_offer:
            winner = auction["winner"] or "Nessuno"
            await update.message.reply_text(
                f"❌ OFFERTA RIFIUTATA (min {min_offer}€)\nID: {auction_id}\nPrezzo attuale: {auction['price']}€\nMiglior offerente: {winner}"
            )
            return

        auction["price"] = offer
        auction["winner"] = user

        await update.message.reply_text(
            f"🔥 NUOVA OFFERTA!\nID: {auction_id}\n{user} → {offer}€"
        )

    # ---------- CHIUSURA MANUALE ----------
    elif text.startswith("#chiudi"):
        if not is_admin(user):
            await update.message.reply_text("❌ Solo admin possono chiudere aste")
            return

        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("❌ Usa: #chiudi ID")
            return

        try:
            auction_id = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ ID non valido")
            return

        auction = auctions.get(auction_id)
        if not auction or not auction["active"]:
            await update.message.reply_text("❌ Asta non trovata o già chiusa")
            return

        auction["active"] = False

        msg = f"🏁 ASTA CHIUSA\nID: {auction_id}\n{auction['description']}\n"
        if auction["winner"]:
            msg += f"Vincitore: {auction['winner']}\nPrezzo finale: {auction['price']}€"
        else:
            msg += "❌ Nessuna offerta ricevuta."

        if auction.get("photo"):
            await update.message.reply_photo(photo=auction["photo"], caption=msg)
        else:
            await update.message.reply_text(msg)


# ===== /SHOP =====
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_auction_timeout()
    active_auctions = [(aid, a) for aid, a in auctions.items() if a["active"]]

    if not active_auctions:
        await update.message.reply_text("🛍️ Nessun oggetto in vendita")
        return

    msg = "🛍️ OGGETTI IN VENDITA\n\n"
    for aid, a in active_auctions:
        price = f"{a['price']}€" if a["price"] > 0 else "Nessuna offerta"
        msg += f"ID {aid}\n{a['description']}\nPrezzo: {price}\n\n"

    msg += "✍️ Per offrire: #offerta ID prezzo"
    await update.message.reply_text(msg)


# ===== AVVIO BOT =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
