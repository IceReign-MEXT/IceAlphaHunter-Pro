"""Telegram Bot - python-telegram-bot v13"""
import sys
import os
import time
import threading
import logging

# FIX: Add imghdr shim for Python 3.13+
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda file, h=None: None
    sys.modules['imghdr'] = imghdr

# Now import telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
    from telegram.ext import (
        Updater, CommandHandler, CallbackQueryHandler,
        CallbackContext, MessageHandler, Filters
    )
except ImportError as e:
    logging.error(f"Failed to import telegram: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.updater = None
        self.bot = None
        self.trading_engine = None
        self.whale_monitor = None
        self.is_running = False
        
    def initialize(self):
        """Initialize components"""
        from config import config
        
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set")
        
        self.updater = Updater(token=config.BOT_TOKEN, use_context=True)
        self.bot = self.updater.bot
        
        # Setup handlers
        self._setup_handlers()
        
        # Initialize other components
        from trading_engine import TradingEngine
        from whale_monitor import WhaleMonitor
        
        self.trading_engine = TradingEngine()
        self.whale_monitor = WhaleMonitor()
        self.whale_monitor.on_whale_detected(self._handle_whale_sync)
        
        logger.info("✅ Telegram bot initialized")
    
    def _setup_handlers(self):
        """Setup command handlers"""
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
🤖 **IceAlpha Hunter Pro** - Activated

🎯 MEV-Optimized Whale Following
📊 Auto-detect → Copy trade → Profit

**Commands:**
/status - Bot health & positions
/stats - Performance analytics  
/trades - Active trades
/balance - Wallet status
/settings - Configuration
/panic - Emergency sell all
/stopbot - Shutdown

🔔 Channel: ON
💰 Auto-trade: {'ON' if config.AUTO_TRADE_ENABLED else 'OFF'}
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status"),
             InlineKeyboardButton("💰 Stats", callback_data="stats")],
            [InlineKeyboardButton("📈 Trades", callback_data="trades"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        
        update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def cmd_help(self, update: Update, context: CallbackContext):
        """Help"""
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        help_text = """
📚 **Commands**

/status - Bot status
/stats - Trading stats
/trades - Active positions
/balance - SOL balance
/panic - Emergency sell
/stopbot - Shutdown
/broadcast <msg> - Channel message
        """
        update.message.reply_text(help_text, parse_mode='Markdown')
    
    def cmd_status(self, update: Update, context: CallbackContext):
        """Status"""
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        open_trades = db.get_open_trades()
        stats = db.get_stats()
        
        status_text = f"""
⚡ **Status**: {'🟢 RUNNING' if self.is_running else '🔴 STOPPED'}

📊 Positions: {len(open_trades)}
💼 Total Trades: {stats.get('total_trades', 0)}
📈 Win Rate: {stats.get('win_rate', 0):.1f}%
💵 Profit: {stats.get('total_profit_sol', 0):.3f} SOL

🔧 Config:
• Min: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
• Max: {config.MAX_POSITION_SOL} SOL
• Auto: {'✅' if config.AUTO_TRADE_ENABLED else '❌'}
        """
        
        update.message.reply_text(status_text, parse_mode='Markdown')
    
    def cmd_stats(self, update: Update, context: CallbackContext):
        """Stats"""
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        stats = db.get_stats()
        
        stats_text = f"""
📊 **Analytics**

Trades: {stats.get('total_trades', 0)}
Profitable: {stats.get('profitable_trades', 0)}
Win Rate: {stats.get('win_rate', 0):.1f}%

Total SOL: {stats.get('total_profit_sol', 0):.4f}
Total USD: ${stats.get('total_profit_usd', 0):.2f}
        """
        
        update.message.reply_text(stats_text, parse_mode='Markdown')
    
    def cmd_trades(self, update: Update, context: CallbackContext):
        """Trades"""
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        trades = db.get_open_trades()
        
        if not trades:
            update.message.reply_text("📭 No active positions")
            return
        
        text = "📈 **Active Positions**\n\n"
        for trade in trades:
            created_str = str(trade.get('created_at', ''))[:16]
            text += f"🔸 **{trade.get('token_symbol', 'Unknown')}**\n"
            text += f"• Entry: {trade.get('entry_price', 0):.6f} SOL\n"
            text += f"• Amount: {trade.get('amount', 0):.4f}\n"
            text += f"• Time: {created_str}\n\n"
        
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_balance(self, update: Update, context: CallbackContext):
        """Balance"""
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        text = f"""
💰 **Wallet**

Address: `{config.WALLET_PUBLIC_KEY}`

⚠️ Use /status for detailed info
        """
        
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_settings(self, update: Update, context: CallbackContext):
        """Settings"""
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        settings_text = f"""
⚙️ **Settings**

Min Whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
Max Position: {config.MAX_POSITION_SOL} SOL
Slippage: {config.SLIPPAGE_BPS/100}%
Auto-Trade: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}
        """
        
        update.message.reply_text(settings_text, parse_mode='Markdown')
    
    def cmd_panic_sell(self, update: Update, context: CallbackContext):
        """Panic sell"""
        from config import config
        from database import db
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        update.message.reply_text("🚨 **PANIC SELL INITIATED**", parse_mode='Markdown')
        
        trades = db.get_open_trades()
        sold = 0
        
        for trade in trades:
            try:
                import asyncio
                result = asyncio.run(self.trading_engine.sell_token(
                    trade.get('token_mint', ''),
                    trade.get('amount', 0)
                ))
                
                if result.success:
                    profit = result.output_amount - trade.get('amount', 0)
                    db.close_trade(trade.get('id'), result.output_amount, profit, 0, result.signature or '')
                    sold += 1
            except Exception as e:
                logger.error(f"Panic sell error: {e}")
        
        update.message.reply_text(f"✅ Sold {sold}/{len(trades)} positions")
    
    def cmd_stop(self, update: Update, context: CallbackContext):
        """Stop"""
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        self.is_running = False
        update.message.reply_text("🛑 Shutting down...")
        self.updater.stop()
    
    def cmd_broadcast(self, update: Update, context: CallbackContext):
        """Broadcast"""
        from config import config
        
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Usage: /broadcast <msg>")
            return
        
        try:
            self.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=f"📢 **Admin Update**\n\n{message}",
                parse_mode='Markdown'
            )
            update.message.reply_text("✅ Broadcast sent")
        except Exception as e:
            update.message.reply_text(f"❌ Failed: {str(e)}")
    
    def on_callback(self, update: Update, context: CallbackContext):
        """Callbacks"""
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
        """Handle whale (sync wrapper)"""
        import asyncio
        try:
            asyncio.run(self._handle_whale_async(whale))
        except Exception as e:
            logger.error(f"Handle whale error: {e}")
    
    async def _handle_whale_async(self, whale):
        """Handle whale (async)"""
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
                logger.info(f"Token validation failed: {validation.get('reason')}")
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
                        'metadata': {
                            'input_sol': position,
                            'price_impact': result.price_impact
                        }
                    })
                    
                    if trade_id:
                        db.mark_whale_followed(alert_id or 0, trade_id)
                    
                    await self._notify_channel(whale, result, position)
                else:
                    logger.error(f"Trade failed: {result.error}")
            
        except Exception as e:
            logger.error(f"Handle whale error: {e}")
    
    async def _notify_channel(self, whale, result, position):
        """Notify channel"""
        from config import config
        
        try:
            message = f"""
🐋 **WHALE FOLLOWED**

Whale: `{whale.trader_address[:8]}...{whale.trader_address[-8:]}`
Token: {whale.token_symbol}
Whale Buy: ${whale.amount_usd:,.2f}

**Our Trade**:
• Invested: {position:.3f} SOL
• Got: {result.output_amount:.4f} {whale.token_symbol}
• Impact: {result.price_impact:.2f}%
• TX: `{str(result.signature)[:20]}...`

⏳ Holding...
            """
            
            self.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Notify channel error: {e}")
    
    def run(self):
        """Run bot"""
        self.initialize()
        self.is_running = True
        
        # Start whale monitor in thread
        whale_thread = threading.Thread(target=self.whale_monitor.start_monitoring_sync, daemon=True)
        whale_thread.start()
        
        # Start polling
        self.updater.start_polling()
        logger.info("🤖 Bot is running...")
        
        # Keep running
        self.updater.idle()
        
        self.is_running = False
