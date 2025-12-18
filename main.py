import os
import asyncio
import aiohttp
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import init_db, check_premium, add_subscription, add_referral, get_user_stats
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_ADDRESS")

init_db()
bot = Bot(token=TOKEN)
dp = Dispatcher()

app = Flask('')
@app.route('/')
def home(): return "Ice Alpha Pro: Viral Engine Active"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# --- KEYBOARDS ---
async def main_menu(user_id):
    ref_count, trial_used = get_user_stats(user_id)
    kb = [
        [InlineKeyboardButton(text="🦅 Hunter Alpha (Gems)", callback_data="get_alpha")],
        [InlineKeyboardButton(text="💎 Join VIP Alpha", callback_data="buy_vip")],
        [InlineKeyboardButton(text="🎁 Refer & Earn Trial", callback_data="refer_info")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- HANDLERS ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Check if user is new and joined via referral link
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id: # Can't refer yourself
            reward = add_referral(referrer_id)
            if reward:
                try:
                    await bot.send_message(referrer_id, "🎁 <b>CONGRATULATIONS!</b>\n\nYou invited 3 friends and earned <b>24 Hours of VIP Alpha Access!</b>", parse_mode="HTML")
                except: pass

    welcome = (
        f"🦅 <b>Ice Alpha Hunter Pro</b> 🦅\n\n"
        f"Welcome <b>{message.from_user.first_name}</b>.\n"
        "Start finding 100x gems or refer friends to unlock VIP for free!"
    )
    await message.answer(welcome, parse_mode="HTML", reply_markup=await main_menu(user_id))

@dp.callback_query(F.data == "refer_info")
async def refer_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_count, trial_used = get_user_stats(user_id)

    status_msg = "✅ Trial Used" if trial_used else f"⏳ {ref_count}/3 Friends Invited"

    msg = (
        "🎁 <b>ICE REFERRAL PROGRAM</b>\n\n"
        "Invite 3 friends to the bot and get <b>24 Hours of VIP Alpha Access</b> for free!\n\n"
        f"📊 <b>Your Progress:</b> {status_msg}\n"
        f"🔗 <b>Your Link:</b> <code>{ref_link}</code>\n\n"
        "<i>Share this link in groups and to friends. Once 3 people join, your VIP starts instantly!</i>"
    )
    await callback.message.answer(msg, parse_mode="HTML")

@dp.callback_query(F.data == "get_alpha")
async def alpha_handler(callback: types.CallbackQuery):
    if not check_premium(callback.from_user.id):
        await callback.message.answer("❌ <b>Access Denied</b>\n\nAlpha Gems are for <b>VIP Members</b> only.\n\n👉 <i>Pay 0.005 ETH or refer 3 friends to unlock!</i>", parse_mode="HTML")
        return
    # ... (rest of the Alpha fetching logic remains the same)
    await callback.answer("Scanning Blockchain...")
    await callback.message.answer("🔥 <b>ALPHA ACCESS GRANTED:</b>\n\n[Displaying Live Gems...]")

# (Include the rest of your handlers for buy_vip and status here)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
