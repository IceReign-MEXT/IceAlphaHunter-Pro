"""Telegram Bot - With Conflict Handling"""
import sys
import os
import time
import threading
import logging
import asyncio

# CRITICAL: Add imghdr shim BEFORE any other imports
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda filename, h=None: None
    sys.modules['imghdr'] = imghdr

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    CallbackContext, MessageHandler, Filters
)
from telegram.error import Conflict, NetworkError

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.updater = None
        self.bot = None
        self.trading_engine = None
        self.whale_monitor = None
        self.is_running = False
        self.channel_id = None
        self.admin_id = None
        
    def initialize(self):
        """Initialize components"""
        from config import config
        
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set")
        
        self.channel_id = config.CHANNEL_ID
        self.admin_id = config.ADMIN_ID
        
        # Add retry logic for conflict
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.updater = Updater(token=config.BOT_TOKEN, use_context=True)
                self.bot = self.updater.bot
                logger.info(f"✅ Bot connected (attempt {attempt + 1})")
                break
            except Conflict as e:
                if attempt < max_retries - 1:
                    logger.warning(f"⚠️ Conflict detected, waiting 10s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(10)
                else:
                    logger.error("❌ Could not connect after 3 attempts. Another instance is running.")
                    raise e
        
        self._setup_handlers()
        
        from trading_engine import TradingEngine
        from whale_monitor import WhaleMonitor
        
        self.trading_engine = TradingEngine()
        self.whale_monitor = WhaleMonitor()
        self.whale_monitor.on_whale_detected(self._handle_whale_sync)
        
        # Send startup message
        self._send_startup_message()
        
        logger.info("✅ Telegram bot initialized")
    
    def _send_startup_message(self):
        """Send startup message to channel"""
        if not self.channel_id:
            return
            
        startup_msg = f"""
🚀 **ICALPHA HUNTER PRO - ONLINE**

🤖 **System Status**: Operational
💰 **Auto-Trading**: {'✅ ACTIVE' if self._get_config().AUTO_TRADE_ENABLED else '❌ MONITOR'}
🎯 **Min Whale**: ${self._get_config().MIN_WHALE_AMOUNT_USD:,.0f}
💼 **Max Position**: {self._get_config().MAX_POSITION_SOL} SOL

**Features:**
• Real-time whale detection
• Jupiter v6 swap execution
• Auto-profit transfer to wallet
• 24/7 monitoring

⏰ Started: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

🔔 **Waiting for whale transactions...**
        """
        
        try:
            self.bot.send_message(
                chat_id=self.channel_id,
                text=startup_msg,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Startup message failed: {e}")
    
    def _get_config(self):
        from config import config
        return config
    
    def _setup_handlers(self):
        """Setup handlers"""
        dp = self.updater.dispatcher
        
        dp.add_handler(CommandHandler("start", self.cmd_start))
        dp.add_handler(CommandHandler("help", self.cmd_help))
        dp.add_handler(CommandHandler("status", self.cmd_status))
        dp.add_handler(CommandHandler("stats", self.cmd_stats))
        dp.add_handler(CommandHandler("trades", self.cmd_trades))
        dp.add_handler(CommandHandler("balance", self.cmd_balance))
        dp.add_handler(CommandHandler("settings", self.cmd_settings))
        dp.add_handler(CommandHandler("stopbot", self.cmd_stop))
        dp.add_handler(CommandHandler("panic", self.cmd_panic_sell))
        dp.add_handler(CommandHandler("profit", self.cmd_profit))
        dp.add_handler(CommandHandler("withdraw", self.cmd_withdraw))
        dp.add_handler(CallbackQueryHandler(self.on_callback))
        dp.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
    
    def cmd_start(self, update: Update, context: CallbackContext):
        """Start command"""
        from config import config
        user_id = update.effective_user.id
        
        if user_id != config.ADMIN_ID:
            update.message.reply_text("⛔ Unauthorized.")
            return
        
        welcome_text = f"""
🤖 **ICALPHA HUNTER PRO**

🎯 **MISSION**: MEV-Optimized Whale Following
📊 **STRATEGY**: Auto-detect → Copy trade → Profit

**📱 COMMANDS:**
/status - Bot health & positions
/stats - Performance & P&L  
/trades - Active trades
/balance - Wallet status
/settings - Configuration
/profit - View profits
/withdraw - Transfer profits
/panic - Emergency sell all
/stopbot - Shutdown

**⚙️ CONFIG:**
• Min Whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
• Max Position: {config.MAX_POSITION_SOL} SOL
• Auto-Trade: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}

**💰 PROFITS:**
• 100% to your wallet
• Auto-transfer enabled
• Real-time tracking

🚀 **Bot is LIVE**
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status"),
             InlineKeyboardButton("💰 Stats", callback_data="stats")],
            [InlineKeyboardButton("📈 Trades", callback_data="trades"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        
        update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    def cmd_help(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        update.message.reply_text("📚 Commands: /status /stats /trades /balance /profit /withdraw /panic /stopbot", parse_mode=ParseMode.MARKDOWN)
    
    def cmd_status(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        open_trades = db.get_open_trades()
        stats = db.get_stats()
        
        status_text = f"""
⚡ **STATUS**: {'🟢 OPERATIONAL' if self.is_running else '🔴 OFFLINE'}

📊 **DASHBOARD**
├─ Open Positions: {len(open_trades)}
├─ Total Trades: {stats.get('total_trades', 0)}
├─ Win Rate: {stats.get('win_rate', 0):.1f}%
└─ Total Profit: {stats.get('total_profit_sol', 0):.4f} SOL

🔧 **CONFIG**
├─ Min Whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
├─ Max Position: {config.MAX_POSITION_SOL} SOL
└─ Auto-Trade: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}
        """
        update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_stats(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        stats = db.get_stats()
        stats_text = f"""
📊 **ANALYTICS**
Trades: {stats.get('total_trades', 0)}
Profitable: {stats.get('profitable_trades', 0)}
Total SOL: {stats.get('total_profit_sol', 0):.4f}
Total USD: ${stats.get('total_profit_usd', 0):.2f}
        """
        update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_trades(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        trades = db.get_open_trades()
        if not trades:
            update.message.reply_text("📭 No active positions", parse_mode=ParseMode.MARKDOWN)
            return
        
        text = "📈 **ACTIVE POSITIONS**\n\n"
        for trade in trades:
            text += f"🔸 **{trade.get('token_symbol', 'Unknown')}** - {trade.get('amount', 0):.4f}\n"
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_balance(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        text = f"💰 **Wallet**\nAddress: `{config.WALLET_PUBLIC_KEY}`"
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_settings(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        settings_text = f"""
⚙️ **SETTINGS**
Min Whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
Max Position: {config.MAX_POSITION_SOL} SOL
Auto-Trade: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}
        """
        update.message.reply_text(settings_text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_profit(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        stats = db.get_stats()
        profit_text = f"""
💸 **PROFIT DASHBOARD**
Total SOL: {stats.get('total_profit_sol', 0):.4f} SOL
Total USD: ${stats.get('total_profit_usd', 0):.2f}
Wallet: {config.WALLET_PUBLIC_KEY[:20]}...
        """
        update.message.reply_text(profit_text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_withdraw(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        update.message.reply_text(
            f"💸 **WITHDRAWAL**\n\nProfits auto-transfer to:\n`{config.WALLET_PUBLIC_KEY}`\n\nNo manual action needed!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    def cmd_panic_sell(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        update.message.reply_text("🚨 **PANIC SELL**", parse_mode=ParseMode.MARKDOWN)
        
        trades = db.get_open_trades()
        sold = 0
        
        for trade in trades:
            try:
                result = asyncio.run(self.trading_engine.sell_token(trade.get('token_mint', ''), trade.get('amount', 0)))
                if result.success:
                    profit = result.output_amount - trade.get('amount', 0)
                    db.close_trade(trade.get('id'), result.output_amount, profit, 0, result.signature or '')
                    sold += 1
            except Exception as e:
                logger.error(f"Panic error: {e}")
        
        update.message.reply_text(f"✅ Sold {sold}/{len(trades)}", parse_mode=ParseMode.MARKDOWN)
    
    def cmd_stop(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        if self.channel_id:
            try:
                self.bot.send_message(
                    chat_id=self.channel_id,
                    text="🛑 **OFFLINE**\n\nBot shutdown. Will resume on restart.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        self.is_running = False
        update.message.reply_text("🛑 **Shutting down...**", parse_mode=ParseMode.MARKDOWN)
        self.updater.stop()
    
    def cmd_broadcast(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Usage: /broadcast <msg>")
            return
        
        try:
            self.bot.send_message(chat_id=self.channel_id, text=f"📢 **ADMIN**\n\n{message}", parse_mode=ParseMode.MARKDOWN)
            update.message.reply_text("✅ Sent")
        except Exception as e:
            update.message.reply_text(f"❌ Failed: {str(e)}")
    
    def on_callback(self, update: Update, context: CallbackContext):
        query = update.callback_query
        query.answer()
        
        if query.data == "status":
            self.cmd_status(update, context)
        elif query.data == "stats":
            self.cmd_stats(update, context)
        elif query.data == "trades":
            self.cmd_trades(update, context)
        elif query.data == "settings":
            self.cmd_settings(update, context)
    
    def _handle_whale_sync(self, whale):
        try:
            asyncio.run(self._handle_whale_async(whale))
        except Exception as e:
            logger.error(f"Handle whale error: {e}")
    
    async def _handle_whale_async(self, whale):
        from config import config
        from database import db
        
        try:
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
                    
                    # Notify channel
                    if self.channel_id:
                        try:
                            self.bot.send_message(
                                chat_id=self.channel_id,
                                text=f"""
🐋 **WHALE FOLLOWED**
Token: {whale.token_symbol}
Invested: {position:.3f} SOL
Received: {result.output_amount:.4f}
TX: `{str(result.signature)[:20]}...`
                                """,
                                parse_mode=ParseMode.MARKDOWN
                            )
                        except Exception as e:
                            logger.error(f"Channel notify error: {e}")
                    
                    # Auto-sell after delay
                    await self._auto_sell(trade_id, whale.token_mint, result.output_amount)
                    
        except Exception as e:
            logger.error(f"Handle whale error: {e}")
    
    async def _auto_sell(self, trade_id, token_mint, amount):
        """Auto-sell for profit"""
        await asyncio.sleep(60)  # Wait 1 min for demo
        
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
💰 **PROFIT**
Trade #{trade_id} closed
Profit: {profit:+.4f} SOL
TX: `{result.signature[:20] if result.signature else 'N/A'}...`
                            """,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
                
                logger.info(f"✅ Auto-sell: {profit:.4f} SOL profit")
        except Exception as e:
            logger.error(f"Auto-sell error: {e}")
    
    def run(self):
        """Run bot with conflict handling"""
        self.initialize()
        self.is_running = True
        
        # Start whale monitor
        threading.Thread(target=self.whale_monitor.start_monitoring_sync, daemon=True).start()
        
        # Start polling with error handling
        logger.info("🤖 Starting polling...")
        
        while self.is_running:
            try:
                self.updater.start_polling(drop_pending_updates=True)
                self.updater.idle()
                break
            except Conflict as e:
                logger.warning(f"⚠️ Conflict: {e}")
                logger.info("Waiting 15s before retry...")
                time.sleep(15)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
        
        self.is_running = False
