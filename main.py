import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Simulation Data for the Dev Demo
async def get_whale_activity():
    return {
        "token": "SOLANA-ALFA (ALFA)",
        "amount": "450 SOL",
        "mcap": "$1.2M",
        "whale": "4ACfp...7NhDEE",
        "link": "https://solscan.io/account/4ACfp3L96HDEE"
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only allow the Admin (You) to control the bot
    if str(update.effective_chat.id) != os.getenv("ADMIN_ID"):
        return

    addr = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
    text = (
        "⚔️ <b>ICE ALPHA HUNTER PRO v2.0</b> ⚔️\n\n"
        "👤 <b>Operator:</b> Mex Robert\n"
        "📡 <b>Node:</b> Helius Premium (Active)\n"
        "💳 <b>Wallet:</b> <code>{addr}</code>\n"
        "📢 <b>Channel:</b> <code>-1003844332949</code>\n\n"
        "<i>Ready to broadcast Alpha signals.</i>"
    )
    keyboard = [
        [InlineKeyboardButton("🚀 SEND SIGNAL TO CHANNEL", callback_data="broadcast")],
        [InlineKeyboardButton("💰 REFRESH WALLET", callback_data="refresh")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        act = await get_whale_activity()
        alert = (
            "🎯 <b>TARGET ACQUIRED (LIVE)</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🐋 Whale: <code>{act['whale']}</code>\n"
            f"💎 Token: <b>{act['token']}</b>\n"
            f"💰 Buy: <code>{act['amount']}</code>\n"
            f"📈 MCAP: <code>{act['mcap']}</code>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='{act['link']}'>View on Solscan</a>\n\n"
            "⚡ <b>COPY-TRADE:</b> Ready for execution."
        )
        # Send to Channel
        channel_id = os.getenv("CHANNEL_ID")
        try:
            await context.bot.send_message(chat_id=channel_id, text=alert, parse_mode='HTML', disable_web_page_preview=True)
            await query.edit_message_text(f"✅ <b>SENT!</b> Check channel: {channel_id}", parse_mode='HTML')
        except Exception as e:
            await query.edit_message_text(f"❌ <b>FAILED:</b> {e}", parse_mode='HTML')

def main():
    token = os.getenv("BOT_TOKEN")
    # Extended timeouts to prevent Termux network errors
    app = Application.builder().token(token).read_timeout(60).write_timeout(60).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("⚔️ ENGINE STARTING... Pushing to Channel: -1003844332949")
    app.run_polling()

if __name__ == "__main__":
    main()
