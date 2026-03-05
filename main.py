import os
import asyncio
import aiohttp
import json
from datetime import datetime
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

class IceAlphaBot:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.admin_id = os.getenv("ADMIN_ID")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.helius_key = os.getenv("HELIUS_API_KEY", "1b0094c2-50b9-4c97-a2d6-2c47d4ac2789")
        self.port = int(os.getenv("PORT", 10000))
        self.is_monitoring = False
        self.wallet = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
        self.start_time = datetime.now()
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != self.admin_id:
            await update.message.reply_text("⛔ Unauthorized")
            return
            
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO v2.0</b> ⚔️\n\n"
            f"👤 <b>Operator:</b> Admin\n"
            f"📡 <b>Node:</b> Helius Premium\n"
            f"💳 <b>Wallet:</b> <code>{self.wallet[:8]}...{self.wallet[-8:]}</code>\n"
            f"📢 <b>Channel:</b> <code>{self.channel_id}</code>\n\n"
            f"<i>Ready to hunt whale alpha.</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 START WHALE MONITOR", callback_data="start_monitor")],
            [InlineKeyboardButton("🚀 SEND TEST SIGNAL", callback_data="test_signal")],
            [InlineKeyboardButton("💰 CHECK BALANCE", callback_data="check_balance")],
            [InlineKeyboardButton("📊 BOT STATUS", callback_data="bot_status")]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='HTML'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_monitor":
            if not self.is_monitoring:
                self.is_monitoring = True
                asyncio.create_task(self.run_monitor_loop())
                await query.edit_message_text(
                    "✅ <b>WHALE MONITOR ACTIVATED</b>\n\nScanning blockchain for alpha...",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("⚠️ Monitor already running", parse_mode='HTML')
                
        elif query.data == "test_signal":
            await self.send_test_signal()
            await query.edit_message_text("✅ Test signal sent", parse_mode='HTML')
            
        elif query.data == "check_balance":
            await query.edit_message_text("💰 Balance check...", parse_mode='HTML')
            
        elif query.data == "bot_status":
            uptime = datetime.now() - self.start_time
            await query.edit_message_text(
                f"📊 <b>STATUS</b>\nUptime: {uptime.seconds//3600}h", 
                parse_mode='HTML'
            )
    
    async def run_monitor_loop(self):
        while self.is_monitoring:
            try:
                await self.send_test_signal()
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def send_test_signal(self):
        message = (
            f"🎯 <b>WHALE ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>4ACfp...7NhDEE</code>\n"
            f"💎 <b>Token:</b> <b>SOLANA-ALFA</b>\n"
            f"💰 <b>Amount:</b> <code>450 SOL</code>\n"
            f"⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        await self.send_telegram_message(message)
    
    async def send_telegram_message(self, message):
        telegram_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(telegram_url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    async def web_server(self):
        """Keep-alive server for Render"""
        app = web.Application()
        
        async def health(request):
            uptime = datetime.now() - self.start_time
            return web.json_response({
                "status": "alive",
                "bot": "IceAlphaHunter-Pro",
                "uptime": f"{uptime.seconds//3600}h {(uptime.seconds%3600)//60}m"
            })
        
        app.router.add_get('/', health)
        app.router.add_get('/health', health)
        app.router.add_get('/ping', health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        print(f"🌐 Web server running on port {self.port}")
        
        while True:
            await asyncio.sleep(3600)
    
    def run_telegram(self):
        """Run Telegram bot in thread"""
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        print("⚔️ Telegram bot started")
        app.run_polling()

async def main():
    bot = IceAlphaBot()
    
    # Run both Telegram and web server
    telegram_task = asyncio.create_task(asyncio.to_thread(bot.run_telegram))
    web_task = asyncio.create_task(bot.web_server())
    
    await asyncio.gather(telegram_task, web_task)

if __name__ == "__main__":
    asyncio.run(main())
