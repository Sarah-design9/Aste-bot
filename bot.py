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

# Durata asta in secondi (24h = 86400)
AUCTION_DURATION = 24 * 3600

# ===== ADMIN =====
ADMINS = ["tuo_username"]  # sostituisci con i tuoi admin
def is_admin(username: str):
    return username in ADMINS


# ===== /START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT ASTE ATTIVO!\n\n"
        "Comandi:\n"
        "#vendita descrizione prezzo_base (base per asta)\n"
        "#offerta ID prezzo\n"
        "#chiudi ID (solo admin)\n"
        "/shop"
    )


# ===== GESTIONE MESSAGGI =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auction_id_counter

    text = update.message.text or update.message.caption or ""
    text = text.strip()
    user = update.message.from_user.username or update.message.from_user.first_name
    chat_id = update.message.chat_id

    # ---------- VENDITA ----------
    if text.startswith("#vendita"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await update.message.reply_text("❌ Formato corretto: #vendita descrizione prezzo_base")
            return

        description = parts[1]
        try:
            base_price = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ Prezzo base non valido")
            return

        auction_id = auction_id_counter
        auction_id_counter += 1

        photo_file_id = update.message.photo[-1].file_id if update.message.photo else None

        auctions[auction_id] = {
            "description": description,
            "price": 0,
            "winner": None,
            "active": False,  # parte alla prima offerta
            "photo": photo_file_id,
            "base_price": base_price,
            "start_time": None,
            "offerers": {},  # username -> chat_id per notifiche
        }

        msg = f"📣 NUOVO OGGETTO IN VENDITA\nID: {auction_id}\n{description}\nPrezzo base: {base_price}€\n💰 L’asta partirà alla prima offerta"
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

        # ---------- ATTIVA ASTA ALLA PRIMA OFFERTA ----------
        if not auction["active"]:
            if offer < auction["base_price"]:
                await update.message.reply_text(f"❌ Offerta troppo bassa. Prezzo base: {auction['base_price']}€")
                return
            auction["active"] = True
            auction["start_time"] = time.time()
            auction["price"] = offer
            auction["winner"] = user
            auction["offerers"][user] = chat_id
            await update.message.reply_text(f"🏁 ASTA AVVIATA!\nID: {auction_id}\n{user} → {offer}€")
            return

        # ---------- OFFERTA ASTA ATTIVA ----------
        if not auction["active"] or (time.time() - auction["start_time"]) >= AUCTION_DURATION:
            auction["active"] = False
            await update.message.reply_text("❌ Asta chiusa, fuori tempo")
            return

        min_offer = auction["price"] + 1
        if offer < min_offer:
            winner = auction["winner"] or "Nessuno"
            await update.message.reply_text(
                f"❌ OFFERTA RIFIUTATA (min {min_offer}€)\nID: {auction_id}\nPrezzo attuale: {auction['price']}€\nMiglior offerente: {winner}"
            )
            return

        # ---------- NOTIFICA OFFERENTE PRECEDENTE ----------
        prev_winner = auction["winner"]
        if prev_winner and prev_winner != user:
            prev_chat_id = auction["offerers"].get(prev_winner)
            if prev_chat_id:
                try:
                    await context.bot.send_message(
                        chat_id=prev_chat_id,
                        text=f"⚠️ La tua offerta per ID {auction_id} è stata superata da {user} con {offer}€"
                    )
                except:
                    pass  # Ignora se non riesce a inviare privato

        auction["price"] = offer
        auction["winner"] = user
        auction["offerers"][user] = chat_id

        await update.message.reply_text(f"🔥 NUOVA OFFERTA!\nID: {auction_id}\n{user} → {offer}€")

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
    msg = ""
    now = time.time()
    for aid, a in auctions.items():
        if a["active"] and (now - a["start_time"]) >= AUCTION_DURATION:
            a["active"] = False
        status = "⚡ ASTA ATTIVA" if a["active"] else "🛒 IN VENDITA"
        price = f"{a['price']}€" if a["price"] > 0 else f"Base: {a['base_price']}€"
        msg += f"ID {aid} - {a['description']}\nPrezzo: {price}\nStato: {status}\n\n"

    if not msg:
        msg = "🛍️ Nessun oggetto in vendita"
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
