import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from fastapi import FastAPI, Request, HTTPException
import asyncpg
from payment_verifier import check_payment_on_blockchain

# --- CONFIGURATION ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
VIP_GROUP_ID = os.getenv("VIP_GROUP_ID")
DATABASE_URL = os.getenv("DATABASE_URL")
PRICES = {"ETH": 0.1, "SOL": 0.5}

# --- DATABASE SETUP ---
pool = None
async def get_db_pool():
    global pool
    if pool is None:
        try:
            # FIX: Ensure the asyncpg driver is correctly in the URL (Render compatibility)
            url = DATABASE_URL
            pool = await asyncpg.create_pool(url)
            print("✅ DB Pool Connected")
        except Exception as e:
            print(f"⚠️ DB Pool Error: {e}")
    return pool

# --- UTILITY: User Management ---
async def add_user_to_group(user_id, group_id):
    # This is a placeholder for the actual API call to add a user to the private chat
    # Requires the bot to be an Admin in the private group.
    print(f"SIMULATED: Adding user {user_id} to group {group_id}")
    return True

# --- FINAL CONTENT STRATEGY LOGIC ---
async def send_alert(context, is_vip, message):
    """Sends content, separating Free (Teaser) from VIP (Full Data)."""

    # 1. SEND TO VIP GROUP (Paid Users get all data)
    await context.bot.send_message(
        chat_id=VIP_GROUP_ID,
        text=f"👑 VIP ALERT (Full Data):\n\n{message}",
        parse_mode=ParseMode.MARKDOWN
    )

    # 2. SEND TO FREE CHANNEL (Free users only get teasers/news)
    if not is_vip:
        teaser_message = (
            "🚨 **INSTITUTIONAL FLOW DETECTED**\n\n"
            "The Alpha Hunter has a confirmed signal.\n"
            "🔒 **Access full details in the VIP Group.**\n"
            "[CLICK HERE TO SUBSCRIBE](https://t.me/+D2L5QlgDQPxhMzFk)" # Use your actual invite link
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID, # Public channel ID
            text=teaser_message,
            parse_mode=ParseMode.MARKDOWN
        )

# --- TELEGRAM HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bot Status Check: Demonstrates the bot is running
    await send_alert(context, False, "Bot is awake and ready for command.")

    await update.message.reply_markdown(
        "❄️ **ICEGODS ALPHA HUNTER**\n\n"
        "Unlock the **Institutional Feed**.\n\n"
        "👇 **Select Plan:**",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Pro Access", callback_data="buy_pro")]])
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # (Logic for buy_pro, pay_eth, pay_sol as before)
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

    # CORE LOGIC: Check payment using the dedicated verifier
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


# --- TELEGRAM APP & FASTAPI ---
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("confirm", confirm))
application.add_handler(CallbackQueryHandler(button))

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

    # NOTE: No application.run_polling() needed for Webhook stability
