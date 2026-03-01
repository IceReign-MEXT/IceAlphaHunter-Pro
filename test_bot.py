import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def simulate_whale_hit():
    print("🧪 SIMULATION STARTING...")
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    chat_id = os.getenv("ADMIN_ID")
    
    # This mimics the data the Helius listener would catch
    test_msg = (
        "📊 <b>LIVE WHALE SIGNAL (SIMULATED)</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>Target:</b> <code>4ACfp...7NhDEE</code>\n"
        "💎 <b>Token:</b> $ALFA (AlphaHunter)\n"
        "💰 <b>Buy Amount:</b> 25.5 SOL\n"
        "📈 <b>New MCAP:</b> $850K\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚡ <i>Copy-trade logic: Triggered.</i>\n"
        "🛑 <i>Status: Insufficient SOL for execution.</i>"
    )
    
    try:
        await bot.send_message(chat_id=chat_id, text=test_msg, parse_mode='HTML')
        print("✅ SUCCESS: The bot sent the signal to your Telegram!")
    except Exception as e:
        print(f"❌ ERROR: Could not reach Telegram. Check your BOT_TOKEN. \nDetails: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_whale_hit())
