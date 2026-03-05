import os
import asyncio
import aiohttp
from datetime import datetime
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from aiohttp import web
from core.whale_monitor import WhaleMonitor

load_dotenv()

class IceAlphaBot:
    def __init__(self):
        self.bot_token = os.getenv("BOT_TOKEN")
        self.admin_id = os.getenv("ADMIN_ID")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.helius_key = os.getenv("HELIUS_API_KEY")
        self.port = int(os.getenv("PORT", 10000))
        self.is_monitoring = False
        self.monitor = WhaleMonitor()
        self.start_time = datetime.now()
        self.wallet = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
        self.trade_count = 0
        self.demo_mode = True
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        if user_id != self.admin_id:
            await update.message.reply_text("⛔ Unauthorized Access")
            return
            
        status = "🟢 ACTIVE" if self.is_monitoring else "🟡 STANDBY"
        mode = "LIVE" if not self.demo_mode else "DEMO"
        
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO</b> ⚔️\n\n"
            f"📡 <b>Status:</b> {status}\n"
            f"🎮 <b>Mode:</b> <code>{mode}</code>\n"
            f"⏱ <b>Uptime:</b> <code>{self.get_uptime()}</code>\n"
            f"📊 <b>Alerts:</b> <code>{self.trade_count}</code>\n"
            f"💳 <b>Bot Wallet:</b> <code>{self.wallet[:8]}...{self.wallet[-8:]}</code>\n\n"
            f"<i>Whale monitoring bot with 2% service fee on profits.</i>\n\n"
            f"<b>⚠️ How it works:</b>\n"
            f"1. Bot detects whale buys (10+ SOL)\n"
            f"2. Sends alert to your channel\n"
            f"3. You manually copy the trade\n"
            f"4. 2% fee on profitable trades only"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 START MONITOR", callback_data="start_monitor")],
            [InlineKeyboardButton("🛑 STOP MONITOR", callback_data="stop_monitor")],
            [InlineKeyboardButton("🚀 TEST ALERT", callback_data="test_alert")],
            [InlineKeyboardButton("📊 BOT INFO", callback_data="bot_info")]
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
                mode_text = "LIVE MODE" if not self.demo_mode else "DEMO MODE (Upgrade Helius for real data)"
                await query.edit_message_text(
                    f"✅ <b>MONITOR ACTIVATED</b>\n\n"
                    f"Mode: {mode_text}\n"
                    f"Alerts will be sent to channel every 30 seconds.\n\n"
                    f"<i>Bot is scanning for whale moves...</i>",
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text("⚠️ Monitor already running", parse_mode='HTML')
                
        elif query.data == "stop_monitor":
            self.is_monitoring = False
            await query.edit_message_text(
                f"🛑 <b>MONITOR STOPPED</b>\n\n"
                f"Total alerts: {self.trade_count}\n"
                f"Uptime: {self.get_uptime()}",
                parse_mode='HTML'
            )
            
        elif query.data == "test_alert":
            await self.send_demo_alert()
            await query.edit_message_text("✅ Test alert sent to channel", parse_mode='HTML')
            
        elif query.data == "bot_info":
            info_text = (
                f"📊 <b>BOT INFORMATION</b>\n\n"
                f"<b>How It Works:</b>\n"
                f"• Detects whale transactions (10+ SOL)\n"
                f"• Sends instant Telegram alerts\n"
                f"• You copy-trade manually\n"
                f"• 2% fee on profitable trades only\n\n"
                f"<b>Current Status:</b>\n"
                f"• Uptime: {self.get_uptime()}\n"
                f"• Alerts sent: {self.trade_count}\n"
                f"• Mode: {'LIVE' if not self.demo_mode else 'DEMO'}\n\n"
                f"<b>⚠️ Risk Warning:</b>\n"
                f"Trading carries risk. Past performance does not guarantee future results. "
                f"Only trade with capital you can afford to lose."
            )
            await query.edit_message_text(info_text, parse_mode='HTML')
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                # Try to get real data first
                signals = await self.monitor.get_real_whales()
                
                # If no real data, use demo
                if not signals:
                    signals = [await self.monitor.get_demo_signal()]
                    self.demo_mode = True
                else:
                    self.demo_mode = False
                
                # Send alerts
                for signal in signals:
                    await self.send_alert(signal)
                    self.trade_count += 1
                    await asyncio.sleep(2)
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def send_alert(self, signal):
        """Send formatted alert to channel"""
        is_demo = signal.get('real_data', False) == False
        demo_warning = signal.get('warning', '') if is_demo else ''
        
        emoji = "🟢" if signal['type'] == 'WHALE_BUY' else "🔵"
        type_label = "LIVE WHALE" if not is_demo else "DEMO ALERT"
        
        message = (
            f"{emoji} <b>{type_label}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>{signal['whale']}</code>\n"
            f"💎 <b>Token:</b> <b>{signal['token']}</b>\n"
            f"💰 <b>Amount:</b> <code>{signal['amount']} SOL</code>\n"
            f"📝 <b>Type:</b> {signal['type']}\n"
            f"⏰ <b>Time:</b> {signal['timestamp']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
        
        if is_demo:
            message += f"\n⚠️ <b>{demo_warning}</b>\n"
        else:
            message += (
                f"\n🤖 <b>COPY-TRADE READY</b>\n"
                f"• Open Jupiter or Raydium\n"
                f"• Paste token address\n"
                f"• Buy with 10% of whale amount\n"
                f"• Set stop loss at -15%\n"
                f"• Take profit at +25%\n\n"
                f"💎 <i>2% service fee applies to profits only</i>"
            )
        
        await self.send_telegram_message(message)
    
    async def send_demo_alert(self):
        """Send manual test alert"""
        demo_signal = {
            'type': 'TEST_ALERT',
            'whale': 'TestWhale...1234',
            'token': 'TEST-TOKEN',
            'amount': 100.0,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'real_data': False,
            'warning': 'This is a test alert. Bot is working correctly.'
        }
        await self.send_alert(demo_signal)
        self.trade_count += 1
    
    async def send_telegram_message(self, message):
        """Send message to Telegram channel"""
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
        """Keep-alive server for Render/UptimeRobot"""
        app = web.Application()
        
        async def health(request):
            return web.json_response({
                "status": "alive",
                "bot": "IceAlphaHunter-Pro",
                "version": "2.0",
                "uptime": self.get_uptime(),
                "alerts": self.trade_count,
                "mode": "live" if not self.demo_mode else "demo"
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

def main():
    bot = IceAlphaBot()
    
    # Run Telegram bot in thread
    def run_telegram():
        app = Application.builder().token(bot.bot_token).build()
        app.add_handler(CommandHandler("start", bot.start))
        app.add_handler(CallbackQueryHandler(bot.button_handler))
        print("⚔️ Telegram bot started")
        print(f"📡 Channel: {bot.channel_id}")
        app.run_polling()
    
    telegram_thread = Thread(target=run_telegram)
    telegram_thread.start()
    
    # Run web server
    asyncio.run(bot.web_server())

if __name__ == "__main__":
    main()
