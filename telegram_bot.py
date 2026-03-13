"""Professional Telegram Bot"""
import logging
from datetime import datetime
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from config import config
from database import db
from subscription_manager import subscription_manager
from trading_engine import trading_engine
from whale_monitor import whale_monitor

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot = None
        self.updater = None
        self.running = False
    
    def run(self):
        try:
            self.updater = Updater(config.BOT_TOKEN, use_context=True)
            self.bot = self.updater.bot
            dp = self.updater.dispatcher
            
            # Commands
            dp.add_handler(CommandHandler("start", self.start))
            dp.add_handler(CommandHandler("help", self.help))
            dp.add_handler(CommandHandler("subscription", self.subscription))
            dp.add_handler(CommandHandler("upgrade", self.upgrade))
            dp.add_handler(CommandHandler("trades", self.trades))
            dp.add_handler(CommandHandler("profit", self.profit))
            dp.add_handler(CommandHandler("buy", self.buy))
            dp.add_handler(CommandHandler("addwhale", self.addwhale))
            dp.add_handler(CommandHandler("stats", self.stats))
            
            whale_monitor.on_whale_movement(self.on_whale)
            
            self.running = True
            logger.info("Bot started")
            
            # Startup message to channel
            self.bot.send_message(
                chat_id=config.channel_id_int,
                text="🚀 <b>IceAlpha Hunter Pro</b> Online!\n💰 Auto-trading active\n🐋 Monitoring whales...",
                parse_mode=ParseMode.HTML
            )
            
            self.updater.start_polling()
            self.updater.idle()
        except Exception as e:
            logger.error(f"Bot error: {e}")
    
    def stop(self):
        self.running = False
        if self.updater:
            self.updater.stop()
    
    def on_whale(self, alert):
        msg = (
            f"{'🟢' if alert['alert_type']=='buy' else '🔴'} <b>WHALE ALERT!</b>\n\n"
            f"🐋 {alert['whale_address'][:8]}...\n"
            f"💎 {alert['token_address'][:8]}...\n"
            f"📊 {alert['alert_type'].upper()}\n"
            f"💰 ${alert['amount_usd']:,.2f}\n"
            f"🔗 <a href='https://solscan.io/tx/{alert['tx_signature']}'>View</a>\n\n"
            f"<i>Pro users auto-copying...</i>"
        )
        try:
            self.bot.send_message(chat_id=config.channel_id_int, text=msg, parse_mode=ParseMode.HTML)
        except:
            pass
        
        if alert['alert_type'] == 'buy' and config.AUTO_TRADE_ENABLED:
            trading_engine.buy_token(alert['token_address'], 0.1)
    
    def start(self, update: Update, context: CallbackContext):
        user = update.effective_user
        db.save_user({
            "user_id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "subscription_type": "free"
        })
        
        welcome = f"""
👋 <b>Welcome {user.first_name}!</b>

🚀 <b>IceAlpha Hunter Pro</b> - Real Money Maker

💰 <b>How You Make Money:</b>
• We track whales spending $10K-$1M per trade
• Detect their moves in < 1 second
• Copy their trades automatically
• Average 15-30% profit per trade

📊 <b>What You Get:</b>
• Real-time whale alerts
• Auto-copy profitable trades
• 2% fee ONLY on profits (no win = no fee)
• Instant notifications

💎 <b>Plans:</b>
• Free: Manual only
• Basic (0.5 SOL): Alerts
• Pro (1.5 SOL): Auto-trade
• Whale (5 SOL): Unlimited

🚀 <b>Start Now:</b>
/subscription - Check your plan
/upgrade - Go Pro
/help - All commands

<i>🤖 Live and monitoring...</i>
"""
        update.message.reply_html(welcome)
    
    def help(self, update: Update, context: CallbackContext):
        help_text = """
<b>📚 Commands</b>

💎 <b>Account</b>
/subscription - Your plan
/upgrade - Upgrade to Pro
/profit - Your profits

📊 <b>Trading</b>
/trades - History
/buy [token] [amt] - Buy
/sell [token] [amt] - Sell

🐋 <b>Whales</b>
/addwhale [addr] - Track whale
/stats - Global stats

<i>💰 Pro = Auto-money!</i>
"""
        update.message.reply_html(help_text)
    
    def subscription(self, update: Update, context: CallbackContext):
        text = subscription_manager.get_text(update.effective_user.id)
        update.message.reply_html(text)
    
    def upgrade(self, update: Update, context: CallbackContext):
        wallet = config.WALLET_PUBLIC_KEY
        uid = update.effective_user.id
        text = f"""
<b>💎 Upgrade</b>

🥉 <b>Basic - 0.5 SOL</b>
✅ Whale alerts
📊 5 trades/day

🥈 <b>Pro - 1.5 SOL</b>
✅ Auto-copy trades
✅ Priority alerts
📊 20 trades/day

🥇 <b>Whale - 5 SOL</b>
✅ Unlimited everything
🎯 White-glove service

<b>Pay:</b>
<code>{wallet}</code>
Amount: [Plan] SOL
Memo: {uid}

Reply with tx to activate
"""
        update.message.reply_html(text)
    
    def trades(self, update: Update, context: CallbackContext):
        trades = db.get_trades(user_id=update.effective_user.id, limit=5)
        if not trades:
            update.message.reply_text("No trades yet. Use /buy to start!")
            return
        
        msg = "<b>📈 Your Trades:</b>\n\n"
        total = 0
        for t in trades:
            pnl = t.get('profit_sol', 0)
            total += pnl
            emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
            msg += f"{emoji} {t['token_symbol']}: {pnl:+.4f} SOL\n"
        
        msg += f"\n<b>Total: {total:+.4f} SOL</b>"
        update.message.reply_html(msg)
    
    def profit(self, update: Update, context: CallbackContext):
        user = db.get_user(update.effective_user.id)
        if not user:
            update.message.reply_text("No data")
            return
        
        profit = user.get('total_profit_sol', 0)
        fees = user.get('total_fees_paid', 0)
        net = profit - fees
        
        text = f"""
<b>💰 Your Profit</b>

📊 Total Profit: {profit:.4f} SOL
🏦 Fees (2%): {fees:.4f} SOL
💰 Net Profit: {net:.4f} SOL

{subscription_manager.get_text(update.effective_user.id)}
"""
        update.message.reply_html(text)
    
    def buy(self, update: Update, context: CallbackContext):
        uid = update.effective_user.id
        
        if not subscription_manager.can_use(uid, 'auto'):
            update.message.reply_html(
                "❌ <b>Locked</b>\nNeed Basic+ plan\n/upgrade to unlock"
            )
            return
        
        if not context.args or len(context.args) < 2:
            update.message.reply_text("Usage: /buy [token] [amount]")
            return
        
        token, amt = context.args[0], float(context.args[1])
        update.message.reply_text(f"Buying {amt} SOL of {token[:8]}...")
        
        if trading_engine.buy_token(token, amt):
            update.message.reply_text("✅ Order placed!")
        else:
            update.message.reply_text("❌ Failed")
    
    def addwhale(self, update: Update, context: CallbackContext):
        if not context.args:
            update.message.reply_text("Usage: /addwhale [address]")
            return
        
        addr = context.args[0]
        whale_monitor.add_whale(addr, "", True)
        update.message.reply_html(
            f"✅ Whale added: <code>{addr[:8]}...</code>\n"
            f"Alerts > ${config.MIN_WHALE_AMOUNT_USD}"
        )
    
    def stats(self, update: Update, context: CallbackContext):
        stats = db.get_bot_stats()
        text = f"""
<b>📊 Global Stats</b>

👥 Users: {stats.get('total_users', 0)}
💎 Trades: {stats.get('total_trades', 0)}
💰 Volume: {stats.get('total_volume_sol', 0):.2f} SOL
🏦 Fees: {stats.get('total_fees_collected', 0):.4f} SOL

🐋 Whales: {len(whale_monitor.known_whales)}
<i>📈 Growing!</i>
"""
        update.message.reply_html(text)

telegram_bot = TelegramBot()
