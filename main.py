import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from fastapi import FastAPI, Request, HTTPException
import asyncpg
import time
from payment_verifier import check_payment_on_blockchain # CORE MONEY LOGIC

# --- CONFIGURATION & DATABASE (Final, Clean Setup) ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_WALLET = os.getenv("ETH_WALLET") # Receiving Wallet
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
VIP_GROUP_ID = os.getenv("VIP_GROUP_ID") # New Variable for the private chat
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID") # New Variable for the public channel
DATABASE_URL = os.getenv("DATABASE_URL")

# Set the high-value subscription price
PRICES = {"price": 0.1, "name": "Pro Access (0.1 ETH)"}
SUBSCRIPTION_AMOUNT_ETH = 0.1 # This is the price

pool = None
async def get_db_pool():
    global pool
    if pool is None:
        try:
            pool = await asyncpg.create_pool(DATABASE_URL)
            print("✅ DB Pool Connected")
        except Exception as e:
            print(f"⚠️ DB Pool Error: {e}")
    return pool

# --- UTILITY: User Management (Simulated Telegram API Calls) ---
# NOTE: The logic to add/remove users requires a special API key or a bot that is an admin in the group.
async def add_user_to_group(user_id, group_id):
    # IN REALITY: Use context.bot.approve_chat_join_request or another method
    print(f"SIMULATED: Adding user {user_id} to group {group_id}")
    return True # Assume success for now

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(
        "❄️ **ICEGODS ALPHA HUNTER**\n\n"
        "Unlock the **Institutional Feed** with 0.1 ETH.\n\n"
        "👇 **Select Plan:**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Pro Access (0.1 ETH)", callback_data="buy_pro")]])
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if "buy_pro" in q.data:
        # Generate a unique invoice link for the user (Final step for professional systems)
        invoice_link = f"https://payment.link/user={q.from_user.id}&amount={PRICES['price']}"
        await q.message.reply_markdown(
            f"🧾 **INVOICE: Pro Access**\n\n"
            f"💵 **Amount:** {PRICES['price']} ETH\n"
            f"🏦 **Pay ETH:** `{ETH_WALLET}`\n\n"
            f"⚠️ **Reply** `/confirm <TX_HASH>` to activate."
        )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args[0]) != 66 or not context.args[0].startswith("0x"): 
        return await update.message.reply_text("❌ Usage: /confirm 0xHash")

    tx_hash = context.args[0]
    user_id = update.effective_user.id

    await update.message.reply_text("⏳ Verifying payment on the blockchain... This may take 60 seconds.")

    # 1. Automated Verification (Using logic from payment_verifier.py)
    verification_result = check_payment_on_blockchain(tx_hash, ETH_WALLET)

    if verification_result['status'] == 'success':
        # 2. Database Log (Grant 1 month access)
        pool = await get_db_pool()
        if pool:
            await pool.execute("INSERT INTO cp_subscriptions (telegram_id, expires_at) VALUES ($1, NOW() + INTERVAL '1 month') ON CONFLICT (telegram_id) DO UPDATE SET expires_at = subscriptions.expires_at + INTERVAL '1 month'", user_id)

        # 3. Grant Access and Notify
        await add_user_to_group(user_id, VIP_GROUP_ID)
        await update.message.reply_markdown("✅ **PAYMENT VERIFIED.** Access granted for 1 month.\n\n[JOIN PRIVATE CHAT HERE](https://t.me/+D2L5QlgDQPxhMzFk)")
    else:
        await update.message.reply_text(f"❌ Verification Failed: {verification_result['message']}. Please wait for more confirmations or check the hash.")

# --- FASTAPI WEBHOOK SETUP (Stable Architecture) ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("confirm", confirm))
application.add_handler(CallbackQueryHandler(button))

app = FastAPI()

@app.post(f"/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check(): return {"status": "ok", "app": "HunterPro Webhook"}

@app.on_event("startup")
async def startup_event():
    await get_db_pool()
    webhook_url = os.getenv("WEBHOOK_URL") 
    if webhook_url: await application.bot.set_webhook(url=f"{webhook_url}/webhook")
    asyncio.create_task(application.run_polling())
