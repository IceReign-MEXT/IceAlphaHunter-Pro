"""Automatic announcements for IceAlpha Hunter"""
import time
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AutoAnnouncer:
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.running = False
        self.thread = None
        
    def start(self):
        """Start announcement loop"""
        self.running = True
        self.thread = threading.Thread(target=self._announcement_loop, daemon=True)
        self.thread.start()
        logger.info("✅ Auto-announcer started")
    
    def _announcement_loop(self):
        """Send periodic updates"""
        # Initial welcome
        time.sleep(30)
        self._send_welcome()
        
        counter = 0
        while self.running:
            time.sleep(3600)
            counter += 1
            if counter % 6 == 0:
                self._send_status_update()
    
    def _send_welcome(self):
        if not self.channel_id:
            return
        msg = """
╔══════════════════════════════════════════╗
║     🎯 ICE ALPHA HUNTER IS WATCHING      ║
╚══════════════════════════════════════════╝

👁️ **24/7 Whale Monitoring Active**

I'm scanning Solana for whale transactions $5,000+

When I detect a whale buying, I will:
1️⃣ Analyze token instantly
2️⃣ Calculate safe position size  
3️⃣ Execute copy-trade
4️⃣ Monitor for profit target
5️⃣ Auto-sell & transfer profits

💰 **Your Profits**: 100% to your wallet
⚡ **Speed**: <2 seconds
🛡️ **Safety**: Auto risk management

🔔 Real-time alerts here!

Ready to catch whales... 🐋
        """
        try:
            self.bot.send_message(chat_id=self.channel_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Welcome failed: {e}")
    
    def _send_status_update(self):
        from database import db
        stats = db.get_stats()
        msg = f"""
╔══════════════════════════════════════════╗
║         📊 SYSTEM HEALTH CHECK           ║
╚══════════════════════════════════════════╝

⏱️ **Uptime**: Operating normally
📈 **Stats**:
├─ Trades: {stats.get('total_trades', 0)}
├─ Profit: {stats.get('total_profit_sol', 0):.4f} SOL
└─ Win Rate: {stats.get('win_rate', 0):.1f}%

🐋 **Status**: Scanning...
💡 Use /status for live data
        """
        try:
            self.bot.send_message(chat_id=self.channel_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Status update failed: {e}")
    
    def announce_trade(self, trade_data):
        if not self.channel_id:
            return
        msg = f"""
╔══════════════════════════════════════════╗
║         🚀 NEW TRADE EXECUTED            ║
╚══════════════════════════════════════════╝

🐋 **Whale**: `{trade_data['whale_address'][:8]}...`
💰 **Invested**: {trade_data['amount_sol']:.3f} SOL
🎯 **Token**: {trade_data['token_symbol']}
📊 **Entry**: {trade_data['entry_price']:.8f}
🎫 **TX**: `{trade_data['tx_signature'][:20]}...`

⏳ Holding for profit target...
        """
        try:
            self.bot.send_message(chat_id=self.channel_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Trade announce failed: {e}")
    
    def announce_profit(self, trade_data, profit_sol, profit_usd):
        if not self.channel_id:
            return
        emoji = "🚀" if profit_sol > 0 else "📉"
        msg = f"""
╔══════════════════════════════════════════╗
║        {emoji} TRADE CLOSED {emoji}         ║
╚══════════════════════════════════════════╝

💰 **PROFIT**
├─ Token: {trade_data['token_symbol']}
├─ Profit: {profit_sol:+.4f} SOL
├─ USD: ${profit_usd:.2f}
└─ TX: `{trade_data['exit_tx'][:20]}...`

✅ Transferred to your wallet!
        """
        try:
            self.bot.send_message(chat_id=self.channel_id, text=msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Profit announce failed: {e}")
    
    def stop(self):
        self.running = False
