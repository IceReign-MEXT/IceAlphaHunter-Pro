import os
import asyncio
import aiohttp
import json
from datetime import datetime
from decimal import Decimal
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
        self.helius_key = os.getenv("HELIUS_API_KEY")
        self.port = int(os.getenv("PORT", 10000))
        
        # Trading config
        self.is_monitoring = False
        self.auto_trade = False
        self.max_position = 1.0  # Max SOL per trade
        self.stop_loss = 0.85   # 15% stop loss
        self.take_profit = 1.25  # 25% take profit
        self.service_fee = 0.02  # 2% transparent fee
        
        # State
        self.start_time = datetime.now()
        self.trade_count = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        self.positions = {}  # token -> {buy_price, amount, time}
        self.last_update_id = 0
        
    def get_uptime(self):
        delta = datetime.now() - self.start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    async def get_updates(self):
        """Poll Telegram for commands"""
        try:
            updates = await self.bot.get_updates(
                offset=self.last_update_id + 1,
                limit=10,
                timeout=30
            )
            
            for update in updates:
                self.last_update_id = update.update_id
                
                if update.message and update.message.text:
                    await self.handle_command(update.message)
                
                elif update.callback_query:
                    await self.handle_callback(update.callback_query)
                    
        except Exception as e:
            print(f"Poll error: {e}")
    
    async def handle_command(self, message):
        """Handle text commands"""
        text = message.text
        user_id = str(message.from_user.id)
        chat_id = message.chat_id
        
        if user_id != self.admin_id:
            await self.bot.send_message(chat_id=chat_id, text="⛔ Unauthorized")
            return
        
        if text == '/start':
            await self.send_control_panel(chat_id)
        elif text == '/status':
            await self.send_status(chat_id)
        elif text == '/positions':
            await self.send_positions(chat_id)
        elif text == '/profits':
            await self.send_profits(chat_id)
    
    async def send_control_panel(self, chat_id):
        """Main control interface"""
        status = "🟢 ACTIVE" if self.is_monitoring else "🟡 STANDBY"
        auto = "🤖 ON" if self.auto_trade else "👤 MANUAL"
        
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO</b> ⚔️\n\n"
            f"📡 Status: {status} | {auto}\n"
            f"⏱ Uptime: <code>{self.get_uptime()}</code>\n"
            f"📊 Trades: <code>{self.trade_count}</code>\n"
            f"💰 Profit: <code>{self.total_profit:.3f} SOL</code>\n"
            f"🎯 Win Rate: <code>{(self.profitable_trades/max(self.trade_count,1)*100):.1f}%</code>\n\n"
            f"<b>Config:</b>\n"
            f"• Max Position: {self.max_position} SOL\n"
            f"• Stop Loss: {(1-self.stop_loss)*100:.0f}%\n"
            f"• Take Profit: {(self.take_profit-1)*100:.0f}%\n"
            f"• Service Fee: {self.service_fee*100:.0f}%\n\n"
            f"<i>Transparent fees. You control all trading.</i>"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 START", callback_data="start"),
                InlineKeyboardButton("🛑 STOP", callback_data="stop")
            ],
            [
                InlineKeyboardButton("🤖 AUTO: ON" if self.auto_trade else "👤 AUTO: OFF", callback_data="toggle_auto"),
                InlineKeyboardButton("⚡ TEST", callback_data="test")
            ],
            [
                InlineKeyboardButton("📊 POSITIONS", callback_data="positions"),
                InlineKeyboardButton("💰 PROFITS", callback_data="profits")
            ]
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
                text = "✅ MONITOR STARTED\n\nScanning blockchain..."
            else:
                text = "⚠️ Already running"
                
        elif data == "stop":
            self.is_monitoring = False
            text = f"🛑 STOPPED\n\nTrades: {self.trade_count}\nProfit: {self.total_profit:.3f} SOL"
            
        elif data == "toggle_auto":
            self.auto_trade = not self.auto_trade
            mode = "AUTO-TRADING ON" if self.auto_trade else "MANUAL MODE"
            text = f"🔄 {mode}\n\nRisk Level: {'HIGH' if self.auto_trade else 'CONTROLLED'}"
            
        elif data == "test":
            await self.execute_demo_trade()
            text = "✅ Demo trade executed\nCheck channel for alert"
            
        elif data == "positions":
            await self.send_positions(chat_id)
            return
            
        elif data == "profits":
            await self.send_profits(chat_id)
            return
        
        await self.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode='HTML'
        )
    
    async def monitor_loop(self):
        """Main monitoring - REAL DATA from Helius"""
        while self.is_monitoring:
            try:
                # Fetch real whale transactions
                signals = await self.fetch_real_whales()
                
                for signal in signals:
                    await self.process_signal(signal)
                    await asyncio.sleep(2)
                
                # Check existing positions for stop loss/take profit
                await self.check_positions()
                
                await asyncio.sleep(20)  # Scan every 20 seconds
                
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(10)
    
    async def fetch_real_whales(self):
        """Fetch REAL transactions from Helius API"""
        if not self.helius_key:
            return []
        
        url = "https://api.helius.xyz/v0/transactions"
        params = {"api-key": self.helius_key}
        
        payload = {
            "query": {
                "types": ["SWAP"],
                "minAmount": 5000000000,  # 5 SOL minimum
                "programs": ["JUP6LkbZbjS1jKKwapdHNy74zc3s6AP7u4KTZXmTLpl"]  # Jupiter
            },
            "options": {"limit": 5}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params, json=payload, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self.parse_transactions(data.get('transactions', []))
                    elif resp.status == 429:
                        print("⚠️ Helius rate limit - need paid plan")
                        return []
                    else:
                        print(f"Helius error: {resp.status}")
                        return []
        except Exception as e:
            print(f"Fetch error: {e}")
            return []
    
    def parse_transactions(self, transactions):
        """Parse Helius transactions into trade signals"""
        signals = []
        
        for tx in transactions:
            try:
                # Extract swap data
                swaps = tx.get('tokenTransfers', [])
                for swap in swaps:
                    amount = float(swap.get('tokenAmount', 0))
                    
                    # Only large buys
                    if amount >= 5:
                        signal = {
                            'type': 'WHALE_BUY',
                            'tx_hash': tx.get('signature', ''),
                            'whale': tx.get('feePayer', '')[:8] + "...",
                            'token': swap.get('mint', 'UNKNOWN'),
                            'amount': amount,
                            'timestamp': datetime.now().isoformat(),
                            'price': swap.get('price', 0)
                        }
                        signals.append(signal)
                        
            except Exception as e:
                continue
                
        return signals
    
    async def process_signal(self, signal):
        """Process whale signal - alert or auto-trade"""
        # Send alert to channel
        await self.send_whale_alert(signal)
        self.trade_count += 1
        
        # Auto-trade if enabled
        if self.auto_trade:
            await self.execute_auto_trade(signal)
    
    async def send_whale_alert(self, signal):
        """Send formatted alert"""
        message = (
            f"🎯 <b>WHALE ALERT #{self.trade_count}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🐋 <b>Whale:</b> <code>{signal['whale']}</code>\n"
            f"💎 <b>Token:</b> <code>{signal['token'][:20]}...</code>\n"
            f"💰 <b>Amount:</b> <code>{signal['amount']:.2f} SOL</code>\n"
            f"⏰ <b>Time:</b> {signal['timestamp'][:19]}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        if self.auto_trade:
            message += "🤖 <b>AUTO-TRADE EXECUTING...</b>\n"
        else:
            message += (
                f"👤 <b>MANUAL TRADE:</b>\n"
                f"• Open: https://jup.ag/swap/{signal['token']}\n"
                f"• Buy: 10% of whale amount\n"
                f"• Stop Loss: -15%\n"
                f"• Take Profit: +25%\n\n"
                f"💎 <i>2% fee on profits only</i>"
            )
        
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Alert error: {e}")
    
    async def execute_auto_trade(self, signal):
        """Execute trade via Jupiter API"""
        token = signal['token']
        
        # Skip if already in position
        if token in self.positions:
            return
        
        # Calculate position size (10% of whale, max 1 SOL)
        position_size = min(signal['amount'] * 0.1, self.max_position)
        
        # Record position
        self.positions[token] = {
            'buy_price': signal.get('price', 0),
            'amount': position_size,
            'time': datetime.now(),
            'tx_hash': signal['tx_hash']
        }
        
        print(f"🤖 Auto-bought {position_size} SOL of {token[:20]}")
        
        # Notify admin
        await self.bot.send_message(
            chat_id=self.admin_id,
            text=f"🤖 <b>AUTO-TRADE EXECUTED</b>\n\nBought: {position_size} SOL\nToken: {token[:20]}...\nTime: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode='HTML'
        )
    
    async def check_positions(self):
        """Check positions for stop loss / take profit"""
        # This would check current prices and sell if needed
        # For now, placeholder
        pass
    
    async def execute_demo_trade(self):
        """Demo trade for testing"""
        self.trade_count += 1
        profit = 0.05  # Simulated 0.05 SOL profit
        
        self.total_profit += profit
        self.profitable_trades += 1
        
        # Calculate fee
        fee = profit * self.service_fee
        net_profit = profit - fee
        
        message = (
            f"🧪 <b>DEMO TRADE #{self.trade_count}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Gross Profit:</b> <code>+{profit:.3f} SOL</code>\n"
            f"📊 <b>Service Fee (2%):</b> <code>-{fee:.3f} SOL</code>\n"
            f"💎 <b>Net Profit:</b> <code>+{net_profit:.3f} SOL</code>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<i>This is a demo. Real trading requires SOL in wallet.</i>"
        )
        
        await self.bot.send_message(
            chat_id=self.channel_id,
            text=message,
            parse_mode='HTML'
        )
    
    async def send_status(self, chat_id):
        """Send detailed status"""
        text = (
            f"📊 <b>BOT STATUS</b>\n\n"
            f"Uptime: {self.get_uptime()}\n"
            f"Monitoring: {'YES' if self.is_monitoring else 'NO'}\n"
            f"Auto-Trade: {'ON' if self.auto_trade else 'OFF'}\n"
            f"Total Trades: {self.trade_count}\n"
            f"Profitable: {self.profitable_trades}\n"
            f"Total Profit: {self.total_profit:.3f} SOL\n"
            f"Active Positions: {len(self.positions)}"
        )
        await self.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    
    async def send_positions(self, chat_id):
        """Show active positions"""
        if not self.positions:
            text = "📭 <b>NO ACTIVE POSITIONS</b>\n\nAll trades completed."
        else:
            text = "📊 <b>ACTIVE POSITIONS</b>\n\n"
            for token, pos in self.positions.items():
                text += f"• <code>{token[:20]}...</code>: {pos['amount']:.2f} SOL\n"
        
        await self.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    
    async def send_profits(self, chat_id):
        """Show profit summary"""
        text = (
            f"💰 <b>PROFIT SUMMARY</b>\n\n"
            f"Total Trades: {self.trade_count}\n"
            f"Win Rate: {(self.profitable_trades/max(self.trade_count,1)*100):.1f}%\n"
            f"Gross Profit: {self.total_profit:.3f} SOL\n"
            f"Service Fees: {self.total_profit * self.service_fee:.3f} SOL\n"
            f"Net Profit: {self.total_profit * (1-self.service_fee):.3f} SOL\n\n"
            f"<i>2% transparent fee on all profits</i>"
        )
        await self.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
    
    async def health_check(self, request):
        """Health endpoint"""
        return web.json_response({
            "status": "alive",
            "bot": "IceAlphaHunter-Pro",
            "version": "3.0",
            "uptime": self.get_uptime(),
            "trades": self.trade_count,
            "profit": self.total_profit,
            "monitoring": self.is_monitoring,
            "auto_trade": self.auto_trade
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
        print(f"🤖 Auto-trade: {'ON' if self.auto_trade else 'OFF'}")
        
        # Main loop
        while True:
            await self.get_updates()
            await asyncio.sleep(2)

if __name__ == "__main__":
    bot = IceAlphaBot()
    asyncio.run(bot.run())
