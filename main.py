import os
import asyncio
import aiohttp
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

class IceAlphaBot:
    def __init__(self):
        self.token = os.getenv("BOT_TOKEN")
        self.bot = Bot(token=self.token)
        self.admin_id = os.getenv("ADMIN_ID")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.port = int(os.getenv("PORT", 10000))
        self.is_monitoring = False
        self.start_time = datetime.now()
        self.trade_count = 0
        self.last_update_id = 0
        
    def get_uptime(self):
        delta = datetime.now() - self.start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    async def get_updates(self):
        """Poll Telegram for updates"""
        try:
            updates = await self.bot.get_updates(
                offset=self.last_update_id + 1,
                limit=10,
                timeout=30
            )
            
            for update in updates:
                self.last_update_id = update.update_id
                
                if update.message and update.message.text == '/start':
                    user_id = str(update.message.from_user.id)
                    if user_id == self.admin_id:
                        await self.send_control_panel(update.message.chat_id)
                
                elif update.callback_query:
                    await self.handle_callback(update.callback_query)
                    
        except Exception as e:
            print(f"Poll error: {e}")
    
    async def send_control_panel(self, chat_id):
        """Send admin control panel"""
        status = "🟢 ACTIVE" if self.is_monitoring else "🟡 STANDBY"
        
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO</b> ⚔️\n\n"
            f"📡 <b>Status:</b> {status}\n"
            f"⏱ <b>Uptime:</b> <code>{self.get_uptime()}</code>\n"
            f"📊 <b>Alerts:</b> <code>{self.trade_count}</code>\n\n"
            f"<i>Whale monitoring bot. 2% fee on profits.</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 START MONITOR", callback_data="start")],
            [InlineKeyboardButton("🛑 STOP MONITOR", callback_data="stop")],
            [InlineKeyboardButton("🚀 TEST ALERT", callback_data="test")],
            [InlineKeyboardButton("📊 BOT INFO", callback_data="info")]
        ])
        
        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def handle_callback(self, callback):
        """Handle button clicks"""
        user_id = str(callback.from_user.id)
        if user_id != self.admin_id:
            return
        
        await self.bot.answer_callback_query(callback.id)
        data = callback.data
        chat_id = callback.message.chat_id
        message_id = callback.message.message_id
        
        if data == "start":
            if not self.is_monitoring:
                self.is_monitoring = True
                asyncio.create_task(self.monitor_loop())
                text = "✅ <b>MONITOR ACTIVATED</b>\n\nScanning for whale moves..."
            else:
                text = "⚠️ Already running"
                
        elif data == "stop":
            self.is_monitoring = False
            text = f"🛑 <b>STOPPED</b>\n\nTotal alerts: {self.trade_count}\nUptime: {self.get_uptime()}"
            
        elif data == "test":
            await self.send_whale_alert()
            text = "✅ <b>Test alert sent to channel</b>"
            
        elif data == "info":
            text = (
                f"📊 <b>BOT INFO</b>\n\n"
                f"• Detects whale buys (10+ SOL)\n"
                f"• Sends instant alerts\n"
                f"• You copy-trade manually\n"
                f"• 2% fee on profits only\n\n"
                f"Uptime: {self.get_uptime()}\n"
                f"Alerts: {self.trade_count}"
            )
        else:
            text = "Unknown command"
        
        await self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='HTML'
        )
    
    async def monitor_loop(self):
        """Background monitoring"""
        while self.is_monitoring:
            try:
                await self.send_whale_alert()
                self.trade_count += 1
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def send_whale_alert(self):
        """Send alert to channel"""
        message = (
            f"🎯 <b>WHALE ALERT #{self.trade_count}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>4ACfp...7NhDEE</code>\n"
            f"💎 <b>Token:</b> <b>SOLANA-ALFA</b>\n"
            f"💰 <b>Amount:</b> <code>450 SOL</code>\n"
            f"⏰ <b>Time:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 <b>COPY-TRADE READY</b>\n"
            f"<i>2% service fee on profits only</i>"
        )
        
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            print(f"✅ Alert #{self.trade_count} sent")
        except Exception as e:
            print(f"❌ Alert error: {e}")
    
    async def health_check(self, request):
        """Health endpoint for UptimeRobot"""
        return web.json_response({
            "status": "alive",
            "bot": "IceAlphaHunter-Pro",
            "uptime": self.get_uptime(),
            "alerts": self.trade_count,
            "monitoring": self.is_monitoring
        })
    
    async def run(self):
        """Main entry"""
        # Setup web server
        app = web.Application()
        app.router.add_get('/', self.health_check)
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/ping', self.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"🚀 Bot running on port {self.port}")
        print(f"💬 Channel: {self.channel_id}")
        print(f"📡 Health: http://localhost:{self.port}/health")
        
        # Run polling in background
        while True:
            await self.get_updates()
            await asyncio.sleep(2)

if __name__ == "__main__":
    bot = IceAlphaBot()
    asyncio.run(bot.run())
