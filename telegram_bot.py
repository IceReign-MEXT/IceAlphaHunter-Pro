"""Telegram Bot"""
import logging
from typing import Dict
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from config import config
from database import db
from trading_engine import trading_engine
from whale_monitor import whale_monitor

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.bot: Bot = None
        self.updater: Updater = None
        self.is_running = False
    
    def run(self):
        try:
            self.updater = Updater(token=config.BOT_TOKEN, use_context=True)
            self.bot = self.updater.bot
            dp = self.updater.dispatcher
            
            dp.add_handler(CommandHandler("start", self.cmd_start))
            dp.add_handler(CommandHandler("help", self.cmd_help))
            dp.add_handler(CommandHandler("status", self.cmd_status))
            dp.add_handler(CommandHandler("trades", self.cmd_trades))
            dp.add_handler(CommandHandler("whales", self.cmd_whales))
            dp.add_handler(CommandHandler("profit", self.cmd_profit))
            dp.add_handler(CommandHandler("buy", self.cmd_buy))
            dp.add_handler(CommandHandler("sell", self.cmd_sell))
            dp.add_handler(CommandHandler("addwhale", self.cmd_add_whale))
            
            whale_monitor.on_whale_movement(self.on_whale_alert)
            
            self.is_running = True
            logger.info("✅ Telegram bot started")
            
            self.send_channel_message(
                "🚀 <b>IceAlpha Hunter Pro</b> is now online!\\n"
                "Monitoring whale movements and executing trades..."
            )
            
            self.updater.start_polling()
            self.updater.idle()
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
    
    def stop(self):
        self.is_running = False
        if self.updater:
            self.updater.stop()
    
    def send_channel_message(self, message: str):
        try:
            if config.channel_id_int:
                self.bot.send_message(
                    chat_id=config.channel_id_int,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Channel msg error: {e}")
    
    def on_whale_alert(self, alert: Dict):
        emoji = "🟢" if alert["alert_type"] == "buy" else "🔴"
        msg = (
            f"{emoji} <b>Whale Alert!</b>\\n\\n"
            f"🐋 Wallet: <code>{alert['whale_address'][:8]}...</code>\\n"
            f"💎 Token: <code>{alert['token_address'][:8]}...</code>\\n"
            f"📊 Action: <b>{alert['alert_type'].upper()}</b>\\n"
            f"💰 Amount: ${alert['amount_usd']:,.2f}\\n"
            f"🔗 <a href='https://solscan.io/tx/{alert['tx_signature']}'>View Tx</a>"
        )
        self.send_channel_message(msg)
        if config.AUTO_TRADE_ENABLED and alert["alert_type"] == "buy":
            trading_engine.buy_token(alert["token_address"], 0.1)
    
    def cmd_start(self, update: Update, context: CallbackContext):
        user = update.effective_user
        db.save_user({"user_id": user.id, "username": user.username or "", "subscription_type": "free"})
        update.message.reply_html(
            f"👋 Welcome <b>{user.first_name}</b>!\\n\\n"
            "🚀 IceAlpha Hunter Pro Features:\\n"
            "• Real-time whale monitoring\\n"
            "• Automated copy-trading\\n"
            "• Profit tracking\\n\\n"
            "📊 Use /help for commands"
        )
    
    def cmd_help(self, update: Update, context: CallbackContext):
        update.message.reply_html(
            "<b>📚 Commands:</b>\\n\\n"
            "/start - Start bot\\n"
            "/status - Bot status\\n"
            "/trades - View trades\\n"
            "/whales - Whale alerts\\n"
            "/profit - Check profits\\n"
            "/buy <token> <amt> - Buy\\n"
            "/sell <token> <amt> - Sell\\n"
            "/addwhale <addr> - Add whale\\n"
            "/help - Show help"
        )
    
    def cmd_status(self, update: Update, context: CallbackContext):
        update.message.reply_html(
            "<b>📊 Status</b>\\n\\n"
            f"🤖 Bot: <b>{'Online' if self.is_running else 'Offline'}</b>\\n"
            f"💰 Auto-Trade: <b>{'On' if config.AUTO_TRADE_ENABLED else 'Off'}</b>\\n"
            f"🎯 Min Whale: <b>${config.MIN_WHALE_AMOUNT_USD:,.0f}</b>\\n"
            f"💳 Wallet: <code>{config.WALLET_PUBLIC_KEY[:8]}...</code>\\n"
            f"🐋 Whales: <b>{len(whale_monitor.known_whales)}</b>"
        )
    
    def cmd_trades(self, update: Update, context: CallbackContext):
        trades = db.get_trades(limit=5)
        if not trades:
            update.message.reply_text("📭 No trades yet")
            return
        msg = "<b>📈 Recent Trades:</b>\\n\\n"
        for t in trades:
            emoji = "🟢" if t["status"] == "completed" else "🟡"
            msg += f"{emoji} <b>{t['token_symbol']}</b> - {t['status']}\\n"
        update.message.reply_html(msg)
    
    def cmd_whales(self, update: Update, context: CallbackContext):
        alerts = db.get_recent_whale_alerts(limit=5)
        if not alerts:
            update.message.reply_text("📭 No alerts yet")
            return
        msg = "<b>🐋 Recent Alerts:</b>\\n\\n"
        for a in alerts:
            emoji = "🟢" if a["alert_type"] == "buy" else "🔴"
            msg += f"{emoji} {a['alert_type'].upper()} <code>{a['whale_address'][:6]}...</code> ${a['amount_usd']:,.0f}\\n"
        update.message.reply_html(msg)
    
    def cmd_profit(self, update: Update, context: CallbackContext):
        trades = db.get_trades(limit=100)
        profit = sum(t.get("profit_usd", 0) for t in trades if t["status"] == "completed")
        wins = len([t for t in trades if t.get("profit_usd", 0) > 0])
        total = len(trades)
        rate = (wins/total*100) if total > 0 else 0
        update.message.reply_html(
            f"<b>💰 Profit Summary</b>\\n\\n"
            f"Total P&L: <b>${profit:,.2f}</b>\\n"
            f"Trades: <b>{total}</b>\\n"
            f"Win Rate: <b>{rate:.1f}%</b>"
        )
    
    def cmd_buy(self, update: Update, context: CallbackContext):
        if not context.args or len(context.args) < 2:
            update.message.reply_text("Usage: /buy <token> <amount_sol>")
            return
        token, amt = context.args[0], float(context.args[1])
        update.message.reply_text(f"🟢 Buying {amt} SOL of {token[:8]}...")
        success = trading_engine.buy_token(token, amt)
        update.message.reply_text("✅ Buy order placed!" if success else "❌ Failed")
    
    def cmd_sell(self, update: Update, context: CallbackContext):
        if not context.args:
            update.message.reply_text("Usage: /sell <token> [percentage]")
            return
        token = context.args[0]
        pct = float(context.args[1]) if len(context.args) > 1 else 100
        update.message.reply_text(f"🔴 Selling {pct}% of {token[:8]}...")
        success = trading_engine.sell_token(token, pct)
        update.message.reply_text("✅ Sell order placed!" if success else "❌ Failed")
    
    def cmd_add_whale(self, update: Update, context: CallbackContext):
        if not context.args:
            update.message.reply_text("Usage: /addwhale <address> [label]")
            return
        addr = context.args[0]
        label = " ".join(context.args[1:]) if len(context.args) > 1 else ""
        whale_monitor.add_whale(addr, label)
        update.message.reply_html(f"✅ Added whale: <code>{addr[:8]}...</code>")

telegram_bot = TelegramBot()
