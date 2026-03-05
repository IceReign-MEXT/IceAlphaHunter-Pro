import os
import logging
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from dotenv import load_dotenv
from trading_engine import TradingEngine
from database import Database
from whale_monitor import WhaleMonitor
from profit_manager import ProfitManager
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.channel_id = os.getenv('TELEGRAM_CHANNEL_ID', self.chat_id)
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set!")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID not set!")
            
        self.config = Config()
        self.db = Database()
        self.trading_engine = TradingEngine(self.db)
        self.profit_manager = ProfitManager(self.db)
        self.whale_monitor = WhaleMonitor(self.trading_engine, self.send_alert)
        
        self.application = Application.builder().token(self.token).build()
        self.bot = Bot(token=self.token)
        
        # Track bot start time for uptime
        self.start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        
        self._register_handlers()
        
    def _register_handlers(self):
        """CRITICAL: Register all command handlers"""
        logger.info("Registering command handlers...")
        
        # Core commands
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("trades", self.cmd_trades))
        self.application.add_handler(CommandHandler("history", self.cmd_history))
        self.application.add_handler(CommandHandler("top", self.cmd_top))
        self.application.add_handler(CommandHandler("profit", self.cmd_profit))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("settings", self.cmd_settings))
        self.application.add_handler(CommandHandler("panic", self.cmd_panic))
        self.application.add_handler(CommandHandler("stopbot", self.cmd_stopbot))
        
        # Admin commands
        self.application.add_handler(CommandHandler("setminwhale", self.cmd_set_min_whale))
        self.application.add_handler(CommandHandler("setmaxposition", self.cmd_set_max_position))
        self.application.add_handler(CommandHandler("setslippage", self.cmd_set_slippage))
        self.application.add_handler(CommandHandler("toggletrading", self.cmd_toggle_trading))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        logger.info("All handlers registered successfully")
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        wallet = os.getenv('WALLET_ADDRESS', 'Not configured')
        
        welcome_msg = f"""
╔══════════════════════════════════════════╗
║      🤖 ICE ALPHA HUNTER PRO v2.0        ║
║      The Ultimate MEV Whale Sniper       ║
╚══════════════════════════════════════════╝

🎯 MISSION
Copy-trade whale moves → Auto-sell for profit → 100% to your wallet

📱 COMMAND CENTER
├─ /status - Live system dashboard
├─ /stats - Performance analytics
├─ /trades - Active positions
├─ /history - Past trades log
├─ /top - Best performing trades
├─ /profit - Withdrawable balance
├─ /balance - Wallet status
├─ /settings - Configuration
├─ /panic - Emergency liquidation
└─ /stopbot - Safe shutdown

⚙️ CURRENT SETUP
├─ Min Whale Size: ${self.config.MIN_WHALE_SIZE:,}
├─ Max Position: {self.config.MAX_POSITION_SOL} SOL
├─ Slippage: {self.config.SLIPPAGE}%
├─ Auto-Trade: {'🟢 ACTIVE' if self.config.AUTO_TRADE else '🔴 PAUSED'}
└─ Uptime: {self._get_uptime()}

💎 WHY WE'RE BETTER
✓ Faster than manual trading
✓ No emotions, pure data
✓ 24/7 monitoring
✓ Instant execution
✓ Full transparency

💰 YOUR WALLET
{wallet}
All profits auto-transfer here
"""
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        positions = self.trading_engine.get_open_positions()
        portfolio_value = sum(p['amount_sol'] for p in positions)
        
        status_msg = f"""
╔══════════════════════════════════════════╗
║           📊 SYSTEM DASHBOARD            ╚══════════════════════════════════════════╝

⚡ STATUS: {'🟢 OPERATIONAL' if self.whale_monitor.is_running else '🔴 STOPPED'}
⏱️ Uptime: {self._get_uptime()}
🔒 Security: Locked & Monitoring

📈 PORTFOLIO
├─ Open Positions: {len(positions)}
├─ Portfolio Value: {portfolio_value:.4f} SOL
├─ Total Trades: {self.db.get_total_trades()}
├─ Win Rate: {self.db.get_win_rate():.1f}%
└─ Total Profit: {self.profit_manager.get_total_profit():.4f} SOL

{'█' * int(self.db.get_win_rate() / 5)}{'░' * (20 - int(self.db.get_win_rate() / 5))} {self.db.get_win_rate():.1f}% Win Rate

🔧 CONFIGURATION
├─ Target Whales: ${self.config.MIN_WHALE_SIZE:,}+
├─ Max Position: {self.config.MAX_POSITION_SOL} SOL
├─ Execution Mode: {'⚡ AUTO-PILOT' if self.config.AUTO_TRADE else '👁️ MONITOR ONLY'}
└─ RPC: Helius (Premium)

🐋 MONITORING
├─ Helius WebSocket: {'🟢 Connected' if self.whale_monitor.ws_connected else '🔴 Disconnected'}
├─ Jupiter API: {'🟢 Ready' if self.trading_engine.jupiter_ready else '🔴 Down'}
├─ Telegram: 🟢 Active
└─ Wallet: {os.getenv('WALLET_ADDRESS', 'Not set')[:20]}...

💡 Next whale alert will be posted here automatically
"""
        await update.message.reply_text(status_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.db.get_performance_stats()
        
        stats_msg = f"""
╔══════════════════════════════════════════╗
║         📊 PERFORMANCE ANALYTICS         ╚══════════════════════════════════════════╝

🎯 TRADING PERFORMANCE
├─ Total Trades: {stats.get('total_trades', 0)}
├─ 🟢 Wins: {stats.get('wins', 0)}
├─ 🔴 Losses: {stats.get('losses', 0)}
├─ Win Rate: {stats.get('win_rate', 0):.1f}%
└─ Avg Profit/Trade: {stats.get('avg_profit', 0):.4f} SOL

{'█' * int(stats.get('win_rate', 0) / 5)}{'░' * (20 - int(stats.get('win_rate', 0) / 5))} {stats.get('win_rate', 0):.1f}%

💰 PROFIT SUMMARY
├─ Total SOL: {self.profit_manager.get_total_profit():.4f} ⬆️
├─ Total USD: ${self.profit_manager.get_total_profit_usd():.2f}
├─ Best Trade: +{stats.get('best_trade', 0):.4f} SOL
└─ Worst Trade: {stats.get('worst_trade', 0):.4f} SOL

🐋 WHALE ACTIVITY
├─ Detected: {stats.get('whales_detected', 0)}
├─ Followed: {stats.get('whales_followed', 0)}
└─ Conversion: {stats.get('conversion_rate', 0):.1f}%

📈 EFFICIENCY RATING
{'⭐' * int(stats.get('win_rate', 0) / 20)}
"""
        await update.message.reply_text(stats_msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trades command"""
        positions = self.trading_engine.get_open_positions()
        
        if not positions:
            msg = """
╔══════════════════════════════════════════╗
║           📭 NO ACTIVE POSITIONS          ╚══════════════════════════════════════════╝

Bot is scanning for whale opportunities...
Target: ${:,}+ transactions

🔔 You'll be notified instantly when we enter a trade
"""
        else:
            msg = "╔══════════════════════════════════════════╗\n"
            msg += "║           📊 ACTIVE POSITIONS             ║\n"
            msg += "╚══════════════════════════════════════════╝\n\n"
            
            for i, pos in enumerate(positions, 1):
                msg += f"📍 POSITION #{i}\n"
                msg += f"├─ Token: `{pos['token_address'][:20]}...`\n"
                msg += f"├─ Entry: {pos['entry_price']:.6f} SOL\n"
                msg += f"├─ Amount: {pos['amount_sol']:.4f} SOL\n"
                msg += f"├─ PnL: {pos.get('pnl', 0):+.4f} SOL\n"
                msg += f"└─ Time: {pos['timestamp']}\n\n"
        
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command"""
        trades = self.db.get_recent_trades(limit=10)
        
        if not trades:
            await update.message.reply_text("📭 No trade history yet.")
            return
        
        msg = "╔══════════════════════════════════════════╗\n"
        msg += "║           📜 RECENT TRADES                ║\n"
        msg += "╚══════════════════════════════════════════╝\n\n"
        
        for trade in trades:
            emoji = "🟢" if trade.get('profit', 0) > 0 else "🔴"
            msg += f"{emoji} `{trade['token_address'][:15]}...`\n"
            msg += f"├─ Profit: {trade.get('profit', 0):+.4f} SOL\n"
            msg += f"├─ Duration: {trade.get('duration', 'N/A')}\n"
            msg += f"└─ Closed: {trade.get('close_time', 'Unknown')}\n\n"
        
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top command"""
        top_trades = self.db.get_top_trades(limit=5)
        
        if not top_trades:
            msg = """
🏆 TOP PERFORMING TRADES

No completed trades yet.
Start trading to see leaderboard!

💡 Tip: Use /history for full log
"""
        else:
            msg = "╔══════════════════════════════════════════╗\n"
            msg += "║         🏆 TOP PERFORMING TRADES          ║\n"
            msg += "╚══════════════════════════════════════════╝\n\n"
            
            for i, trade in enumerate(top_trades, 1):
                medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
                msg += f"{medal} #{i}: `{trade['token_address'][:20]}...`\n"
                msg += f"   Profit: +{trade['profit']:.4f} SOL (${trade['profit_usd']:.2f})\n\n"
        
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_profit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /profit command"""
        profit_data = self.profit_manager.get_profit_summary()
        
        msg = f"""
╔══════════════════════════════════════════╗
║           💸 PROFIT DASHBOARD            ╚══════════════════════════════════════════╝

AVAILABLE BALANCE
├─ 💰 SOL: {profit_data['available_sol']:.4f} ⬆️
├─ 💵 USD: ${profit_data['available_usd']:.2f}
└─ 📈 Unrealized: {profit_data['unrealized_sol']:.4f} SOL

NEXT MILESTONE
{'█' * int(profit_data['progress'] / 5)}{'░' * (20 - int(profit_data['progress'] / 5))} {profit_data['progress']:.1f}% {profit_data['current']:.2f}/{profit_data['target']:.2f} SOL

WITHDRAWAL INFO
├─ 🎯 Destination: Your wallet
├─ 🔄 Method: Auto-transfer on sell
├─ ⛽ Fee: 0% (internal)
└─ ⚡ Speed: Instant

WALLET
{os.getenv('WALLET_ADDRESS', 'Not configured')}

💡 Profits transfer automatically!
No manual withdrawal needed.
"""
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        wallet = os.getenv('WALLET_ADDRESS', 'Not configured')
        
        msg = f"""
╔══════════════════════════════════════════╗
║           💰 WALLET STATUS               ╚══════════════════════════════════════════╝

📍 Address
`{wallet}`

🔗 Network: Solana Mainnet
🔌 RPC: Helius (Premium Tier)
💎 Type: Self-Custody

⚠️ IMPORTANT
├─ Keep 0.05+ SOL for transaction fees
├─ Never share private key
└─ All profits auto-deposit here

💸 Withdrawals
Profits are automatically transferred to this wallet when trades close. No manual action needed!

🔒 Security: Maximum
"""
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command"""
        msg = f"""
╔══════════════════════════════════════════╗
║           ⚙️ BOT CONFIGURATION           ╚══════════════════════════════════════════╝

CURRENT SETTINGS
├─ Min Whale Size: ${self.config.MIN_WHALE_SIZE:,}
├─ Max Position: {self.config.MAX_POSITION_SOL} SOL
├─ Slippage: {self.config.SLIPPAGE}%
├─ Auto-Sell Target: {self.config.TAKE_PROFIT}%
├─ Stop Loss: {self.config.STOP_LOSS}%
└─ Auto-Trade: {'✅ ON' if self.config.AUTO_TRADE else '❌ OFF'}

ADMIN COMMANDS
├─ /setminwhale <amount> - Update min whale ($)
├─ /setmaxposition <sol> - Update max position
├─ /setslippage <percent> - Update slippage %
└─ /toggletrading - Enable/disable auto-trade

⚠️ Changes take effect immediately
"""
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_panic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /panic command - Emergency sell all"""
        await update.message.reply_text("🚨 INITIATING EMERGENCY LIQUIDATION...")
        
        positions = self.trading_engine.get_open_positions()
        if not positions:
            await update.message.reply_text("📭 No positions to sell")
            return
        
        sold_count = 0
        for pos in positions:
            try:
                await self.trading_engine.emergency_sell(pos['token_address'])
                sold_count += 1
            except Exception as e:
                logger.error(f"Panic sell failed for {pos['token_address']}: {e}")
        
        await update.message.reply_text(f"✅ Sold {sold_count}/{len(positions)} positions")
    
    async def cmd_stopbot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stopbot command"""
        await update.message.reply_text("🛑 Shutting down... 👋")
        await self.stop()
    
    async def cmd_set_min_whale(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Set minimum whale size"""
        if not context.args:
            await update.message.reply_text("Usage: /setminwhale <amount_in_usd>")
            return
        
        try:
            amount = int(context.args[0])
            self.config.MIN_WHALE_SIZE = amount
            await update.message.reply_text(f"✅ Min whale size updated to ${amount:,}")
        except ValueError:
            await update.message.reply_text("❌ Invalid amount")
    
    async def cmd_set_max_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Set max position size"""
        if not context.args:
            await update.message.reply_text("Usage: /setmaxposition <sol_amount>")
            return
        
        try:
            amount = float(context.args[0])
            self.config.MAX_POSITION_SOL = amount
            await update.message.reply_text(f"✅ Max position updated to {amount} SOL")
        except ValueError:
            await update.message.reply_text("❌ Invalid amount")
    
    async def cmd_set_slippage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Set slippage tolerance"""
        if not context.args:
            await update.message.reply_text("Usage: /setslippage <percent>")
            return
        
        try:
            percent = float(context.args[0])
            self.config.SLIPPAGE = percent
            await update.message.reply_text(f"✅ Slippage updated to {percent}%")
        except ValueError:
            await update.message.reply_text("❌ Invalid percentage")
    
    async def cmd_toggle_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin: Toggle auto-trading"""
        self.config.AUTO_TRADE = not self.config.AUTO_TRADE
        status = "ENABLED" if self.config.AUTO_TRADE else "DISABLED"
        await update.message.reply_text(f"🔄 Auto-trading {status}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and hasattr(update, 'message') and update.message:
            await update.message.reply_text("⚠️ An error occurred. Check logs.")
    
    async def send_alert(self, message: str, to_channel: bool = True):
        """Send alert to Telegram (chat and/or channel)"""
        try:
            # Send to private chat
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send to channel if configured and requested
            if to_channel and self.channel_id and self.channel_id != self.chat_id:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    def _get_uptime(self):
        """Calculate uptime string"""
        if not hasattr(self, 'start_time') or self.start_time == 0:
            return "0h 0m"
        
        try:
            elapsed = asyncio.get_event_loop().time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"
        except:
            return "0h 0m"
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Telegram bot...")
        
        # Start whale monitor
        asyncio.create_task(self.whale_monitor.start())
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot is running!")
        await self.send_alert("🤖 IceAlphaHunter Pro is now ONLINE!", to_channel=True)
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        await self.whale_monitor.stop()
        await self.application.stop()
        await self.application.shutdown()

if __name__ == "__main__":
    bot = TelegramBot()
    asyncio.run(bot.start())
