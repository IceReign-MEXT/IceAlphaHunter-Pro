"""Telegram Bot - Webhook Mode (No Polling Conflicts)"""
import sys
import os
import time
import threading
import logging
import asyncio

# CRITICAL: Add imghdr shim
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda filename, h=None: None
    sys.modules['imghdr'] = imghdr

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Dispatcher, CommandHandler, CallbackQueryHandler,
    CallbackContext, MessageHandler, Filters
)
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
        
    def initialize(self):
        """Initialize"""
        from config import config
        
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set")
        
        self.channel_id = config.CHANNEL_ID
        self.admin_id = config.ADMIN_ID
        
        # Initialize bot
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dispatcher = Dispatcher(self.bot, None, workers=4)
        
        self._setup_handlers()
        
        from trading_engine import TradingEngine
        from whale_monitor import WhaleMonitor
        
        self.trading_engine = TradingEngine()
        self.whale_monitor = WhaleMonitor()
        self.whale_monitor.on_whale_detected(self._handle_whale_sync)
        
        # Setup webhook endpoint
        self._setup_webhook_endpoint()
        
        # Send startup
        self._send_startup_message()
        
        logger.info("✅ Bot initialized in WEBHOOK mode")
    
    def _setup_webhook_endpoint(self):
        """Setup Flask webhook endpoint"""
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Receive Telegram updates"""
            if request.method == "POST":
                update = Update.de_json(request.get_json(force=True), self.bot)
                self.dispatcher.process_update(update)
                return jsonify({"status": "ok"}), 200
            return jsonify({"status": "error"}), 400
        
        @self.app.route('/')
        def health():
            """Health check"""
            return {
                "status": "running",
                "bot": "IceAlpha Hunter Pro",
                "mode": "webhook",
                "timestamp": time.time()
            }, 200
    
    def _send_startup_message(self):
        """Send startup to channel"""
        if not self.channel_id:
            return
        
        try:
            self.bot.send_message(
                chat_id=self.channel_id,
                text=f"""
🚀 **ICALPHA HUNTER - ONLINE**

🤖 Status: Operational
💰 Auto-Trade: {'✅ ON' if self._get_config().AUTO_TRADE_ENABLED else '❌ OFF'}
🎯 Min Whale: ${self._get_config().MIN_WHALE_AMOUNT_USD:,.0f}

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

🔔 Monitoring for whales...
                """,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Startup msg failed: {e}")
    
    def _get_config(self):
        from config import config
        return config
    
    def _setup_handlers(self):
        """Setup command handlers"""
        dp = self.dispatcher
        
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
        dp.add_handler(CallbackQueryHandler(self.on_callback))
        dp.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
    
    def cmd_start(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            update.message.reply_text("⛔ Unauthorized")
            return
        
        welcome = f"""
🤖 **ICALPHA HUNTER PRO**

**COMMANDS:**
/status - Bot status
/stats - Performance
/trades - Active positions
/balance - Wallet
/profit - View profits
/panic - Emergency sell
/stopbot - Shutdown

**CONFIG:**
• Min Whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
• Max Position: {config.MAX_POSITION_SOL} SOL
• Auto-Trade: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}

💰 100% profits to your wallet
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status"),
             InlineKeyboardButton("💰 Stats", callback_data="stats")],
            [InlineKeyboardButton("📈 Trades", callback_data="trades"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ]
        
        update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    def cmd_help(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != config.ADMIN_ID:
            return
        update.message.reply_text("📚 /status /stats /trades /balance /profit /panic /stopbot", parse_mode='Markdown')
    
    def cmd_status(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != config.ADMIN_ID:
            return
        
        open_trades = db.get_open_trades()
        stats = db.get_stats()
        
        status = f"""
⚡ **STATUS**: {'🟢 RUNNING' if self.is_running else '🔴 OFFLINE'}
📊 Positions: {len(open_trades)}
💼 Trades: {stats.get('total_trades', 0)}
📈 Win Rate: {stats.get('win_rate', 0):.1f}%
💵 Profit: {stats.get('total_profit_sol', 0):.4f} SOL
        """
        update.message.reply_text(status, parse_mode='Markdown')
    
    def cmd_stats(self, update: Update, context: CallbackContext):
        from database import db
        if update.effective_user.id != self.admin_id:
            return
        
        stats = db.get_stats()
        text = f"""
📊 **STATS**
Trades: {stats.get('total_trades', 0)}
Profitable: {stats.get('profitable_trades', 0)}
SOL: {stats.get('total_profit_sol', 0):.4f}
USD: ${stats.get('total_profit_usd', 0):.2f}
        """
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_trades(self, update: Update, context: CallbackContext):
        from database import db
        if update.effective_user.id != self.admin_id:
            return
        
        trades = db.get_open_trades()
        if not trades:
            update.message.reply_text("📭 No positions", parse_mode='Markdown')
            return
        
        text = "📈 **TRADES**\n\n"
        for t in trades:
            text += f"🔸 {t.get('token_symbol', 'Unknown')}: {t.get('amount', 0):.4f}\n"
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_balance(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != self.admin_id:
            return
        text = f"💰 **Wallet**\n`{config.WALLET_PUBLIC_KEY}`"
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_settings(self, update: Update, context: CallbackContext):
        from config import config
        if update.effective_user.id != self.admin_id:
            return
        text = f"""
⚙️ **SETTINGS**
Min: ${config.MIN_WHALE_AMOUNT_USD:,.0f}
Max: {config.MAX_POSITION_SOL} SOL
Auto: {'✅ ON' if config.AUTO_TRADE_ENABLED else '❌ OFF'}
        """
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_profit(self, update: Update, context: CallbackContext):
        from config import config
        from database import db
        if update.effective_user.id != self.admin_id:
            return
        
        stats = db.get_stats()
        text = f"""
💸 **PROFIT**
SOL: {stats.get('total_profit_sol', 0):.4f}
USD: ${stats.get('total_profit_usd', 0):.2f}
Wallet: {config.WALLET_PUBLIC_KEY[:20]}...
        """
        update.message.reply_text(text, parse_mode='Markdown')
    
    def cmd_panic_sell(self, update: Update, context: CallbackContext):
        from database import db
        if update.effective_user.id != self.admin_id:
            return
        
        update.message.reply_text("🚨 **PANIC SELL**", parse_mode='Markdown')
        
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
                logger.error(f"Panic error: {e}")
        
        update.message.reply_text(f"✅ Sold {sold}/{len(trades)}", parse_mode='Markdown')
    
    def cmd_stop(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self.admin_id:
            return
        
        self.is_running = False
        update.message.reply_text("🛑 **Shutting down...**", parse_mode='Markdown')
        
        # Shutdown Flask
        func = request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
    
    def cmd_broadcast(self, update: Update, context: CallbackContext):
        if update.effective_user.id != self.admin_id:
            return
        
        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Usage: /broadcast <msg>")
            return
        
        try:
            self.bot.send_message(
                chat_id=self.channel_id,
                text=f"📢 **ADMIN**\n\n{message}",
                parse_mode='Markdown'
            )
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
            logger.error(f"Whale error: {e}")
    
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
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logger.error(f"Channel notify: {e}")
                    
                    # Auto-sell
                    await self._auto_sell(trade_id, whale.token_mint, result.output_amount)
                    
        except Exception as e:
            logger.error(f"Handle whale: {e}")
    
    async def _auto_sell(self, trade_id, token_mint, amount):
        await asyncio.sleep(60)
        
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
Trade #{trade_id}
Profit: {profit:+.4f} SOL
                            """,
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                
                logger.info(f"Auto-sell: {profit:.4f} SOL")
        except Exception as e:
            logger.error(f"Auto-sell: {e}")
    
    def run(self):
        """Run webhook server"""
        from config import config
        
        self.initialize()
        self.is_running = True
        
        # Start whale monitor in thread
        threading.Thread(target=self.whale_monitor.start_monitoring_sync, daemon=True).start()
        
        # Set webhook
        port = int(os.getenv('PORT', 10000))
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
        
        try:
            self.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set: {webhook_url}")
        except Exception as e:
            logger.error(f"Webhook setup failed: {e}")
            logger.info("🔄 Falling back to polling...")
            # Fallback to polling with drop_pending_updates
            threading.Thread(target=self._run_polling, daemon=True).start()
        
        # Start Flask
        logger.info(f"🌐 Starting server on port {port}")
        self.app.run(host='0.0.0.0', port=port, threaded=True)
    
    def _run_polling(self):
        """Fallback polling"""
        from telegram.ext import Updater
        
        updater = Updater(bot=self.bot, use_context=True)
        
        # Copy handlers
        for handler in self.dispatcher.handlers[0]:
            updater.dispatcher.add_handler(handler)
        
        updater.start_polling(drop_pending_updates=True)
        updater.idle()
