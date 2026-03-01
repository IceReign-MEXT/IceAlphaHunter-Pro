import asyncio
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()

async def send_demo():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    chat_id = os.getenv("ADMIN_ID")
    demo_msg = (
        "⚔️ <b>LIVE TRADE DETECTED</b> ⚔️\n\n"
        "🎯 <b>Whale:</b> <code>4ACfp...7NhDEE</code>\n"
        "💎 <b>Token:</b>  (IceGods)\n"
        "💰 <b>Amount:</b> 10 SOL Buy\n\n"
        "✅ <b>Copy-Trade Executed:</b> 0.1 SOL\n"
        "🔗 <a href='https://solscan.io'>View on Solscan</a>"
    )
    await bot.send_message(chat_id=chat_id, text=demo_msg, parse_mode='HTML')
    print("✅ Demo Signal Sent to Telegram!")

if __name__ == "__main__":
    asyncio.run(send_demo())
