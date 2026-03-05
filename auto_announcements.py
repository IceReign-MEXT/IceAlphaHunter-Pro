import os
import asyncio
import logging
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class AutoAnnouncer:
    def __init__(self, bot: Bot, channel_id: str):
        self.bot = bot
        self.channel_id = channel_id
        self.running = False
        
    async def start(self):
        """Start periodic announcements"""
        self.running = True
        logger.info("Starting auto-announcer...")
        
        while self.running:
            try:
                await self.send_status_update()
                await asyncio.sleep(3600)  # Every hour
            except Exception as e:
                logger.error(f"Announcer error: {e}")
                await asyncio.sleep(300)
    
    async def send_status_update(self):
        """Send periodic status to channel"""
        msg = f"""
⏰ **Hourly Update** - {datetime.now().strftime('%Y-%m-%d %H:%M')}

🤖 IceAlphaHunter Pro Status: 🟢 ONLINE
📊 Scanning for whale opportunities...
💰 Target: $5,000+ transactions
⚡ Auto-trading: Active

Join the hunt! 👇
"""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send announcement: {e}")
    
    async def send_trade_alert(self, trade_data: dict):
        """Send trade alert to channel"""
        msg = f"""
🚨 **LIVE TRADE ALERT** 🚨

🪙 Token: `{trade_data['token'][:20]}...`
💰 Amount: {trade_data['amount']} SOL
📈 Entry: {trade_data['price']}
🎯 Target: +20%
🛑 Stop: -10%

Copy-trading now! ⚡
"""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send trade alert: {e}")
    
    def stop(self):
        self.running = False
