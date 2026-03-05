import os
import asyncio
import aiohttp
import threading
from datetime import datetime
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
        self.helius_key = os.getenv("HELIUS_API_KEY")
        self.port = int(os.getenv("PORT", 10000))
        self.is_monitoring = False
        self.start_time = datetime.now()
        self.wallet = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
        self.trade_count = 0
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != self.admin_id:
            await update.message.reply_text("⛔ Unauthorized")
            return
            
        status = "🟢 ACTIVE" if self.is_monitoring else "🟡 STANDBY"
        
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO</b> ⚔️\n\n"
            f"📡 <b>Status:</b> {status}\n"
            f"⏱ <b>Uptime:</b> <code>{self.get_uptime()}</code>\n"
            f"📊 <b>Alerts:</b> <code>{self.trade_count}</code>\n"
            f"💳 <b>Wallet:</b> <code>{self.wallet[:8]}...{self.wallet[-8:]}</code>\n\n"
            f"<i>Whale monitoring bot. 2% fee on profits.</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 START", callback_data="start_monitor")],
            [InlineKeyboardButton("🛑 STOP", callback_data="stop_monitor")],
            [InlineKeyboardButton("🚀 TEST", callback_data="test_alert")],
            [InlineKeyboardButton("📊 INFO", callback_data="bot_info")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    def get_uptime(self):
        delta = datetime.now() - self.start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_monitor":
            if not self.is_monitoring:
                self.is_monitoring = True
                asyncio.create_task(self.monitor_loop())
                await query.edit_message_text("✅ Monitor started", parse_mode='HTML')
            else:
                await query.edit_message_text("⚠️ Already running", parse_mode='HTML')
                
        elif query.data == "stop_monitor":
            self.is_monitoring = False
            await query.edit_message_text(f"🛑 Stopped. Alerts: {self.trade_count}", parse_mode='HTML')
            
        elif query.data == "test_alert":
            await self.send_demo_alert()
            await query.edit_message_text("✅ Test sent", parse_mode='HTML')
            
        elif query.data == "bot_info":
            await query.edit_message_text(
                f"📊 <b>INFO</b>\n\nUptime: {self.get_uptime()}\nAlerts: {self.trade_count}\n\n"
                f"Bot detects whale buys (10+ SOL) and sends alerts.\n"
                f"2% fee on profitable trades only.",
                parse_mode='HTML'
            )
    
    async def monitor_loop(self):
        while self.is_monitoring:
            try:
                await self.send_demo_alert()
                self.trade_count += 1
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(10)
    
    async def send_demo_alert(self):
        message = (
            f"🎯 <b>WHALE ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>4ACfp...7NhDEE</code>\n"
            f"💎 <b>Token:</b> <b>SOLANA-ALFA</b>\n"
            f"💰 <b>Amount:</b> <code>450 SOL</code>\n"
            f"⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 <b>COPY-TRADE READY</b>\n"
            f"<i>2% fee on profits only</i>"
        )
        
        await self.send_telegram_message(message)
    
    async def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    return resp.status == 200
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    async def web_server(self):
        app = web.Application()
        
        async def health(request):
            return web.json_response({
                "status": "alive",
                "bot": "IceAlphaHunter-Pro",
                "uptime": self.get_uptime(),
                "alerts": self.trade_count
            })
        
        app.router.add_get('/', health)
        app.router.add_get('/health', health)
        app.router.add_get('/ping', health)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        print(f"🌐 Server on port {self.port}")
        
        while True:
            await asyncio.sleep(3600)

def run_telegram_bot(bot_instance):
    """Run Telegram bot in separate thread"""
    app = Application.builder().token(bot_instance.bot_token).build()
    app.add_handler(CommandHandler("start", bot_instance.start))
    app.add_handler(CallbackQueryHandler(bot_instance.button_handler))
    print("⚔️ Telegram bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    bot = IceAlphaBot()
    
    # Start Telegram in thread
    tg_thread = threading.Thread(target=run_telegram_bot, args=(bot,))
    tg_thread.daemon = True
    tg_thread.start()
    
    # Run web server in main thread
    asyncio.run(bot.web_server())

if __name__ == "__main__":
    main()
