import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from core.whale_monitor import WhaleMonitor

load_dotenv()

class IceAlphaBot:
    def __init__(self):
        self.monitor = WhaleMonitor()
        self.is_monitoring = False
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Admin only"""
        user_id = str(update.effective_user.id)
        if user_id != os.getenv("ADMIN_ID"):
            await update.message.reply_text("⛔ Unauthorized")
            return
            
        wallet = "CUCPfYEBgQBAgB1js3F3Hxz7vbqzY7x6zG8yR8fJ252o"
        
        text = (
            f"⚔️ <b>ICE ALPHA HUNTER PRO v2.0</b> ⚔️\n\n"
            f"👤 <b>Operator:</b> Admin\n"
            f"📡 <b>Node:</b> Helius Premium\n"
            f"💳 <b>Wallet:</b> <code>{wallet[:8]}...{wallet[-8:]}</code>\n"
            f"📢 <b>Channel:</b> <code>{os.getenv('CHANNEL_ID')}</code>\n\n"
            f"<i>Ready to hunt whale alpha.</i>"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 START WHALE MONITOR", callback_data="start_monitor")],
            [InlineKeyboardButton("🚀 SEND TEST SIGNAL", callback_data="test_signal")],
            [InlineKeyboardButton("💰 CHECK BALANCE", callback_data="check_balance")]
        ]
        
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='HTML'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "start_monitor":
            if not self.is_monitoring:
                self.is_monitoring = True
                asyncio.create_task(self.run_monitor_loop())
                await query.edit_message_text("✅ <b>WHALE MONITOR ACTIVATED</b>\n\nScanning blockchain for alpha...", parse_mode='HTML')
            else:
                await query.edit_message_text("⚠️ Monitor already running", parse_mode='HTML')
                
        elif query.data == "test_signal":
            await self.send_test_signal(context)
            await query.edit_message_text("✅ Test signal sent to channel", parse_mode='HTML')
            
        elif query.data == "check_balance":
            await query.edit_message_text("💰 Balance check coming soon...", parse_mode='HTML')
    
    async def run_monitor_loop(self):
        """Continuous monitoring"""
        while self.is_monitoring:
            try:
                signals = await self.monitor.fetch_whale_transactions()
                for signal in signals:
                    await self.monitor.send_alert(signal)
                    await asyncio.sleep(2)  # Avoid rate limits
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def send_test_signal(self, context: ContextTypes.DEFAULT_TYPE):
        """Send demo signal"""
        test_signal = {
            "type": "TEST",
            "whale": "4ACfp...7NhDEE",
            "token": "SOLANA-ALFA (ALFA)",
            "amount": 450.0,
            "tx_hash": "test123",
            "timestamp": "2026-03-02T00:00:00"
        }
        await self.monitor.send_alert(test_signal)

def main():
    token = os.getenv("BOT_TOKEN")
    bot = IceAlphaBot()
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.button_handler))
    
    print("⚔️ ICE ALPHA HUNTER STARTED")
    app.run_polling()

if __name__ == "__main__":
    main()
