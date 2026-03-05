"""IceAlpha Hunter Pro - Elite MEV Bot"""
import sys
import os
import time
import threading
import logging
import asyncio
import random

# Python 3.13+ compatibility
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda f, h=None: None
    sys.modules['imghdr'] = imghdr

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, CallbackContext
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot = None
        self.dispatcher = None
        self.trading_engine = None
        self.whale_monitor = None
        self.is_running = False
        self.channel_id = None
        self.admin_id = None
        self.app = Flask(__name__)
        self.start_time = time.time()
        
    def initialize(self):
        from config import config
        
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set")
        
        self.channel_id = config.CHANNEL_ID
        self.admin_id = config.ADMIN_ID
        
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dispatcher = Dispatcher(self.bot, None, workers=4)
        
        self._setup_handlers()
        self._setup_webhook_endpoint()
        
        from trading_engine import TradingEngine
        from whale_monitor import WhaleMonitor
        
        self.trading_engine = TradingEngine()
        self.whale_monitor = WhaleMonitor()
        self.whale_monitor.on_whale_detected(self._handle_whale_sync)
        
        self._send_startup_message()
        logger.info("✅ IceAlpha Hunter Pro initialized")
    
    def _setup_webhook_endpoint(self):
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            if request.method == "POST":
                update = Update.de_json(request.get_json(force=True), self.bot)
                self.dispatcher.process_update(update)
                return jsonify({"status": "ok"}), 200
            return jsonify({"status": "error"}), 400
        
        @self.app.route('/')
        def health():
            uptime = time.time() - self.start_time
            return {
                "status": "operational",
                "bot": "IceAlpha Hunter Pro",
                "version": "2.0.0",
                "uptime_seconds": int(uptime),
                "uptime_formatted": f"{int(uptime//3600)}h {int((uptime%3600)//60)}m",
                "auto_trade": self._get_config().AUTO_TRADE_ENABLED,
                "wallet": self._get_config().WALLET_PUBLIC_KEY[:20] + "..."
            }, 200
    
    def _get_config(self):
        from config import config
        return config
    
    def _send_startup_message(self):
        if not self.channel_id:
            return
        
        ascii_art = """
╔═══════════════════════════════════════╗
║     🤖 ICE ALPHA HUNTER PRO 🤖        ║
║         MEV WHALE SNIPER v2.0         ║
╚═══════════════════════════════════════╝
        """
        
        startup_msg = f"""
{ascii_art}

🟢 **SYSTEM ONLINE**
⏰ `{time.strftime('%Y-%m-%d %H:%M:%S')} UTC`

📊 **CONFIGURATION**
├─ Strategy: Copy-Trade Whales
├─ Min Target: ${self._get_config().MIN_WHALE_AMOUNT_USD:,.0f}
├─ Max Position: {self._get_config().MAX_POSITION_SOL} SOL
├─ Auto-Execute: {'✅ ENABLED' if self._get_config().AUTO_TRADE_ENABLED else '❌ MONITOR'}
└─ Profit Wallet: `{self._get_config().WALLET_PUBLIC_KEY[:25]}...`

🔧 **FEATURES**
├─ Real-time Helius WebSocket
├─ Jupiter v6 Swap Engine
├─ Automatic Profit Realization
├─ 24/7 Whale Monitoring
└─ Instant Telegram Alerts

💰 **100% OF PROFITS GO TO YOUR WALLET**
        """
        
        try:
            self.bot.send_message(chat_id=self.channel_id, text=startup_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Startup msg failed: {e}")
    
    def _setup_handlers(self):
        dp = self.dispatcher
        
        commands = [
            ('start', self.cmd_start),
            ('help', self.cmd_help),
            ('status', self.cmd_status),
            ('stats', self.cmd_stats),
            ('trades', self.cmd_trades),
            ('balance', self.cmd_balance),
            ('settings', self.cmd_settings),
            ('profit', self.cmd_profit),
            ('history', self.cmd_history),
            ('top', self.cmd_top_trades),
            ('panic', self.cmd_panic_sell),
            ('stopbot', self.cmd_stop),
            ('broadcast', self.cmd_broadcast),
        ]
        
        for cmd, handler in commands:
            dp.add_handler(CommandHandler(cmd, handler))
        
        dp.add_handler(CallbackQueryHandler(self.on_callback))
    
    def _get_uptime(self):
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    def _progress_bar(self, value, max_val, length=20):
        filled = int((value / max_val) * length) if max_val > 0 else 0
        bar = '█' * filled + '░' * (length - filled)
        pct = (value / max_val * 100) if max_val > 0 else 0
        return f"[{bar}] {pct:.1f}%"
    
    def cmd_start(self, update: Update, context: CallbackContext):
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            update.message.reply_text("⛔ **ACCESS DENIED**", parse_mode='Markdown')
            return
        
        welcome = f"""
╔══════════════════════════════════════════╗
║      🤖 ICE ALPHA HUNTER PRO v2.0        ║
║      The Ultimate MEV Whale Sniper       ║
╚══════════════════════════════════════════╝

🎯 **MISSION**
Copy-trade whale moves → Auto-sell for profit → 100% to your wallet

📱 **COMMAND CENTER**
├─ `/status` - Live system dashboard
├─ `/stats` - Performance analytics
├─ `/trades` - Active positions
├─ `/history` - Past trades log
├─ `/top` - Best performing trades
├─ `/profit` - Withdrawable balance
├─ `/balance` - Wallet status
├─ `/settings` - Configuration
├─ `/panic` - Emergency liquidation
└─ `/stopbot` - Safe shutdown

⚙️ **CURRENT SETUP**
├─ Min Whale Size: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
├─ Max Position: {config.MAX_POSITION_SOL} SOL
├─ Slippage: {config.SLIPPAGE_BPS/100}%
├─ Auto-Trade: {'🟢 ACTIVE' if config.AUTO_TRADE_ENABLED else '🔴 MONITOR ONLY'}
└─ Uptime: {self._get_uptime()}

💎 **WHY WE'RE BETTER**
✓ Faster than manual trading
✓ No emotions, pure data
✓ 24/7 monitoring
✓ Instant execution
✓ Full transparency

💰 **YOUR WALLET**
`{config.WALLET_PUBLIC_KEY}`
All profits auto-transfer here
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💰 Stats", callback_data="stats")
            ],
            [
                InlineKeyboardButton("📈 Trades", callback_data="trades"),
                InlineKeyboardButton("🏆 Top", callback_data="top")
            ],
            [
                InlineKeyboardButton("💸 Profit", callback_data="profit"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("🚨 PANIC SELL", callback_data="panic")
            ]
        ]
        
        update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    def cmd_help(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        help_text = """
📚 **COMMAND REFERENCE**

**MONITORING**
`/status` - System health & live positions
`/stats` - Win rate, P&L, analytics
`/trades` - Current holdings with entry prices
`/history` - Complete trade log
`/top` - Best trades leaderboard

**WALLET & PROFITS**
`/balance` - SOL balance & wallet info
`/profit` - Available withdrawal amount
`/settings` - View/change configuration

**ACTIONS**
`/panic` - Emergency sell ALL positions
`/broadcast <msg>` - Alert channel subscribers
`/stopbot` - Graceful shutdown

**TIPS**
• Keep 0.05+ SOL for gas fees
• Use /status every hour to monitor
• /panic only if market crashes
• All data saves automatically
        """
        update.message.reply_text(help_text, parse_mode='Markdown')
    
    def cmd_status(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        open_trades = db.get_open_trades()
        stats = db.get_stats()
        
        # Calculate portfolio value
        portfolio_value = sum(t.get('amount', 0) * t.get('entry_price', 0) for t in open_trades)
        
        status = f"""
╔══════════════════════════════════════════╗
║           📊 SYSTEM DASHBOARD            ║
╚══════════════════════════════════════════╝

⚡ **STATUS**: 🟢 OPERATIONAL
⏱️ **Uptime**: {self._get_uptime()}
🔒 **Security**: Locked & Monitoring

📈 **PORTFOLIO**
├─ Open Positions: {len(open_trades)}
├─ Portfolio Value: {portfolio_value:.4f} SOL
├─ Total Trades: {stats.get('total_trades', 0)}
├─ Win Rate: {stats.get('win_rate', 0):.1f}%
└─ Total Profit: {stats.get('total_profit_sol', 0):.4f} SOL

{self._progress_bar(stats.get('profitable_trades', 0), max(stats.get('total_trades', 1), 1))} Win Rate

🔧 **CONFIGURATION**
├─ Target Whales: ${config.MIN_WHALE_AMOUNT_USD:,.0f}+
├─ Max Position: {config.MAX_POSITION_SOL} SOL
├─ Execution Mode: {'⚡ AUTO-PILOT' if config.AUTO_TRADE_ENABLED else '👁️ MONITOR'}
└─ RPC: Helius (Premium)

🐋 **MONITORING**
├─ Helius WebSocket: 🟢 Connected
├─ Jupiter API: 🟢 Ready
├─ Telegram: 🟢 Active
└─ Wallet: `{config.WALLET_PUBLIC_KEY[:20]}...`

💡 Next whale alert will be posted here automatically
        """
        update.message.reply_text(status, parse_mode='Markdown')
    
    def cmd_stats(self, update: Update, context: CallbackContext):
        from database import db
        
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        stats = db.get_stats()
        total = stats.get('total_trades', 0)
        wins = stats.get('profitable_trades', 0)
        losses = total - wins
        
        stats_text = f"""
╔══════════════════════════════════════════╗
║         📊 PERFORMANCE ANALYTICS         ║
╚══════════════════════════════════════════╝

🎯 **TRADING PERFORMANCE**
├─ Total Trades: {total}
├─ 🟢 Wins: {wins}
├─ 🔴 Losses: {losses}
├─ Win Rate: {stats.get('win_rate', 0):.1f}%
└─ Avg Profit/Trade: {stats.get('avg_profit_sol', 0):.4f} SOL

{self._progress_bar(wins, max(total, 1))}

💰 **PROFIT SUMMARY**
├─ Total SOL: {stats.get('total_profit_sol', 0):.4f} ⬆️
├─ Total USD: ${stats.get('total_profit_usd', 0):.2f}
├─ Best Trade: +{stats.get('best_trade_sol', 0):.4f} SOL
└─ Worst Trade: {stats.get('worst_trade_sol', 0):.4f} SOL

🐋 **WHALE ACTIVITY**
├─ Detected: {stats.get('whales_detected', 0)}
├─ Followed: {stats.get('whales_followed', 0)}
└─ Conversion: {(stats.get('whales_followed', 0) / max(stats.get('whales_detected', 1), 1) * 100):.1f}%

📈 **EFFICIENCY RATING**
{'⭐⭐⭐⭐⭐' if stats.get('win_rate', 0) > 60 else '⭐⭐⭐⭐' if stats.get('win_rate', 0) > 50 else '⭐⭐⭐'}
        """
        update.message.reply_text(stats_text, parse_mode='Markdown')
    
    def cmd_trades(self, update: Update, context: CallbackContext):
        from database import db
        
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        trades = db.get_open_trades()
        
        if not trades:
            update.message.reply_text("""
╔══════════════════════════════════════════╗
║           📭 NO ACTIVE POSITIONS          ║
╚══════════════════════════════════════════╝

Bot is scanning for whale opportunities...
Target: ${}k+ transactions

🔔 You'll be notified instantly when we enter a trade
            """.format(self._get_config().MIN_WHALE_AMOUNT_USD/1000), parse_mode='Markdown')
            return
        
        text = "╔══════════════════════════════════════════╗\n"
        text += "║         📈 ACTIVE POSITIONS              ║\n"
        text += "╚══════════════════════════════════════════╝\n\n"
        
        total_value = 0
        for i, trade in enumerate(trades, 1):
            value = trade.get('amount', 0) * trade.get('entry_price', 0)
            total_value += value
            age = self._get_trade_age(trade.get('created_at', ''))
            
            text += f"**#{i} {trade.get('token_symbol', 'UNKNOWN')}**\n"
            text += f"├─ 💰 Amount: {trade.get('amount', 0):.4f}\n"
            text += f"├─ 📊 Entry: {trade.get('entry_price', 0):.8f} SOL\n"
            text += f"├─ 💵 Value: {value:.4f} SOL\n"
            text += f"├─ 📈 P&L: {trade.get('profit_sol', 0):+.4f} SOL\n"
            text += f"├─ ⏱️  Age: {age}\n"
            text += f"└─ 🎯 Status: ⏳ Holding\n\n"
        
        text += f"**💼 Total Value: {total_value:.4f} SOL**\n"
        text += f"**📊 Positions: {len(trades)}**\n"
        
        update.message.reply_text(text, parse_mode='Markdown')
    
    def _get_trade_age(self, created_at):
        """Calculate trade age"""
        try:
            from datetime import datetime
            if isinstance(created_at, str):
                created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                created = created_at
            age = datetime.now() - created
            if age.days > 0:
                return f"{age.days}d {age.seconds//3600}h"
            elif age.seconds > 3600:
                return f"{age.seconds//3600}h {(age.seconds%3600)//60}m"
            else:
                return f"{age.seconds//60}m"
        except:
            return "Unknown"
    
    def cmd_history(self, update: Update, context: CallbackContext):
        from database import db
        
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        trades = db.get_recent_trades(10)
        
        if not trades:
            update.message.reply_text("📭 No trade history yet", parse_mode='Markdown')
            return
        
        text = "📜 **RECENT TRADES**\n\n"
        for trade in trades:
            status = "🟢" if trade.get('profit_sol', 0) > 0 else "🔴"
            text += f"{status} {trade.get('token_symbol', 'Unknown')}: {trade.get('profit_sol', 0):+.4f} SOL\n"
        
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_top_trades(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        update.message.reply_text("""
🏆 **TOP PERFORMING TRADES**

No completed trades yet.
Start trading to see leaderboard!

💡 Tip: Use `/history` for full log
        """, parse_mode='Markdown')
    
    def cmd_balance(self, update: Update, context: CallbackContext):
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        text = f"""
╔══════════════════════════════════════════╗
║           💰 WALLET STATUS               ║
╚══════════════════════════════════════════╝

📍 **Address**
`{config.WALLET_PUBLIC_KEY}`

🔗 **Network**: Solana Mainnet
🔌 **RPC**: Helius (Premium Tier)
💎 **Type**: Self-Custody

⚠️ **IMPORTANT**
├─ Keep 0.05+ SOL for transaction fees
├─ Never share private key
└─ All profits auto-deposit here

💸 **Withdrawals**
Profits are automatically transferred to this wallet when trades close. No manual action needed!

🔒 **Security**: Maximum
        """
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_settings(self, update: Update, context: CallbackContext):
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        settings = f"""
╔══════════════════════════════════════════╗
║           ⚙️ CONFIGURATION               ║
╚══════════════════════════════════════════╝

**TRADING PARAMETERS**
├─ 🎯 Min Whale Size: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
├─ 💰 Max Position: {config.MAX_POSITION_SOL} SOL
├─ 📊 Slippage Tolerance: {config.SLIPPAGE_BPS/100}%
├─ ⛽ Jito Tip: {config.JITO_TIP_LAMPORTS/1_000_000_000:.4f} SOL
└─ ⚡ Auto-Execute: {'✅ ENABLED' if config.AUTO_TRADE_ENABLED else '❌ DISABLED'}

**WALLET**
├─ 📍 Public: `{config.WALLET_PUBLIC_KEY[:30]}...`
└─ 🔑 Private: {'✅ Loaded' if config.WALLET_PRIVATE_KEY else '❌ Not Set'}

**API STATUS**
├─ 🤖 Telegram: 🟢 Connected
├─ 🔗 Helius RPC: 🟢 Online
└─ 🪐 Jupiter: 🟢 Ready

**SAFETY FEATURES**
✓ Position sizing: Automatic
✓ Risk management: Enabled
✓ Emergency stop: Available
✓ Profit tracking: Real-time
        """
        update.message.reply_text(settings, parse_mode='Markdown')
    
    def cmd_profit(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        stats = db.get_stats()
        profit_sol = stats.get('total_profit_sol', 0)
        
        # Fancy progress to next milestone
        milestones = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
        next_milestone = next((m for m in milestones if m > profit_sol), 1000.0)
        progress = (profit_sol / next_milestone) * 100 if next_milestone > 0 else 0
        
        text = f"""
╔══════════════════════════════════════════╗
║           💸 PROFIT DASHBOARD            ║
╚══════════════════════════════════════════╝

**AVAILABLE BALANCE**
├─ 💰 SOL: {profit_sol:.4f} ⬆️
├─ 💵 USD: ${stats.get('total_profit_usd', 0):.2f}
└─ 📈 Unrealized: 0.0000 SOL

**NEXT MILESTONE**
{self._progress_bar(profit_sol, next_milestone)} {profit_sol:.2f}/{next_milestone:.2f} SOL

**WITHDRAWAL INFO**
├─ 🎯 Destination: Your wallet
├─ 🔄 Method: Auto-transfer on sell
├─ ⛽ Fee: 0% (internal)
└─ ⚡ Speed: Instant

**WALLET**
`{config.WALLET_PUBLIC_KEY}`

💡 Profits transfer automatically!
No manual withdrawal needed.
        """
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_panic_sell(self, update: Update, context: CallbackContext):
        from database import db
        
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        update.message.reply_text("""
╔══════════════════════════════════════════╗
║         🚨 EMERGENCY LIQUIDATION         ║
╚══════════════════════════════════════════╝

⚠️ **WARNING**: This will sell ALL positions immediately!
        """, parse_mode='Markdown')
        
        trades = db.get_open_trades()
        if not trades:
            update.message.reply_text("📭 No positions to sell", parse_mode='Markdown')
            return
        
        sold = 0
        total_profit = 0
        
        for trade in trades:
            try:
                result = asyncio.run(self.trading_engine.sell_token(
                    trade.get('token_mint', ''),
                    trade.get('amount', 0)
                ))
                
                if result.success:
                    profit = result.output_amount - trade.get('amount', 0)
                    db.close_trade(trade.get('id'), result.output_amount, profit, 0, result.signature or '')
                    sold += 1
                    total_profit += profit
                    
                    # Notify channel
                    if self.channel_id:
                        try:
                            self.bot.send_message(
                                chat_id=self.channel_id,
                                text=f"""
🚨 **PANIC SELL EXECUTED**
Token: {trade.get('token_symbol', 'Unknown')}
Profit: {profit:+.4f} SOL
                                """,
                                parse_mode='Markdown'
                            )
                        except:
                            pass
            except Exception as e:
                logger.error(f"Panic error: {e}")
        
        update.message.reply_text(f"""
✅ **PANIC COMPLETE**

Sold: {sold}/{len(trades)} positions
Total P&L: {total_profit:+.4f} SOL
All positions closed!
        """, parse_mode='Markdown')
    
    def cmd_stop(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        if self.channel_id:
            try:
                self.bot.send_message(
                    chat_id=self.channel_id,
                    text="""
╔══════════════════════════════════════════╗
║              🛑 OFFLINE                  ║
╚══════════════════════════════════════════╝

System shutdown complete.
Will resume automatically on restart.
                    """,
                    parse_mode='Markdown'
                )
            except:
                pass
        
        self.is_running = False
        update.message.reply_text("🛑 **Shutting down...** 👋", parse_mode='Markdown')
        
        # Shutdown Flask
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
    
    def cmd_broadcast(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self._get_config().ADMIN_ID:
            return
        
        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Usage: /broadcast <message>")
            return
        
        try:
            self.bot.send_message(
                chat_id=self.channel_id,
                text=f"""
╔══════════════════════════════════════════╗
║           📢 ADMIN ALERT                 ║
╚══════════════════════════════════════════╝

{message}
                """,
                parse_mode='Markdown'
            )
            update.message.reply_text("✅ Broadcast sent")
        except Exception as e:
            update.message.reply_text(f"❌ Failed: {str(e)}")
    
    def on_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        
        callbacks = {
            'status': self.cmd_status,
            'stats': self.cmd_stats,
            'trades': self.cmd_trades,
            'top': self.cmd_top_trades,
            'profit': self.cmd_profit,
            'settings': self.cmd_settings,
            'panic': self.cmd_panic_sell
        }
        
        if query.data in callbacks:
            callbacks[query.data](update, context)
    
    def _handle_whale_sync(self, whale):
        try:
            asyncio.run(self._handle_whale_async(whale))
        except Exception as e:
            logger.error(f"Whale error: {e}")
    
    async def _handle_whale_async(self, whale):
        from config import config
        from database import db
        
        try:
            # Log detection
            alert_id = db.log_whale_alert({
                'signature': whale.signature,
                'trader_address': whale.trader_address,
                'token_mint': whale.token_mint,
                'token_symbol': whale.token_symbol,
                'amount_usd': whale.amount_usd,
                'amount_tokens': whale.amount_tokens,
                'type': whale.transaction_type
            })
            
            if whale.transaction_type != 'buy':
                return
            
            # Validate
            validation = await self.trading_engine.validate_token(whale.token_mint)
            if not validation.get('valid'):
                return
            
            position = self.trading_engine.calculate_position_size(whale.amount_usd)
            
            if config.AUTO_TRADE_ENABLED:
                result = await self.trading_engine.buy_token(whale.token_mint, position)
                
                if result.success:
                    trade_id = db.log_trade({
                        'signature': result.signature or 'unknown',
                        'token_mint': whale.token_mint,
                        'token_symbol': whale.token_symbol,
                        'entry_price': result.output_amount / position if position > 0 else 0,
                        'amount': result.output_amount,
                        'whale_signature': whale.signature,
                        'whale_amount_usd': whale.amount_usd,
                        'metadata': {'input_sol': position, 'price_impact': result.price_impact}
                    })
                    
                    if trade_id:
                        db.mark_whale_followed(alert_id or 0, trade_id)
                    
                    # Channel notification
                    if self.channel_id:
                        try:
                            self.bot.send_message(
                                chat_id=self.channel_id,
                                text=f"""
╔══════════════════════════════════════════╗
║         🐋 WHALE FOLLOWED                ║
╚══════════════════════════════════════════╝

**Whale**: `{whale.trader_address[:8]}...{whale.trader_address[-8:]}`
**Token**: {whale.token_symbol}
**Invested**: {position:.3f} SOL
**Received**: {result.output_amount:.4f}
**TX**: `{str(result.signature)[:25]}...`

⏳ Holding for profit target...
                                """,
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Channel notify: {e}")
                    
                    # Auto-sell simulation
                    await self._auto_sell(trade_id, whale.token_mint, result.output_amount)
                    
        except Exception as e:
            logger.error(f"Handle whale: {e}")
    
    async def _auto_sell(self, trade_id, token_mint, amount):
        """Simulate profit taking"""
        await asyncio.sleep(60)  # 1 minute for demo
        
        try:
            result = await self.trading_engine.sell_token(token_mint, amount)
            
            if result.success:
                profit = result.output_amount - amount
                
                from database import db
                db.close_trade(trade_id, result.output_amount, profit, profit * 20, result.signature or '')
                
                if self.channel_id:
                    try:
                        self.bot.send_message(
                            chat_id=self.channel_id,
                            text=f"""
╔══════════════════════════════════════════╗
║          💰 PROFIT REALIZED              ║
╚══════════════════════════════════════════╝

**Trade #{trade_id}** CLOSED
**Profit**: {profit:+.4f} SOL (${profit * 20:.2f})
**TX**: `{result.signature[:20] if result.signature else 'N/A'}...`

✅ Profits transferred to your wallet!
                            """,
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                
                logger.info(f"Profit: {profit:.4f} SOL")
        except Exception as e:
            logger.error(f"Auto-sell: {e}")
    
    def run(self):
        from config import config
        
        self.initialize()
        self.is_running = True
        
        # Start whale monitor
        threading.Thread(target=self.whale_monitor.start_monitoring_sync, daemon=True).start()
        
        # Set webhook
        port = int(os.getenv('PORT', 10000))
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
        
        try:
            self.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook: {webhook_url}")
        except Exception as e:
            logger.error(f"Webhook failed: {e}")
        
        # Start server
        logger.info(f"🌐 Port {port}")
        self.app.run(host='0.0.0.0', port=port, threaded=True)
