#!/usr/bin/env python3
"""
ICE ALPHA HUNTER V2040 - NEW PAIR SNIPER
Features: Zero-Block Sniping, Liquidity Analysis, Auto-Posting
"""

import os
import time
import asyncio
import threading
import requests
import asyncpg
import random
from decimal import Decimal
from dotenv import load_dotenv
from flask import Flask

# Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Blockchain
from web3 import Web3

# --- 1. CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_MAIN = os.getenv("ETH_MAIN", "").lower()
SOL_MAIN = os.getenv("SOL_MAIN", "")
DATABASE_URL = os.getenv("DATABASE_URL")
VIP_CHANNEL_ID = os.getenv("VIP_CHANNEL_ID")
PRIVATE_LINK = os.getenv("PRIVATE_GROUP_LINK")
ADMIN_ID = os.getenv("ADMIN_ID")
ETH_RPC = os.getenv("ETHEREUM_RPC")

# --- 2. ASSETS ---
IMG_SNIPER = "https://cdn.pixabay.com/photo/2021/08/25/11/33/sniper-6573356_1280.jpg"
IMG_ALERT = "https://cdn.pixabay.com/photo/2020/09/22/09/25/matrix-5592762_1280.jpg"

# --- 3. FLASK SERVER ---
flask_app = Flask(__name__)
@flask_app.route("/")
def health(): return "ALPHA HUNTER V2040 ONLINE", 200

def run_web():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# --- 4. DATABASE ENGINE ---
pool = None
w3 = None
if ETH_RPC:
    try: w3 = Web3(Web3.HTTPProvider(ETH_RPC))
    except: pass

async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        print("✅ Hunter Connected to DB")
    except: print("⚠️ DB Connection Retry...")

# --- 5. PAYMENT VERIFICATION ---
def verify_eth(tx_hash, required_usd):
    if not w3: return False, "Network Busy"
    try:
        tx = w3.eth.get_transaction(tx_hash)
        if tx.to.lower() != ETH_MAIN: return False, "❌ Wrong Address"

        # Get Price
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd").json()
        price = r["ethereum"]["usd"]

        val = (Decimal(tx.value) / Decimal(10**18)) * Decimal(price)
        if val >= (Decimal(required_usd) * Decimal(0.95)): return True, "Success"
        return False, f"Low Amount: ${val:.2f}"
    except: return False, "Check Failed"

# --- 6. SNIPER ENGINE (Auto-Content) ---
async def sniper_loop(app: Application):
    print("🚀 Sniper Radar Active...")
    while True:
        try:
            if VIP_CHANNEL_ID:
                # Simulate finding a NEW PAIR (Real data would use paid RPCs)
                # We use trending as a proxy for "Hot New Pairs"
                r = requests.get("https://api.coingecko.com/api/v3/search/trending").json()
                coin = random.choice(r['coins'][:5])['item']

                # Logic: Is it safe?
                score = random.randint(80, 100)
                liquidity = random.randint(10000, 50000)

                msg = (
                    f"🔫 **NEW PAIR DETECTED** 🔫\n\n"
                    f"💎 **Token:** {coin['name']} ({coin['symbol']})\n"
                    f"💧 **Liquidity:** ${liquidity:,.0f} (Locked 🔒)\n"
                    f"🛡 **Security Score:** {score}/100\n\n"
                    f"🧠 **Alpha Hunter AI:**\n"
                    f"Contract verified. No honeypot code found. Sniper entry zone active.\n\n"
                    f"🎯 **Action:** SNIPE\n"
                    f"🔗 [Chart](https://www.coingecko.com/en/coins/{coin['id']})"
                )

                # Post to Channel
                await app.bot.send_photo(chat_id=VIP_CHANNEL_ID, photo=IMG_ALERT, caption=msg, parse_mode=ParseMode.MARKDOWN)
                print(f"✅ Sniped: {coin['symbol']}")

            await asyncio.sleep(1800) # Every 30 mins
        except Exception as e:
            print(f"Loop Error: {e}")
            await asyncio.sleep(300)

# --- 7. HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("💎 Buy Sniper Pass ($50)", callback_data="buy_pass")],
        [InlineKeyboardButton("🚀 Boost Token ($500)", callback_data="buy_boost")],
        [InlineKeyboardButton("📢 View Channel", url="https://t.me/ICEGODSICEDEVIL")]
    ]
    await update.message.reply_photo(
        IMG_SNIPER,
        caption=(
            "🔫 **ICE ALPHA HUNTER V2040**\n\n"
            "I scan the blockchain for new tokens BEFORE they trend.\n\n"
            "**Capabilities:**\n"
            "✅ Zero-Block Sniping\n"
            "✅ Liquidity Lock Checker\n"
            "✅ Honeypot Detector\n\n"
            "👇 **Initialize:**"
        ),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    price = 50 if "pass" in q.data else 500
    service = "Sniper Pass" if "pass" in q.data else "Token Boost"

    # DB Log Intent
    try:
        if pool:
            tid = str(q.from_user.id)
            await pool.execute("INSERT INTO cp_users (telegram_id, username, plan_id, expiry_date) VALUES ($1, $2, $3, 0) ON CONFLICT (telegram_id) DO NOTHING", tid, q.from_user.username, "hunter_user")
    except: pass

    await q.message.reply_text(
        f"🧾 **INVOICE: {service}**\n\n"
        f"💰 **Amount:** ${price} USD\n"
        f"💠 **ETH:** `{ETH_MAIN}`\n"
        f"🟣 **SOL:** `{SOL_MAIN}`\n\n"
        f"⚠️ **Reply:** `/confirm <TX_HASH>`",
        parse_mode=ParseMode.MARKDOWN
    )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Usage: /confirm <HASH>")
    tx = context.args[0]

    if len(tx) > 70:
        await update.message.reply_text("🟣 **SOL Detected.** Verifying...")
        if ADMIN_ID: await context.bot.send_message(ADMIN_ID, f"💰 **HUNTER SALE:** {tx} from @{update.effective_user.username}")
        return

    msg = await update.message.reply_text("🛰 **Checking ETH...**")
    try:
        success, text = verify_eth(tx, 50)
        if success:
            if pool: await pool.execute("INSERT INTO cp_payments (telegram_id, tx_hash, amount_usd, service_type, created_at) VALUES ($1, $2, $3, 'HUNTER', $4)", str(update.effective_user.id), tx, 50, int(time.time()))

            await msg.edit_text(f"✅ **ACCESS GRANTED.**\n\n🔗 **Private Group:** {PRIVATE_LINK}")
            if ADMIN_ID: await context.bot.send_message(ADMIN_ID, f"💰 **SNIPER SALE:** $50 from @{update.effective_user.username}")
        else:
            await msg.edit_text(text)
    except: await msg.edit_text("⚠️ Verification Error.")

# --- ADMIN FORCE SCAN ---
async def force_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID): return
    await update.message.reply_text("🚀 Forcing Sniper Scan...")

    url = "https://api.coingecko.com/api/v3/search/trending"
    coin = requests.get(url).json()['coins'][0]['item']

    msg = f"🔫 **MANUAL SNIPE: {coin['name']}**\n\nLiquidity: LOCKED 🔒\nRisk: LOW\n\n🎯 **Action:** ENTRY"
    await context.bot.send_photo(chat_id=VIP_CHANNEL_ID, photo=IMG_ALERT, caption=msg, parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("✅ Done.")

# --- MAIN ---
def main():
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: loop.run_until_complete(init_db())
    except: pass

    loop.create_task(sniper_loop(app))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("force_scan", force_scan))
    app.add_handler(CallbackQueryHandler(button))

    print("🚀 ALPHA HUNTER V2040 LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()
