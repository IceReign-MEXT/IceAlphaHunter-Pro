import os
import asyncio
from aiohttp import web
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

class WebServer:
    def __init__(self):
        self.port = int(os.getenv("PORT", 10000))
        self.bot_token = os.getenv("BOT_TOKEN")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.start_time = __import__('time').time()
        
    async def health_check(self, request):
        """Endpoint for UptimeRobot to ping"""
        uptime = __import__('time').time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        return web.json_response({
            "status": "alive",
            "bot": "IceAlphaHunter-Pro",
            "version": "2.0",
            "uptime": f"{hours}h {minutes}m",
            "channel": self.channel_id
        })
    
    async def send_test(self, request):
        """Manual trigger to test Telegram"""
        try:
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=self.channel_id,
                text="🤖 <b>Bot Status Check</b>\n\nUptimeRobot ping received. Bot is active.",
                parse_mode='HTML'
            )
            return web.json_response({"status": "message_sent"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start(self):
        app = web.Application()
        app.router.add_get('/', self.health_check)
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/ping', self.health_check)
        app.router.add_get('/test', self.send_test)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        print(f"🌐 Web server running on port {self.port}")
        print(f"📡 Health check: http://0.0.0.0:{self.port}/health")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    server = WebServer()
    asyncio.run(server.start())
