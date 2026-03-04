import asyncio
import json
import os
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class WhaleMonitor:
    def __init__(self):
        self.helius_key = os.getenv("HELIUS_API_KEY", "1b0094c2-50b9-4c97-a2d6-2c47d4ac2789")
        self.rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_key}"
        self.bot_token = os.getenv("BOT_TOKEN")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.min_sol_amount = 5
        
    async def fetch_whale_transactions(self):
        """Fetch recent large transactions from Helius"""
        url = f"https://api.helius.xyz/v0/addresses/?api-key={self.helius_key}"
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {
                    "query": {
                        "types": ["TRANSFER", "SWAP"],
                        "minAmount": self.min_sol_amount * 1e9
                    },
                    "options": {"limit": 10}
                }
                
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self.process_transactions(data.get('transactions', []))
            except Exception as e:
                print(f"Error fetching: {e}")
                return []
    
    def process_transactions(self, transactions):
        """Filter and format whale moves"""
        signals = []
        for tx in transactions:
            amount = float(tx.get('amount', 0)) / 1e9
            
            if amount >= self.min_sol_amount:
                signal = {
                    "type": "WHALE_BUY",
                    "whale": tx.get('from', 'Unknown')[:8] + "...",
                    "token": tx.get('token', 'SOL'),
                    "amount": round(amount, 2),
                    "tx_hash": tx.get('signature', ''),
                    "timestamp": datetime.now().isoformat()
                }
                signals.append(signal)
        return signals
    
    async def send_alert(self, signal):
        """Send to Telegram"""
        message = (
            f"🎯 <b>WHALE ALERT</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>{signal['whale']}</code>\n"
            f"💎 <b>Token:</b> <b>{signal['token']}</b>\n"
            f"💰 <b>Amount:</b> <code>{signal['amount']} SOL</code>\n"
            f"⏰ <b>Time:</b> {signal['timestamp'][:19]}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <a href='https://solscan.io/tx/{signal['tx_hash']}'>View Tx</a>"
        )
        
        telegram_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.channel_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(telegram_url, json=payload) as resp:
                return resp.status == 200

if __name__ == "__main__":
    monitor = WhaleMonitor()
    asyncio.run(monitor.fetch_whale_transactions())
