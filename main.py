import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db, check_premium, add_subscription, add_referral, get_user_stats
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_ADDRESS")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY")
CHANNEL_ID = os.getenv("ALERT_CHANNEL_ID")

# Initialize DB, Bot, and Dispatcher
init_db()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- WEB SERVER (RENDER KEEP-ALIVE) ---
app = Flask('')
@app.route('/')
def home(): return "Ice Alpha Hunter Pro: Engine Online"
@app.route('/health')
def health(): return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- FSM STATES ---
class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- API LOGIC (ALPHA & PAYMENTS) ---

async def get_alpha_gems():
    """Fetches high-volume trending pairs from DexScreener"""
    url = "https://api.dexscreener.com/token-boosts/latest/v1"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except: return []

async def verify_eth_payment(user_wallet, amount_eth):
    """Automatic Blockchain Verification via Etherscan"""
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={WALLET}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('status') == '1':
                    for tx in data['result']:
                        is_sender = tx['from'].lower() == user_wallet.lower()
                        value_eth = float(tx['value']) / 10**18
                        tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                        is_recent = datetime.now() - tx_time < timedelta(hours=24)
                        if is_sender and value_eth >= amount_eth and is_recent:
                            return True
                return False
        except: return False

# --- KEYBOARDS ---
async def main_menu():
    kb = [
        [InlineKeyboardButton(text="🦅 Hunter Alpha (Gems)", callback_data="get_alpha")],
        [InlineKeyboardButton(text="🎁 Refer & Earn Trial", callback_data="refer_info")],
        [InlineKeyboardButton(text="💎 Join VIP Alpha", callback_data="buy_vip")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- COMMAND HANDLERS ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()

    # Handle Referral Logic
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            reward = add_referral(referrer_id)
            if reward:
                try: await bot.send_message(referrer_id, "🎁 <b>MILESTONE REACHED!</b>\nYou invited 3 friends! You now have <b>24 Hours of VIP Access</b>.", parse_mode="HTML")
                except: pass

    welcome = (
        f"🦅 <b>Ice Alpha Hunter Pro</b> 🦅\n\n"
        f"Welcome <b>{message.from_user.first_name}</b>.\n"
        "We track Smart Money and 100x Gems on ETH & Solana.\n\n"
        "💰 <b>Earn:</b> Invite 3 friends for a free 24h VIP trial."
    )
    await message.answer(welcome, parse_mode="HTML", reply_markup=await main_menu())

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    is_vip = check_premium(message.from_user.id)
    text = "✅ <b>VIP ACTIVE</b>" if is_vip else "❌ <b>VIP INACTIVE</b>"
    await message.answer(f"📊 <b>Your Status:</b> {text}", parse_mode="HTML")

@dp.message(Command("refer"))
async def cmd_refer(message: types.Message):
    user_id = message.from_user.id
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={user_id}"
    ref_count, trial_used = get_user_stats(user_id)
    msg = (
        "🎁 <b>ICE REFERRAL PROGRAM</b>\n\n"
        "Invite 3 friends to unlock 24h VIP Alpha Access!\n\n"
        f"📊 <b>Progress:</b> {ref_count}/3 Friends\n"
        f"🔗 <b>Your Link:</b> <code>{ref_link}</code>"
    )
    await message.answer(msg, parse_mode="HTML")

# --- CALLBACK HANDLERS ---

@dp.callback_query(F.data == "get_alpha")
async def alpha_handler(callback: types.CallbackQuery):
    if not check_premium(callback.from_user.id):
        await callback.message.answer("❌ <b>Access Denied</b>\n\nAlpha Gems are for <b>VIP Members</b> only.\n\n👉 <i>Pay 0.005 ETH or refer 3 friends to unlock!</i>", parse_mode="HTML")
        return

    await callback.answer("Scanning Blockchain... ⏳")
    gems = await get_alpha_gems()
    msg = "🔥 <b>LIVE ALPHA TRENDING:</b>\n\n"
    for g in gems[:5]:
        msg += f"🔹 {g.get('header', 'Token')}\n🔗 <a href='{g.get('url')}'>View Chart</a>\n\n"
    await callback.message.answer(msg, parse_mode="HTML", disable_web_page_preview=True)

@dp.callback_query(F.data == "refer_info")
async def refer_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={user_id}"
    ref_count, _ = get_user_stats(user_id)
    msg = (
        "🎁 <b>FREE VIP TRIAL</b>\n\n"
        "Invite 3 friends to get 24 hours of VIP access.\n\n"
        f"📊 <b>Invited:</b> {ref_count}/3\n"
        f"🔗 <b>Link:</b> <code>{ref_link}</code>"
    )
    await callback.message.answer(msg, parse_mode="HTML")

@dp.callback_query(F.data == "buy_vip")
async def buy_vip(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 <b>Wallet Registration</b>\n\nPlease send your <b>ETH Wallet Address</b> below to begin:", parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    wallet = message.text.strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer("❌ Invalid ETH Address. Try again.")
        return
    await state.update_data(user_wallet=wallet)
    msg = (
        "💰 <b>Payment Instructions</b>\n\n"
        f"<b>Amount:</b> <code>0.005</code> ETH\n"
        f"<b>To Address:</b> <code>{WALLET}</code>\n\n"
        "Wait 2 minutes after sending, then click verify."
    )
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")]]
    await message.answer(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")
    await callback.answer("Searching Blockchain... ⏳")

    if await verify_eth_payment(user_wallet, 0.005):
        add_subscription(callback.from_user.id, 168) # 7 Days = 168 Hours
        await callback.message.answer("🎉 <b>Success!</b> VIP Alpha is now active for 7 days.")
        await bot.send_message(ADMIN_ID, f"💰 <b>SALE:</b> 0.005 ETH from @{callback.from_user.username}")
        await state.clear()
    else:
        await callback.message.answer("❌ Payment not found yet. Try again in 2 minutes.")

@dp.callback_query(F.data == "status")
async def status_callback(callback: types.CallbackQuery):
    is_vip = check_premium(callback.from_user.id)
    text = "✅ VIP ACTIVE" if is_vip else "❌ VIP INACTIVE"
    await callback.answer(text, show_alert=True)

# --- MONITORING (THE READ) ---

@dp.channel_post()
async def monitor_channel(message: types.Message):
    log = f"📢 <b>Post in {message.chat.title}:</b>\n\n{message.text or '[Media]'}"
    await bot.send_message(ADMIN_ID, log, parse_mode="HTML")

@dp.chat_member()
async def track_members(chat_member: ChatMemberUpdated):
    user = chat_member.from_user
    new_status = chat_member.new_chat_member.status
    if new_status == "member":
        msg = f"✅ <b>Subscriber Joined:</b> {user.first_name} (@{user.username})"
        await bot.send_message(ADMIN_ID, msg, parse_mode="HTML")

# --- STARTUP ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    logging.info("Bot is starting...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "channel_post", "chat_member"])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
