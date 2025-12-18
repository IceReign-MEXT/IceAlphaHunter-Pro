import os
import asyncio
import aiohttp
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, check_premium, add_subscription
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_ADDRESS")
CHANNEL_ID = os.getenv("ALERT_CHANNEL_ID")

init_db()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- RENDER WEB SERVER (Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Ice Alpha Hunter Pro: Online"
@app.route('/health')
def health(): return "OK", 200
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- ALPHA CONTENT GENERATOR ---
async def get_alpha_gems():
    """Fetches high-conviction trending pairs from DexScreener"""
    url = "https://api.dexscreener.com/token-boosts/latest/v1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return []

# --- KEYBOARDS ---
def main_menu():
    kb = [
        [InlineKeyboardButton(text="🦅 Hunter Alpha (Gems)", callback_data="get_alpha")],
        [InlineKeyboardButton(text="💎 Join VIP Alpha", callback_data="buy_vip")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERS ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome = (
        f"🦅 <b>Ice Alpha Hunter Pro</b> 🦅\n\n"
        "Welcome {message.from_user.first_name}.\n"
        "We scan ETH and Solana for Smart Money moves and 100x Gems.\n\n"
        "👇 <i>Select an option to begin.</i>"
    )
    await message.answer(welcome, parse_mode="HTML", reply_markup=main_menu())

@dp.callback_query(F.data == "get_alpha")
async def alpha_handler(callback: types.CallbackQuery):
    if not check_premium(callback.from_user.id):
        await callback.message.answer("❌ <b>Access Denied</b>\n\nAlpha Hunter Gems are for <b>VIP Members</b> only. Unlock now for 0.005 ETH.", parse_mode="HTML")
        return

    await callback.answer("Scanning Blockchain...")
    gems = await get_alpha_gems()
    msg = "🔥 <b>TOP ALPHA BOOSTS (LIVE):</b>\n\n"
    for g in gems[:5]:
        msg += f"🔹 {g.get('header', 'Token')}\n🔗 <a href='{g.get('url')}'>View Chart</a>\n\n"
    await callback.message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(F.data == "buy_vip")
async def buy_vip(callback: types.CallbackQuery):
    pay_text = (
        "👑 <b>VIP ALPHA MEMBERSHIP</b>\n\n"
        "• Instant DexScreener Alerts\n"
        "• Private 100x Signals Channel\n"
        "• Whale Wallet Tracking\n\n"
        "💰 <b>Price:</b> 0.005 ETH / 7 Days\n"
        f"<b>Wallet:</b> <code>{WALLET}</code>\n\n"
        "<i>Once sent, click 'Verify' or contact Admin.</i>"
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify")]]
    await callback.message.answer(pay_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify")
async def verify_payment(callback: types.CallbackQuery):
    await callback.answer("Verification in progress...", show_alert=True)
    # Manual verify logic for stability or use the blockchain logic from Bot 1
    await bot.send_message(ADMIN_ID, f"🔔 <b>VERIFICATION REQUEST:</b>\nUser: @{callback.from_user.username}\nID: {callback.from_user.id}")
    await callback.message.answer("⏳ <b>Blockchain Syncing...</b>\n\nYour payment is being verified. You will receive a notification once active.")

@dp.callback_query(F.data == "status")
async def status(callback: types.CallbackQuery):
    is_vip = check_premium(callback.from_user.id)
    text = "✅ VIP ACTIVE" if is_vip else "❌ VIP INACTIVE"
    await callback.answer(text, show_alert=True)

# --- STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    logging.info("Alpha Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
