import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class WhaleMonitor:
    def __init__(self):
        self.helius_key = os.getenv("HELIUS_API_KEY")
        self.min_amount = 10  # Minimum SOL to alert
        self.last_check = None
        
    async def get_real_whales(self):
        """Fetch real whale transactions from Helius"""
        if not self.helius_key:
            return []
            
        url = f"https://api.helius.xyz/v0/addresses/?api-key={self.helius_key}"
        
        # This requires paid Helius plan for real-time data
        payload = {
            "query": {
                "types": ["TRANSFER", "SWAP"],
                "minAmount": self.min_amount * 1e9
            },
            "options": {"limit": 5}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self.parse_real_data(data)
                    elif resp.status == 429:
                        print("⚠️ Helius rate limit - need paid plan")
                        return []
                    else:
                        print(f"Helius error: {resp.status}")
                        return []
        except Exception as e:
            print(f"Monitor error: {e}")
            return []
    
    def parse_real_data(self, data):
        """Parse Helius response into signals"""
        signals = []
        txs = data.get('transactions', [])
        
        for tx in txs:
            try:
                amount = float(tx.get('amount', 0)) / 1e9
                if amount >= self.min_amount:
                    signal = {
                        'type': 'WHALE_BUY',
                        'whale': tx.get('from', 'Unknown')[:8] + "...",
                        'token': tx.get('token', 'SOL'),
                        'amount': round(amount, 2),
                        'tx_hash': tx.get('signature', '')[:16],
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'real_data': True
                    }
                    signals.append(signal)
            except Exception as e:
                continue
                
        return signals
    
    async def get_demo_signal(self):
        """Demo signal when no real data available"""
        return {
            'type': 'DEMO_ALERT',
            'whale': '4ACfp...7NhDEE',
            'token': 'DEMO-TOKEN',
            'amount': 450.0,
            'tx_hash': 'demo123',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'real_data': False,
            'warning': '⚠️ DEMO MODE - Connect paid Helius for real alerts'
        }
