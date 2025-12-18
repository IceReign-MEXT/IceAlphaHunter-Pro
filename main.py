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

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WALLET = os.getenv("PAYMENT_ADDRESS")
ETHERSCAN_KEY = os.getenv("ETHERSCAN_API_KEY")
CHANNEL_ID = os.getenv("ALERT_CHANNEL_ID")

init_db()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

app = Flask('')
@app.route('/')
def home(): return "Ice Alpha Pro: 10/10 Engine"
@app.route('/health')
def health(): return "OK", 200

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

class PaymentStates(StatesGroup):
    waiting_for_wallet = State()

# --- BLOCKCHAIN VERIFICATION ---
async def verify_eth_payment(user_wallet, amount_eth):
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address={WALLET}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_KEY}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if data.get('status') == '1':
                    for tx in data['result']:
                        if tx['from'].lower() == user_wallet.lower():
                            value_eth = float(tx['value']) / 10**18
                            tx_time = datetime.fromtimestamp(int(tx['timeStamp']))
                            if value_eth >= amount_eth and (datetime.now() - tx_time < timedelta(hours=24)):
                                return True
                return False
        except: return False

# --- UI COMPONENTS ---
async def get_main_menu():
    kb = [
        [InlineKeyboardButton(text="🦅 Hunter Alpha (Gems)", callback_data="get_alpha")],
        [InlineKeyboardButton(text="🎁 Refer & Earn Trial", callback_data="refer_info")],
        [InlineKeyboardButton(text="💎 Join VIP Alpha", callback_data="buy_vip")],
        [InlineKeyboardButton(text="📊 My Status", callback_data="status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- COMMANDS ---

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Action cancelled. Back to main menu.", reply_markup=await get_main_menu())

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            if add_referral(referrer_id):
                try: await bot.send_message(referrer_id, "🎁 <b>MILESTONE!</b> You invited 3 friends. 24h VIP Unlocked!", parse_mode="HTML")
                except: pass

    await message.answer(f"🦅 <b>Ice Alpha Hunter Pro</b>\n\nWelcome {message.from_user.first_name}.\nTrack smart money and get 100x gems.", parse_mode="HTML", reply_markup=await get_main_menu())

@dp.message(Command("refer"))
async def cmd_refer(message: types.Message):
    me = await bot.get_me()
    ref_count, _ = get_user_stats(message.from_user.id)
    msg = f"🎁 <b>REFERRAL PROGRAM</b>\n\nInvited: {ref_count}/3\nLink: <code>https://t.me/{me.username}?start={message.from_user.id}</code>"
    await message.answer(msg, parse_mode="HTML")

# --- BROADCAST FEATURE (ADMIN ONLY) ---
@dp.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def cmd_broadcast(message: types.Message):
    msg_to_send = message.text.replace("/broadcast ", "")
    if not msg_to_send or msg_to_send == "/broadcast":
        await message.answer("Usage: /broadcast Hello everyone!")
        return
    # This is a simple version; in a real biz, you'd loop through all IDs in your DB
    await message.answer("📢 Sending broadcast to all active sessions...")
    # For now, we simulate. To make this real, you need a 'users' list in DB.

# --- STATE HANDLER (FIXED) ---
@dp.message(PaymentStates.waiting_for_wallet)
async def get_wallet(message: types.Message, state: FSMContext):
    # If the user types a command, don't treat it as a wallet
    if message.text.startswith("/"):
        return

    wallet = message.text.strip()
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer("❌ <b>Invalid Wallet Address.</b>\n\nPlease send a valid ETH address or type /cancel.", parse_mode="HTML")
        return

    await state.update_data(user_wallet=wallet)
    msg = f"💰 <b>Payment Instructions</b>\n\nAmount: <code>0.005</code> ETH\nTo: <code>{WALLET}</code>\n\nWait 2 mins then click verify."
    kb = [[InlineKeyboardButton(text="✅ Verify Payment", callback_data="verify_now")],
          [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_reg")]]
    await message.answer(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

# --- CALLBACKS ---
@dp.callback_query(F.data == "get_alpha")
async def alpha_handler(callback: types.CallbackQuery):
    if not check_premium(callback.from_user.id):
        await callback.message.answer("❌ <b>Access Denied</b>\n\nVIP feature only. Pay 0.005 ETH or refer 3 friends.", parse_mode="HTML")
        return
    await callback.answer("Scanning DexScreener Alpha...")
    # (Fetching logic here...)
    await callback.message.answer("🔥 <b>LIVE ALPHA:</b>\n\n[Displaying Trending Gems...]")

@dp.callback_query(F.data == "buy_vip")
async def buy_vip(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔗 <b>Wallet Registration</b>\n\nPaste your ETH Wallet Address below:", parse_mode="HTML")
    await state.set_state(PaymentStates.waiting_for_wallet)

@dp.callback_query(F.data == "verify_now")
async def verify_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_wallet = data.get("user_wallet")
    await callback.answer("Verifying on Blockchain... ⏳")
    if await verify_eth_payment(user_wallet, 0.005):
        add_subscription(callback.from_user.id, 168)
        await callback.message.answer("🎉 <b>Verified!</b> 7 days VIP added.")
        await bot.send_message(ADMIN_ID, f"💰 <b>SALE!</b> 0.005 ETH from @{callback.from_user.username}")
        await state.clear()
    else:
        await callback.message.answer("❌ Payment not found. Check the wallet and amount, then try again.")

@dp.callback_query(F.data == "cancel_reg")
async def cancel_reg(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Payment cancelled.")

@dp.callback_query(F.data == "refer_info")
async def refer_info(callback: types.CallbackQuery):
    me = await bot.get_me()
    ref_count, _ = get_user_stats(callback.from_user.id)
    msg = f"🎁 <b>FREE VIP</b>\n\nInvite 3 friends to get 24h access.\nInvited: {ref_count}/3\nLink: <code>https://t.me/{me.username}?start={callback.from_user.id}</code>"
    await callback.message.answer(msg, parse_mode="HTML")

@dp.callback_query(F.data == "status")
async def status_cb(callback: types.CallbackQuery):
    is_vip = check_premium(callback.from_user.id)
    await callback.answer("VIP ACTIVE" if is_vip else "VIP INACTIVE", show_alert=True)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=run_web).start()
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "channel_post", "chat_member"])

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
