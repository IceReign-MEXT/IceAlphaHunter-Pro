import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from fastapi import FastAPI, Request, HTTPException
import asyncpg
from payment_verifier import check_payment_on_blockchain  # CORE MONEY LOGIC

# --- LOAD ENV & CONFIG ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_WALLET = os.getenv("ETH_WALLET")  # Receiving Wallet
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
VIP_GROUP_ID = os.getenv("VIP_GROUP_ID")
FREE_CHANNEL_ID = os.getenv("FREE_CHANNEL_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Subscription Price
PRICES = {"price": 0.1, "name": "Pro Access (0.1 ETH)"}
SUBSCRIPTION_AMOUNT_ETH = 0.1  # Price in ETH

# --- DATABASE POOL ---
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

# --- USER MANAGEMENT (SIMULATED) ---
async def add_user_to_group(user_id, group_id):
    # IN PRODUCTION: use context.bot.approve_chat_join_request or invite link
    print(f"SIMULATED: Adding user {user_id} to group {group_id}")
    return True  # Assume success

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

    # --- VERIFY PAYMENT ---
    verification_result = check_payment_on_blockchain(tx_hash, ETH_WALLET)

    if verification_result['status'] == 'success':
        # --- DATABASE LOG ---
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
        # --- GRANT ACCESS ---
        await add_user_to_group(user_id, VIP_GROUP_ID)
        await update.message.reply_markdown(
            "✅ **PAYMENT VERIFIED.** Access granted for 1 month.\n\n"
            "[JOIN PRIVATE CHAT HERE](https://t.me/+D2L5QlgDQPxhMzFk)"
        )
    else:
        await update.message.reply_text(f"❌ Verification Failed: {verification_result['message']}. Please check the TX hash or wait for confirmations.")

# --- TELEGRAM APP ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("confirm", confirm))
application.add_handler(CallbackQueryHandler(button))

# --- FASTAPI WEBHOOK ---
app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def health_check():
    return {"status": "ok", "app": "HunterPro Webhook"}

@app.on_event("startup")
async def startup_event():
    await get_db_pool()
    await application.initialize()
    await application.start()
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
