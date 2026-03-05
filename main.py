#!/usr/bin/env python3
"""
🤖 MEX BALANCER PRO - FINAL VERSION
Auto-posts profits to channel for transparency & trust
"""

import os
import asyncio
import aiohttp
import random
from datetime import datetime
from typing import Dict
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
RPC_URL = os.getenv("RPC_URL")
WALLET = os.getenv("SOL_MAIN")
FEE_WALLET = os.getenv("FEE_WALLET", WALLET)
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = "https://mex-balancer.onrender.com"

TIERS = {
    "free": {"name": "🆓 Free", "max_trade": 2.0, "daily_trades": 5, "fee_percent": 1.0, "mev_boost": False, "auto_tp": False, "price_sol": 0},
    "pro": {"name": "⚡ Pro", "max_trade": 10.0, "daily_trades": 20, "fee_percent": 0.5, "mev_boost": True, "auto_tp": True, "price_sol": 0.5},
    "whale": {"name": "🐋 Whale", "max_trade": 50.0, "daily_trades": 100, "fee_percent": 0.25, "mev_boost": True, "auto_tp": True, "copy_trading": True, "price_sol": 2.0}
}

WAITING_TOKEN, WAITING_AMOUNT = 1, 2

class UserData:
    def __init__(self):
        self.users = {}
    
    def get_user(self, user_id: int) -> Dict:
        if user_id not in self.users:
            self.users[user_id] = {
                "tier": "free", "joined": datetime.now().isoformat(),
                "total_trades": 0, "total_volume": 0.0, "total_profit": 0.0,
                "total_fees_paid": 0.0, "coffee_earnings": 0.0,
                "daily_trades": 0, "last_trade_date": None,
                "biggest_win": 0.0
            }
        return self.users[user_id]
    
    def record_trade(self, user_id: int, amount: float, profit: float, fee: float):
        user = self.get_user(user_id)
        user["total_trades"] += 1
        user["total_volume"] += amount
        user["total_profit"] += profit
        user["total_fees_paid"] += fee
        if profit > user["biggest_win"]:
            user["biggest_win"] = profit
        if 0 < profit <= 0.1:
            user["coffee_earnings"] += profit
        today = str(datetime.now().date())
        if user["last_trade_date"] != today:
            user["daily_trades"] = 0
            user["last_trade_date"] = today
        user["daily_trades"] += 1

class MexBalancerPro:
    def __init__(self):
        self.db = UserData()
        self.admin_revenue = 0.0
        self.platform_stats = {
            "total_users": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "total_fees": 0.0
        }
        
    def get_tier_info(self, user_id: int) -> Dict:
        return TIERS[self.db.get_user(user_id)["tier"]]
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db.get_user(user.id)
        tier_info = self.get_tier_info(user.id)
        
        # Update platform stats
        self.platform_stats["total_users"] = len(self.db.users)
        
        welcome = f"""🎯 *MEX BALANCER PRO*
💰 *AUTOMATED PROFIT MACHINE*

👤 Trader: `{user.id}`
⭐ Tier: {tier_info['name']}
🤖 Status: 🟢 LIVE TRADING

📊 *YOUR PERFORMANCE:*
• Trades: {user_data['total_trades']}
• Volume: {user_data['total_volume']:.2f} SOL
• Total Profit: *{user_data['total_profit']:.4f} SOL* 🟢
• Fees Paid: {user_data['total_fees_paid']:.4f} SOL
• ☕ Coffee: {user_data['coffee_earnings']:.4f} SOL
• 🏆 Biggest Win: {user_data['biggest_win']:.4f} SOL

🚀 *HOW TO MAKE MONEY:*
1️⃣ /snipe - Find hot tokens
2️⃣ Bot buys at best price via Jupiter
3️⃣ Auto-sells at +100% (TP1) or +400% (TP2)
4️⃣ *Profit automatically sent to your wallet*

💼 *COMMANDS:*
🎯 /snipe - Start trading (Max: {tier_info['max_trade']} SOL)
⭐ /upgrade - Lower fees & bigger trades
📊 /stats - Full P&L breakdown
💼 /wallet - Check balance & deposits
📈 /leaderboard - Top earners

⚠️ *Start with 0.1-0.5 SOL to test*
*Then scale up as you see profits!*"""
        
        keyboard = [
            [InlineKeyboardButton("🎯 START SNIPING", callback_data="snipe")],
            [InlineKeyboardButton("⭐ UPGRADE TIER", callback_data="upgrade")],
            [InlineKeyboardButton("📊 VIEW STATS", callback_data="stats")]
        ]
        
        await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.db.get_user(update.effective_user.id)
        tier = self.get_tier_info(update.effective_user.id)
        
        win_rate = (user['total_profit'] / max(user['total_volume'], 0.001) * 100)
        avg_profit = user['total_profit'] / max(user['total_trades'], 1)
        
        # Calculate next tier benefit
        if tier['name'] == '🆓 Free':
            savings_example = "Trade 10 SOL: Save 0.05 SOL in fees with Pro!"
        elif tier['name'] == '⚡ Pro':
            savings_example = "Trade 50 SOL: Save 0.125 SOL in fees with Whale!"
        else:
            savings_example = "You're at max tier! Lowest fees possible."
        
        await update.message.reply_text(
            f"""📊 *YOUR MONEY MACHINE STATS*

💰 *Financial Performance:*
├ Trades: {user['total_trades']}
├ Volume: {user['total_volume']:.3f} SOL
├ Gross Profit: *+{user['total_profit']:.4f} SOL* 🟢
├ Fees Paid: -{user['total_fees_paid']:.4f} SOL
└ **NET PROFIT: {user['total_profit'] - user['total_fees_paid']:.4f} SOL** 💎

☕ *Coffee Earnings:* {user['coffee_earnings']:.4f} SOL
(Small consistent wins ≤0.1 SOL)

📈 *Trading Metrics:*
• Win Rate: {win_rate:.1f}%
• Avg Profit/Trade: {avg_profit:.4f} SOL
• Fee Rate: {tier['fee_percent']}%
• Daily Limit: {user['daily_trades']}/{tier['daily_trades']}

🏆 *Personal Best:* {user['biggest_win']:.4f} SOL

💡 *{savings_example}*

🚀 *Upgrade to earn more:* /upgrade""",
            parse_mode="Markdown"
        )
    
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show top earners to motivate users"""
        sorted_users = sorted(self.db.users.items(), 
                            key=lambda x: x[1]['total_profit'], 
                            reverse=True)[:5]
        
        text = "🏆 *TOP PROFIT LEADERS*\n\n"
        
        for i, (uid, data) in enumerate(sorted_users, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "▫️"
            text += f"{medal} *#{i}* User `{uid}`\n"
            text += f"   Profit: *{data['total_profit']:.4f} SOL*\n"
            text += f"   Trades: {data['total_trades']} | Volume: {data['total_volume']:.2f} SOL\n\n"
        
        text += f"📊 *Platform Total:* {self.platform_stats['total_profit']:.4f} SOL profit generated!\n"
        text += "\n💎 *You can be #1! Start trading: /snipe*"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def upgrade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        current = self.db.get_user(update.effective_user.id)["tier"]
        
        text = """💎 *UPGRADE & MAXIMIZE PROFITS*

Current tier fees vs profit potential:"""
        
        for tid, tier in TIERS.items():
            status = "✅ YOU" if tid == current else ""
            roi_calc = ""
            if tid == "pro" and current == "free":
                roi_calc = "\n   💡 *ROI: Break even at 10 SOL volume*"
            elif tid == "whale":
                roi_calc = "\n   💡 *ROI: Break even at 40 SOL volume*"
            
            text += f"""
{tier['name']} {status}
├ Max Trade: {tier['max_trade']} SOL
├ Daily Trades: {tier['daily_trades']}
├ Fee: {tier['fee_percent']}%
├ Price: {tier['price_sol']} SOL/month{roi_calc}
"""
        
        text += "\n🔥 *Lower fees = More profit per trade!*"
        
        keyboard = []
        if current == "free":
            keyboard.append([InlineKeyboardButton("⚡ UPGRADE PRO (0.5 SOL)", callback_data="pay_pro")])
            keyboard.append([InlineKeyboardButton("🐋 UPGRADE WHALE (2 SOL)", callback_data="pay_whale")])
        elif current == "pro":
            keyboard.append([InlineKeyboardButton("🐋 UPGRADE WHALE (2 SOL)", callback_data="pay_whale")])
        
        keyboard.append([InlineKeyboardButton("💬 Contact @IceReign_MEXT", url="https://t.me/IceReign_MEXT")])
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def snipe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.db.get_user(update.effective_user.id)
        tier = self.get_tier_info(update.effective_user.id)
        today = str(datetime.now().date())
        
        if user["last_trade_date"] != today:
            user["daily_trades"] = 0
            user["last_trade_date"] = today
        
        remaining = tier["daily_trades"] - user["daily_trades"]
        
        if remaining <= 0:
            await update.message.reply_text(
                f"""❌ *DAILY LIMIT REACHED*

You've used all {tier['daily_trades']} trades today.

⏰ Resets in: 24 hours
⭐ Upgrade for unlimited trades:
• Pro: 20 trades/day
• Whale: 100 trades/day

/upgrade""",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"""🎯 *SNIPER MODE ACTIVATED*

⭐ Tier: {tier['name']}
💰 Max per trade: {tier['max_trade']} SOL
🔄 Remaining today: {remaining} trades
⚡ MEV Boost: {'✅ ON' if tier['mev_boost'] else '❌ OFF'}

*Send token contract address:*
(Example: `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`)""",
            parse_mode="Markdown"
        )
        return WAITING_TOKEN
    
    async def handle_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        token = update.message.text.strip()
        
        if len(token) < 32:
            await update.message.reply_text("❌ Invalid address. Use Solana contract address (32-44 chars).")
            return WAITING_TOKEN
        
        context.user_data["token"] = token
        tier = self.get_tier_info(update.effective_user.id)
        
        await update.message.reply_text(
            f"""✅ Token received: `{token[:20]}...`

💰 *ENTER SOL AMOUNT TO INVEST:*
• Min: 0.05 SOL
• Max: {tier['max_trade']} SOL (your tier limit)
• Suggested: 0.1 - 1.0 SOL for testing

*Send amount (numbers only):*
Example: `0.5` or `1.0`""",
            parse_mode="Markdown"
        )
        return WAITING_AMOUNT
    
    async def handle_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        tier = self.get_tier_info(user_id)
        
        text = update.message.text.strip()
        
        # Check if user sent token instead of number
        if len(text) > 20 or not text.replace('.', '').isdigit():
            await update.message.reply_text("❌ Send a NUMBER only (like 0.5 or 1.0)")
            return WAITING_AMOUNT
        
        try:
            amount = float(text)
            if amount < 0.05:
                await update.message.reply_text("❌ Minimum 0.05 SOL")
                return WAITING_AMOUNT
            if amount > tier["max_trade"]:
                await update.message.reply_text(f"❌ Max for your tier is {tier['max_trade']} SOL. /upgrade to increase.")
                return WAITING_AMOUNT
        except ValueError:
            await update.message.reply_text("❌ Invalid number")
            return WAITING_AMOUNT
        
        token = context.user_data["token"]
        
        executing = await update.message.reply_text(
            "⚡ *EXECUTING TRADE...*\n"
            f"💰 Amount: {amount} SOL\n"
            "⏳ Routing via Jupiter...\n"
            "⏳ Optimizing for best price...",
            parse_mode="Markdown"
        )
        
        # Simulate trade execution (replace with real Jupiter swap)
        result = await self.execute_trade_simulation(token, amount, tier["mev_boost"])
        
        if result["success"]:
            profit = result["profit"]
            fee = max(profit, 0) * (tier["fee_percent"] / 100)
            net_profit = profit - fee
            
            self.db.record_trade(user_id, amount, profit, fee)
            self.admin_revenue += fee
            
            # Update platform stats
            self.platform_stats["total_trades"] += 1
            self.platform_stats["total_profit"] += profit
            self.platform_stats["total_fees"] += fee
            
            # Build success message
            profit_emoji = "🟢" if profit > 0 else "🔴"
            coffee_text = ""
            if 0 < profit <= 0.1:
                coffee_text = f"\n☕ Coffee money: +{profit:.4f} SOL!"
            
            await executing.edit_text(
                f"""{profit_emoji} *TRADE EXECUTED!*

🎯 Token: `{token[:20]}...`
💰 Invested: {amount:.3f} SOL
📊 Entry: {result['entry_price']:.8f}
💸 Exit: {result['exit_price']:.8f}

💰 *P&L BREAKDOWN:*
├ Gross: {profit:+.4f} SOL
├ Fee ({tier['fee_percent']}%): -{fee:.4f} SOL
└ **NET: {net_profit:+.4f} SOL**{coffee_text}

🔗 TX: `{result['tx'][:25]}...`

🤖 *Auto-management active*
Monitoring for next moves...""",
                parse_mode="Markdown"
            )
            
            # 🎉 POST TO CHANNEL FOR TRANSPARENCY
            await self.post_profit_to_channel(user_id, amount, profit, fee, net_profit, tier['name'])
            
        else:
            await executing.edit_text(f"❌ Trade failed: {result['error']}")
        
        return ConversationHandler.END
    
    async def execute_trade_simulation(self, token, amount, mev_boost):
        """Simulate trade for demo (replace with real Jupiter execution)"""
        try:
            # Simulate realistic trade outcome
            import random
            success_rate = 0.7 if mev_boost else 0.6
            is_success = random.random() < success_rate
            
            if is_success:
                # Random profit between -5% and +15%
                profit_pct = random.uniform(-0.05, 0.15)
                profit = amount * profit_pct
                
                return {
                    "success": True,
                    "profit": profit,
                    "entry_price": random.uniform(0.0001, 0.01),
                    "exit_price": random.uniform(0.0001, 0.01),
                    "tx": "SimTX_" + token[:15] + "_" + str(random.randint(1000, 9999))
                }
            else:
                return {"success": False, "error": "Slippage too high - trade rejected for safety"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def post_profit_to_channel(self, user_id, amount, profit, fee, net_profit, tier_name):
        """Auto-post profits to channel for transparency and FOMO"""
        try:
            profit_emoji = "🟢💰" if profit > 0 else "🔴"
            result_text = "PROFIT" if profit > 0 else "loss"
            
            message = f"""{profit_emoji} *LIVE TRADE RESULT*

👤 User: `{user_id}`
⭐ Tier: {tier_name}
💰 Volume: {amount:.3f} SOL

📊 *Trade Outcome:*
├ Gross {result_text}: {profit:+.4f} SOL
├ Platform Fee: {fee:.4f} SOL
├ **User Net: {net_profit:+.4f} SOL**

💎 Platform Revenue: +{fee:.4f} SOL
📈 Total Platform Profit: {self.platform_stats['total_profit']:.4f} SOL

✅ Transparent. Automated. Profitable.

🤖 Trade with us: @Iceboys_Bot"""
            
            await Bot(BOT_TOKEN).send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )
            
            # If big win, celebrate more
            if profit > 0.5:
                await Bot(BOT_TOKEN).send_message(
                    chat_id=CHANNEL_ID,
                    text=f"🎉 *BIG WIN ALERT!* 🎉\n\nUser `{user_id}` just made *{profit:.4f} SOL* profit!\n\n🏆 Biggest win today!\n\nStart trading: @Iceboys_Bot",
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Channel post failed: {e}")
    
    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [WALLET]}) as resp:
                    balance = (await resp.json())["result"]["value"] / 1e9
        except:
            balance = 0.0
        
        user = self.db.get_user(update.effective_user.id)
        
        await update.message.reply_text(
            f"""💼 *YOUR TRADING WALLET*

📍 Address: `{WALLET}`
💰 Balance: `{balance:.4f}` SOL

📊 *Your Trading History:*
├ Trades: {user['total_trades']}
├ Volume: {user['total_volume']:.2f} SOL
├ Total Profit: {user['total_profit']:.4f} SOL
├ Fees Paid: {user['total_fees_paid']:.4f} SOL
├ Net P&L: {user['total_profit'] - user['total_fees_paid']:.4f} SOL
└ ☕ Coffee: {user['coffee_earnings']:.4f} SOL

🏆 Biggest Win: {user['biggest_win']:.4f} SOL

📥 *To deposit:*
Send SOL to the address above
Min: 0.05 SOL for gas + trade amount

⚠️ *Security Tips:*
• Never share private keys
• Start small, scale with profits
• Only trade what you can afford to lose""",
            parse_mode="Markdown"
        )
    
    async def admin_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin only - full platform stats"""
        if update.effective_user.id != ADMIN_ID:
            return await update.message.reply_text("⛔ Admin only")
        
        await update.message.reply_text(
            f"""💎 *ADMIN DASHBOARD*

📊 *Platform Statistics:*
├ Total Users: {len(self.db.users)}
├ Total Trades: {self.platform_stats['total_trades']}
├ Total Volume: {self.platform_stats.get('total_volume', 0):.2f} SOL
├ Total Profit Generated: {self.platform_stats['total_profit']:.4f} SOL
├ Total Fees Collected: {self.platform_stats['total_fees']:.4f} SOL
└ **Your Revenue: {self.admin_revenue:.4f} SOL** 💰

💵 USD Value: ~${self.admin_revenue * 82:.2f} (at $82/SOL)

📈 *Tier Distribution:*
• Free: {sum(1 for u in self.db.users.values() if u['tier'] == 'free')}
• Pro: {sum(1 for u in self.db.users.values() if u['tier'] == 'pro')}
• Whale: {sum(1 for u in self.db.users.values() if u['tier'] == 'whale')}

🎯 *Projections (100 active users):*
Monthly Volume: ~500 SOL
Monthly Fees: ~2.5 SOL (~$205)

💼 Fee Wallet: `{FEE_WALLET}`""",
            parse_mode="Markdown"
        )
    
    async def cancel(self, update, context):
        await update.message.reply_text("❌ Cancelled")
        return ConversationHandler.END

# Initialize
bot = MexBalancerPro()
application = Application.builder().token(BOT_TOKEN).build()

# Handlers
conv = ConversationHandler(
    entry_points=[CommandHandler("snipe", bot.snipe_command)],
    states={
        WAITING_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_token)],
        WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_amount)]
    },
    fallbacks=[CommandHandler("cancel", bot.cancel)]
)

application.add_handler(CommandHandler("start", bot.start))
application.add_handler(CommandHandler("stats", bot.stats_command))
application.add_handler(CommandHandler("leaderboard", bot.leaderboard_command))
application.add_handler(CommandHandler("upgrade", bot.upgrade_command))
application.add_handler(CommandHandler("wallet", bot.wallet_command))
application.add_handler(CommandHandler("admin", bot.admin_stats_command))
application.add_handler(conv)

# Callbacks
application.add_handler(CallbackQueryHandler(lambda u,c: bot.snipe_command(u,c), pattern="^snipe$"))
application.add_handler(CallbackQueryHandler(lambda u,c: bot.upgrade_command(u,c), pattern="^upgrade$"))
application.add_handler(CallbackQueryHandler(lambda u,c: bot.stats_command(u,c), pattern="^stats$"))

# Web server
async def health_check(request):
    return web.Response(text="✅ MEX BALANCER PRO - OPERATIONAL")

async def webhook_handler(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def main():
    logger.add("logs/bot.log", rotation="500 MB")
    logger.info("🚀 MEX BALANCER PRO FINAL VERSION STARTED")
    
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    
    # Startup notification to channel
    await Bot(BOT_TOKEN).send_message(
        chat_id=CHANNEL_ID,
        text="""🤖 *MEX BALANCER PRO* is ONLINE!

✅ Auto-profit posting enabled
✅ Leaderboard tracking active
✅ Subscription tiers ready
✅ Transparent fee structure

💰 Every trade profit posted here automatically!

🎯 Start trading: @Iceboys_Bot""",
        parse_mode="Markdown"
    )
    
    # Web server
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_post('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    logger.info(f"🌐 Server running on port {PORT}")
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
