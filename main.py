import os
import asyncio
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# THE POWER FEATURE: Live Whale Watcher
async def get_whale_activity():
    # This simulates the Helius High-Speed Parser
    return {
        "token": "SOLANA-ALFA (ALFA)",
        "amount": "450 SOL",
        "mcap": ".2M",
        "whale": "4ACfp...7NhDEE"
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addr = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
    keyboard = [
        [InlineKeyboardButton("⚡ ACTIVATE HIGH-SPEED HUNT", callback_data="activate")],
        [InlineKeyboardButton("📊 WHALE STATS (24h)", callback_data="stats")],
        [InlineKeyboardButton("🛡️ SECURITY VAULT", callback_data="vault")]
    ]
    
    text = (
        "⚔️ <b>ICE ALPHA HUNTER PRO v2.0</b> ⚔️\n\n"
        "👤 <b>Operator:</b> Mex Robert\n"
        "📡 <b>Node:</b> Helius Premium (Active)\n"
        "💳 <b>Hunter Wallet:</b> <code>{addr}</code>\n\n"
        "<i>Ready to front-run the elite whales.</i>"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "activate":
        act = await get_whale_activity()
        alert = (
            "🎯 <b>TARGET ACQUIRED</b>\n"
            f"🐋 Whale: <code>{act['whale']}</code>\n"
            f"💎 Buying: <b>{act['token']}</b>\n"
            f"💰 Volume: <code>{act['amount']}</code>\n"
            f"📈 MCAP: <code>{act['mcap']}</code>\n\n"
            "✅ <b>COPY-TRADE PENDING:</b> Waiting for SOL balance..."
        )
        await query.edit_message_text(alert, parse_mode='HTML')

def main():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("⚔️ WEAPON ARMED AND READY...")
    app.run_polling()

if __name__ == "__main__":
    main()
