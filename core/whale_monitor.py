import asyncio
import json
import os
import websockets
from datetime import datetime
from typing import Dict, List
import aiohttp
from solathon import Client, Keypair, PublicKey
from dotenv import load_dotenv

load_dotenv()

class WhaleMonitor:
    def __init__(self):
        self.helius_key = os.getenv("HELIUS_API_KEY", "1b0094c2-50b9-4c97-a2d6-2c47d4ac2789")
        self.rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_key}"
        self.ws_url = f"wss://mainnet.helius-rpc.com/?api-key={self.helius_key}"
        self.client = Client(self.rpc_url)
        
        # Whale thresholds
        self.min_sol_amount = 5  # Minimum SOL to trigger alert
        self.whale_wallets = set()  # Track known whales
        self.target_tokens = {}  # Token address -> metadata
        
        # Telegram bot for alerts
        self.bot_token = os.getenv("BOT_TOKEN")
        self.channel_id = os.getenv("CHANNEL_ID", "-1003844332949")
        self.admin_id = os.getenv("ADMIN_ID", "8254662446")
        
    async def start_monitoring(self):
        """Start real-time blockchain monitoring"""
        print("🐋 WHALE MONITOR ACTIVATED")
        print(f"📡 Connecting to Helius WSS...")
        
        try:
            async with websockets.connect(self.ws_url) as ws:
                # Subscribe to account changes (large transfers)
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logsSubscribe",
                    "params": [
                        {
                            "mentions": ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"]
                        },
                        {"commitment": "confirmed"}
                    ]
                }
                await ws.send(json.dumps(subscribe_msg))
                
                # Confirm subscription
                response = await ws.recv()
                print(f"✅ Subscribed: {response}")
                
                # Listen for transactions
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)
                        
                        if 'method' in data and data['method'] == 'logsNotification':
                            await self.process_transaction(data['params']['result'])
                            
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
                        continue
                        
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await asyncio.sleep(5)
            await self.start_monitoring()  # Reconnect
    
    async def process_transaction(self, log_data: Dict):
        """Analyze transaction for whale activity"""
        try:
            signature = log_data.get('signature', '')
            logs = log_data.get('logs', [])
            
            # Parse logs for transfer instructions
            for log in logs:
                if 'Transfer' in log or 'Instruction: Transfer' in log:
                    # Extract transfer details
                    await self.analyze_transfer(signature, logs)
                    break
                    
        except Exception as e:
            print(f"Error processing tx: {e}")
    
    async def analyze_transfer(self, signature: str, logs: List[str]):
        """Deep dive into transfer to find whale moves"""
        try:
            # Get transaction details from Helius
            async with aiohttp.ClientSession() as session:
                url = f"https://api.helius.xyz/v0/transactions/?api-key={self.helius_key}"
                payload = {
                    "query": {
                        "accounts": [],
                        "types": ["TRANSFER", "SWAP"]
                    },
                    "options": {
                        "limit": 1
                    }
                }
                
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('transactions'):
                            tx = data['transactions'][0]
                            await self.evaluate_whale_move(tx)
                            
        except Exception as e:
            print(f"Error analyzing transfer: {e}")
    
    async def evaluate_whale_move(self, tx: Dict):
        """Determine if this is a whale move worth copying"""
        try:
            # Extract data
            from_addr = tx.get('from', '')
            to_addr = tx.get('to', '')
            amount = float(tx.get('amount', 0))
            token = tx.get('token', 'SOL')
            
            # Check if sender is a whale (balance check)
            is_whale = await self.check_whale_status(from_addr)
            
            if is_whale and amount >= self.min_sol_amount:
                # Generate signal
                signal = {
                    "type": "WHALE_BUY",
                    "whale": from_addr[:8] + "..." + from_addr[-8:],
                    "token": token,
                    "amount": amount,
                    "tx_hash": tx.get('signature', ''),
                    "timestamp": datetime.now().isoformat(),
                    "copy_recommendation": True
                }
                
                await self.send_alert(signal)
                await self.trigger_copy_trade(token, amount)
                
        except Exception as e:
            print(f"Error evaluating move: {e}")
    
    async def check_whale_status(self, address: str) -> bool:
        """Check if address has whale-level balance"""
        try:
            # Get SOL balance
            balance = self.client.get_balance(address)
            sol_balance = balance / 1e9
            
            # Whale = 1000+ SOL
            if sol_balance >= 1000:
                self.whale_wallets.add(address)
                return True
            return False
            
        except Exception as e:
            return False
    
    async def send_alert(self, signal: Dict):
        """Send Telegram alert to channel"""
        try:
            message = (
                f"🎯 <b>WHALE ALERT DETECTED</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🐋 <b>Whale:</b> <code>{signal['whale']}</code>\n"
                f"💎 <b>Token:</b> <b>{signal['token']}</b>\n"
                f"💰 <b>Amount:</b> <code>{signal['amount']} SOL</code>\n"
                f"⏰ <b>Time:</b> {signal['timestamp']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🤖 <b>COPY-TRADE:</b> <code>EXECUTING...</code>\n"
                f"🔗 <a href='https://solscan.io/tx/{signal['tx_hash']}'>View Transaction</a>"
            )
            
            # Send to Telegram
            telegram_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.channel_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(telegram_url, json=payload) as resp:
                    if resp.status == 200:
                        print(f"✅ Alert sent: {signal['token']}")
                    else:
                        print(f"❌ Failed to send alert: {await resp.text()}")
                        
        except Exception as e:
            print(f"Error sending alert: {e}")
    
    async def trigger_copy_trade(self, token: str, amount: float):
        """Trigger copy-trade execution"""
        # This will be handled by AutoTrader
        print(f"🚀 Copy-trade triggered: {token} @ {amount} SOL")
        # Save to queue for auto-trader to process
        trade_data = {
            "token": token,
            "amount": min(amount * 0.1, 1),  # Copy with 10% of whale amount, max 1 SOL
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Save to file for auto-trader to pick up
        with open('pending_trades.json', 'a') as f:
            json.dump(trade_data, f)
            f.write('\n')

# Run standalone
if __name__ == "__main__":
    monitor = WhaleMonitor()
    asyncio.run(monitor.start_monitoring())

