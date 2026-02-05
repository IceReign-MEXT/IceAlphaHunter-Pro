import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from fastapi import FastAPI, Request, HTTPException
import asyncpg
from payment_verifier import check_payment_on_blockchain # CORE MONEY LOGIC

# --- CONFIGURATION & DATABASE (Final, Clean Setup) ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
VIP_GROUP_ID = os.getenv("VIP_GROUP_ID")
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID")
DATABASE_URL = os.getenv("DATABASE_URL")

# Subscription amounts
PRICES = {"ETH": 0.1, "SOL": 0.5}

# DB pool
pool = None
async def get_db_pool():
    global pool
    if pool is None:
        try:
            # FIX 1: Remove redundant driver name. Use URL exactly as set in ENV.
            url = DATABASE_URL
            pool = await asyncpg.create_pool(url)
            print("✅ DB Pool Connected")
        except Exception as e:
            print(f"⚠️ DB Pool Error: {e}")
    return pool

# --- UTILITY: User Management (Simulated Telegram API Calls) ---
async def add_user_to_group(user_id, group_id):
    print(f"SIMULATED: Adding user {user_id} to group {group_id}")
    return True

# --- TELEGRAM HANDLERS (Same as before) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown(
        "❄️ **ICEGODS ALPHA HUNTER**\n\n"
        "Unlock the **Institutional Feed**.\n\n"
        "👇 **Select Plan:**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Pro Access", callback_data="buy_pro")]])
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "buy_pro":
        keyboard = [
            [
                InlineKeyboardButton(f"💎 Pay with ETH ({PRICES['ETH']} ETH)", callback_data="pay_eth"),
                InlineKeyboardButton(f"💎 Pay with SOL ({PRICES['SOL']} SOL)", callback_data="pay_sol")
            ]
        ]
        await q.message.reply_markdown("👇 Choose your payment method:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif q.data == "pay_eth":
        await q.message.reply_markdown(
            f"🧾 **INVOICE: Pro Access (ETH)**\n\n"
            f"💵 Amount: {PRICES['ETH']} ETH\n"
            f"🏦 Pay ETH: `{ETH_WALLET}`\n\n"
            f"⚠️ Reply `/confirm <TX_HASH>` to activate."
        )

    elif q.data == "pay_sol":
        await q.message.reply_markdown(
            f"🧾 **INVOICE: Pro Access (SOL)**\n\n"
            f"💵 Amount: {PRICES['SOL']} SOL\n"
            f"🏦 Pay SOL: `{SOL_WALLET}`\n\n"
            f"⚠️ Reply `/confirm <TX_HASH>` to activate."
        )

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args[0]) < 10:
        return await update.message.reply_text("❌ Usage: /confirm <TX_HASH>")

    tx_hash = context.args[0]
    user_id = update.effective_user.id
    currency = "ETH" if tx_hash.startswith("0x") else "SOL"

    await update.message.reply_text(f"⏳ Verifying {currency} payment on blockchain... This may take 60 seconds.")

    verification_result = check_payment_on_blockchain(tx_hash, currency=currency)

    if verification_result['status'] == 'success':
        pool = await get_db_pool()
        if pool:
            await pool.execute(
                """
                INSERT INTO cp_subscriptions (telegram_id, expires_at)
                VALUES ($1, NOW() + INTERVAL '1 month')
                ON CONFLICT (telegram_id)
                DO UPDATE SET expires_at = cp_subscriptions.expires_at + INTERVAL '1 month'
                """,
                user_id
            )

        await add_user_to_group(user_id, VIP_GROUP_ID)
        await update.message.reply_markdown(
            f"✅ **{currency} PAYMENT VERIFIED.** Access granted for 1 month.\n\n"
            f"[JOIN PRIVATE CHAT HERE](https://t.me/+D2L5QlgDQPxhMzFk)"
        )
    else:
        await update.message.reply_text(f"❌ Verification Failed: {verification_result['message']}")

# --- TELEGRAM APP ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("confirm", confirm))
application.add_handler(CallbackQueryHandler(button))

# --- FASTAPI WEBHOOK SETUP ---
app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update_obj = Update.de_json(data, application.bot)
        await application.update_queue.put(update_obj)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check(): return {"status": "ok", "app": "HunterPro Webhook"}

@app.on_event("startup")
async def startup_event():
    # Initialize DB connection pool
    await get_db_pool()

    # Set Webhook URL
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await application.bot.set_webhook(url=f"{webhook_url}/webhook")
        print(f"WEBHOOK SET TO: {webhook_url}/webhook")

    # FIX 2: Removed application.run_polling() to prevent "RuntimeError: this event loop is already running"
    # Relying solely on the Webhook POST and application.update_queue.put
