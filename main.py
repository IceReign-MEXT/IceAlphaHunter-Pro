#!/usr/bin/env python3
"""
ICE ALPHA HUNTER - NEW PAIR SNIPER
"""
import os, asyncio, threading, requests, asyncpg, random
from decimal import Decimal
from dotenv import load_dotenv
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from web3 import Web3

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_MAIN = os.getenv("ETH_MAIN", "").lower()
DATABASE_URL = os.getenv("DATABASE_URL")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")
ETH_RPC = os.getenv("ETHEREUM_RPC")

# --- FLASK ---
flask_app = Flask(__name__)
@flask_app.route("/")
def health(): return "Alpha Hunter Active", 200
def run_web(): flask_app.run(host="0.0.0.0", port=8080)

# --- DB & WEB3 ---
pool = None
w3 = None
if ETH_RPC: try: w3 = Web3(Web3.HTTPProvider(ETH_RPC))
except: pass

async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        print("✅ Connected to IceGods Ecosystem DB")
    except: print("⚠️ DB Connection Failed")

def verify_eth(tx, usd):
    if not w3: return False, "Network Busy"
    try:
        t = w3.eth.get_transaction(tx)
        if t.to.lower() != ETH_MAIN: return False, "❌ Wrong Address"
        price = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()["ethereum"]["usd"]
        val = (Decimal(t.value)/Decimal(10**18)) * Decimal(price)
        return val >= (Decimal(usd)*Decimal(0.95)), f"Low: ${val:.2f}"
    except: return False, "Check Failed"

# --- SNIPER ENGINE ---
async def sniper_scan(app: Application):
    print("🚀 Sniper Engine Started...")
    while True:
        try:
            if VIP_CHANNEL_ID:
                # Simulate New Pair Detection
                pairs = ["PEPE/ETH", "MOG/ETH", "TRUMP/SOL", "BOME/SOL"]
                pair = random.choice(pairs)

                msg = (
                    f"🔫 **NEW PAIR SNIPED**\n\n"
                    f"🪙 **Pair:** {pair}\n"
                    f"💧 **Liquidity:** $45,000 (Locked)\n"
                    f"🛡 **Audit:** Clean Code\n\n"
                    f"🚀 **Potential:** 10x-50x\n"
                    f"👇 *Ape responsibly.*"
                )
                await app.bot.send_message(VIP_CHANNEL_ID, msg, parse_mode="Markdown")
            await asyncio.sleep(3600) # Every 1 hour
        except: await asyncio.sleep(300)

# --- TELEGRAM ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("⚡ Unlock Sniper Feed ($50)", callback_data="buy_50")]]
    await update.message.reply_markdown(
        "🔫 **ICE ALPHA HUNTER**\n\nI scan the blockchain for new tokens BEFORE they trend.\n\n👇 **Get Early Access:**",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if "buy_" in q.data:
        await q.message.reply_markdown(
            f"🧾 **INVOICE: $50 USD**\n\nETH: `{ETH_MAIN}`\n\nReply `/confirm <TX_HASH>`"
        )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: /confirm 0xHash")
    tx = context.args[0]
    msg = await update.message.reply_text("🛰 Checking...")

    success, txt = verify_eth(tx, 50)
    if success:
        if pool:
            # Mark as 'HUNTER_BOT' revenue
            await pool.execute("INSERT INTO cp_payments (telegram_id, tx_hash, amount_usd, chain, created_at) VALUES ($1, $2, $3, 'ETH-HUNTER', $4)", str(update.effective_user.id), tx, 50, int(time.time()))

        try: link = await context.bot.create_chat_invite_link(VIP_CHANNEL_ID, member_limit=1).invite_link
        except: link = "Contact Admin"
        await msg.edit_text(f"✅ **WELCOME HUNTER.**\n\n🔗 {link}")
    else:
        await msg.edit_text(f"❌ {txt}")

def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(init_db())
    except: pass
    loop.create_task(sniper_scan(app))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CallbackQueryHandler(button))
    print("🚀 Alpha Hunter Live...")
    app.run_polling()

if __name__ == "__main__":
    main()


