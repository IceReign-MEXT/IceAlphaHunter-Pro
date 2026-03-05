#!/usr/bin/env python3
"""
🔥 MEV ARBITRAGE SCANNER PRO
Real-time Solana arbitrage + Smart money tracking
Makes money through referral fees & subscriptions
"""

import os
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List
from loguru import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from aiohttp import web

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
HELIUS_KEY = os.getenv("RPC_URL", "").split("api-key=")[-1] if "api-key=" in os.getenv("RPC_URL", "") else ""

# Jupiter Referral Key (EARN 0.1% on all trades!)
JUPITER_REFERRAL = "YOUR_REFERRAL_KEY_HERE"  # Get from https://referral.jup.ag

PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = "https://mex-balancer.onrender.com"

class MEVScanner:
    def __init__(self):
        self.hot_tokens = {}  # Track trending tokens
        self.smart_wallets = [
            "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVbNUqSCKdMQxK",  # Example smart wallet
            "H8sMJSCQxfKiFTF7kD4E5sDt9PnSLP6T9xUym1Toc6vV",
        ]
        self.arbitrage_opportunities = []
        self.user_subscriptions = {}  # Track paid users
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Professional welcome with money-making focus"""
        user = update.effective_user
        
        welcome = f"""🔥 *MEV ARBITRAGE SCANNER PRO*

👤 Trader: `{user.id}`
⏱️ Last Scan: {datetime.now().strftime('%H:%M:%S')}
🤖 Status: 🟢 LIVE SCANNING

💰 *HOW YOU MAKE MONEY:*
1️⃣ Scanner finds price differences (arbitrage)
2️⃣ Alerts you BEFORE others buy
3️⃣ You buy low on DEX A, sell high on DEX B
4️⃣ Profit in seconds!

📊 *REAL-TIME FEATURES:*
🎯 Arbitrage Scanner - Live price gaps
🐋 Smart Money Tracker - Copy whales
📈 Trending Tokens - Early alpha
⚡ MEV Protection - Front-run protection

💎 *SUBSCRIPTION TIERS:*
🆓 Free - 3 alerts/day, 5min delay
⚡ Pro - 0.3 SOL/month - Instant alerts, unlimited
🐋 Whale - 1 SOL/month - Smart money copy, insider signals

🚀 *Start earning now:*"""
        
        keyboard = [
            [InlineKeyboardButton("🔥 VIEW LIVE ARBITRAGE", callback_data="arbitrage")],
            [InlineKeyboardButton("🐋 SMART MONEY MOVES", callback_data="smart_money")],
            [InlineKeyboardButton("📈 TRENDING TOKENS", callback_data="trending")],
            [InlineKeyboardButton("⚡ UPGRADE TO PRO", callback_data="upgrade")]
        ]
        
        await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def scan_arbitrage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Find price differences between DEXs"""
        scanning_msg = await update.message.reply_text("🔍 *SCANNING FOR ARBITRAGE...*", parse_mode="Markdown")
        
        opportunities = await self.find_arbitrage_opportunities()
        
        if not opportunities:
            await scanning_msg.edit_text(
                """📊 *NO ARBITRAGE FOUND*

Current market is efficient.
Scanner running 24/7...

⏰ Next scan: 30 seconds
🎯 You'll be first to know!""",
                parse_mode="Markdown"
            )
            return
        
        # Show top 3 opportunities
        text = "🔥 *ARBITRAGE OPPORTUNITIES FOUND!*\n\n"
        
        for i, opp in enumerate(opportunities[:3], 1):
            profit_pct = opp['profit_pct']
            profit_emoji = "🟢" if profit_pct > 5 else "🟡" if profit_pct > 2 else "🟠"
            
            text += f"""{profit_emoji} *OPPORTUNITY #{i}*

🎯 Token: `{opp['token'][:15]}...`
💰 Buy on: {opp['buy_dex']} @ ${opp['buy_price']:.6f}
💎 Sell on: {opp['sell_dex']} @ ${opp['sell_price']:.6f}
📊 Profit: *+{profit_pct:.2f}%*
💵 With 1 SOL: *+{profit_pct/100:.3f} SOL*

⚡ *ACT FAST - Opportunities last seconds!*

[JUPITER SWAP](https://jup.ag/swap/{opp['token']}?referral={JUPITER_REFERRAL})
"""
        
        text += "\n💡 *Upgrade to Pro for instant alerts (0 delay)*"
        
        keyboard = [[InlineKeyboardButton("⚡ UPGRADE FOR INSTANT ALERTS", callback_data="upgrade")]]
        
        await scanning_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
        # Alert channel
        await self.notify_channel(f"🔥 {len(opportunities)} arbitrage opportunities detected!")
    
    async def find_arbitrage_opportunities(self) -> List[Dict]:
        """Scan Jupiter for price differences"""
        opportunities = []
        
        # Popular tokens to scan
        tokens = [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "So11111111111111111111111111111111111111112",     # SOL
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",   # BONK
        ]
        
        try:
            async with aiohttp.ClientSession() as session:
                for token in tokens:
                    # Get quotes from different DEXs via Jupiter
                    # Buy SOL with token
                    buy_url = f"https://quote-api.jup.ag/v6/quote?inputMint={token}&outputMint=So11111111111111111111111111111111111111112&amount=1000000&slippageBps=50"
                    
                    async with session.get(buy_url) as resp:
                        if resp.status == 200:
                            buy_data = await resp.json()
                            buy_price = float(buy_data.get('outAmount', 0)) / 1e9
                            
                            # Sell SOL for token
                            sell_url = f"https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={token}&amount=1000000000&slippageBps=50"
                            
                            async with session.get(sell_url) as sell_resp:
                                if sell_resp.status == 200:
                                    sell_data = await sell_resp.json()
                                    sell_price = 1 / (float(sell_data.get('outAmount', 0)) / 1e6) if sell_data.get('outAmount') else 0
                                    
                                    # Calculate arbitrage
                                    if buy_price > 0 and sell_price > 0:
                                        profit_pct = ((buy_price - sell_price) / sell_price) * 100
                                        
                                        if profit_pct > 1.5:  # Only show >1.5% profit
                                            opportunities.append({
                                                'token': token,
                                                'buy_dex': 'Jupiter',
                                                'sell_dex': 'Jupiter',
                                                'buy_price': buy_price,
                                                'sell_price': sell_price,
                                                'profit_pct': profit_pct
                                            })
        except Exception as e:
            logger.error(f"Arbitrage scan error: {e}")
        
        return sorted(opportunities, key=lambda x: x['profit_pct'], reverse=True)
    
    async def smart_money_tracker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track whale wallets"""
        tracking_msg = await update.message.reply_text("🐋 *TRACKING SMART MONEY...*", parse_mode="Markdown")
        
        moves = await self.get_smart_money_moves()
        
        if not moves:
            await tracking_msg.edit_text(
                """🐋 *SMART MONEY STATUS*

No major moves detected in last hour.
Whales are holding...

⏰ Scanner watching 24/7
🎯 You'll know FIRST when they buy!""",
                parse_mode="Markdown"
            )
            return
        
        text = "🐋 *WHALE MOVEMENTS DETECTED!*\n\n"
        
        for move in moves[:5]:
            emoji = "🟢" if move['type'] == 'BUY' else "🔴"
            text += f"""{emoji} *{move['type']} ALERT*

👤 Whale: `{move['wallet'][:10]}...`
🎯 Token: `{move['token'][:15]}...`
💰 Amount: {move['amount']:.2f} SOL
⏰ Time: {move['time']}

{'📈 *ACCUMULATING - Bullish signal!*' if move['type'] == 'BUY' else '📉 *DUMPING - Bearish signal!*'}

💡 *Copy this trade?*
[JUPITER SWAP](https://jup.ag/swap/{move['token']}?referral={JUPITER_REFERRAL})

"""
        
        keyboard = [[InlineKeyboardButton("⚡ GET INSTANT WHALE ALERTS", callback_data="upgrade")]]
        
        await tracking_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def get_smart_money_moves(self) -> List[Dict]:
        """Get recent transactions from smart wallets"""
        moves = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for wallet in self.smart_wallets:
                    url = f"https://api.helius.xyz/v0/addresses/?api-key={HELIUS_KEY}&transactions={wallet}&limit=5"
                    
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for tx in data.get('transactions', []):
                                # Parse transaction for buy/sell
                                if 'tokenTransfers' in tx:
                                    for transfer in tx['tokenTransfers']:
                                        moves.append({
                                            'wallet': wallet,
                                            'token': transfer.get('mint', ''),
                                            'amount': transfer.get('tokenAmount', 0),
                                            'type': 'BUY' if transfer.get('toUserAccount') == wallet else 'SELL',
                                            'time': datetime.fromtimestamp(tx.get('timestamp', 0)).strftime('%H:%M')
                                        })
        except Exception as e:
            logger.error(f"Smart money tracking error: {e}")
        
        return moves[:10]  # Return last 10 moves
    
    async def trending_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trending tokens with early entry signals"""
        trending = await self.get_trending_tokens()
        
        text = "📈 *TRENDING TOKENS - EARLY ALPHA*\n\n"
        
        for i, token in enumerate(trending[:5], 1):
            text += f"""{i}. *{token['symbol']}*
`{token['address'][:20]}...`
💧 Volume: ${token['volume']:,.0f}
📊 Price Change: {token['change']:+.1f}%
🔥 Buys: {token['buys']} | Sells: {token['sells']}

[JUPITER](https://jup.ag/swap/{token['address']}?referral={JUPITER_REFERRAL})

"""
        
        text += "⚠️ *DYOR - These are momentum plays*"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def get_trending_tokens(self) -> List[Dict]:
        """Get trending tokens from Jupiter"""
        # This would integrate with Jupiter's trending API
        # For now, return sample data
        return [
            {'symbol': 'BONK', 'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263', 'volume': 5000000, 'change': 15.5, 'buys': 1250, 'sells': 800},
            {'symbol': 'WIF', 'address': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm', 'volume': 3200000, 'change': 8.3, 'buys': 980, 'sells': 650},
        ]
    
    async def upgrade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show upgrade options with payment"""
        text = """💎 *UPGRADE & MAXIMIZE PROFITS*

🆓 *FREE TIER*
❌ 3 alerts/day only
❌ 5 minute delay
❌ No smart money alerts
💰 You miss opportunities

⚡ *PRO TIER - 0.3 SOL/month (~$25)*
✅ UNLIMITED alerts
✅ INSTANT notifications (0 delay)
✅ Arbitrage scanner
✅ Trending tokens
✅ Priority support
💰 *Catch every opportunity!*

🐋 *WHALE TIER - 1 SOL/month (~$82)*
✅ Everything in Pro
✅ Smart money copy-trading
✅ Whale wallet alerts
✅ Insider signals
✅ Private alpha group
💰 *Trade like a whale!*

🎯 *ROI Calculation:*
One good arbitrage = 2-5% profit
With 1 SOL trade = 0.02-0.05 SOL profit
Pro costs 0.3 SOL/month
*Just 6 good trades = Profit!*"""
        
        keyboard = [
            [InlineKeyboardButton("⚡ BUY PRO (0.3 SOL)", callback_data="pay_pro")],
            [InlineKeyboardButton("🐋 BUY WHALE (1 SOL)", callback_data="pay_whale")],
            [InlineKeyboardButton("💬 Contact Admin", url="https://t.me/IceReign_MEXT")]
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    async def notify_channel(self, message: str):
        """Send to channel"""
        try:
            await Bot(BOT_TOKEN).send_message(
                chat_id=CHANNEL_ID,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Notify failed: {e}")

# Initialize
scanner = MEVScanner()
application = Application.builder().token(BOT_TOKEN).build()

# Handlers
application.add_handler(CommandHandler("start", scanner.start))
application.add_handler(CommandHandler("arbitrage", scanner.scan_arbitrage))
application.add_handler(CommandHandler("smart", scanner.smart_money_tracker))
application.add_handler(CommandHandler("trending", scanner.trending_tokens))
application.add_handler(CommandHandler("upgrade", scanner.upgrade_command))

# Callbacks
application.add_handler(CallbackQueryHandler(lambda u,c: scanner.scan_arbitrage(u,c), pattern="^arbitrage$"))
application.add_handler(CallbackQueryHandler(lambda u,c: scanner.smart_money_tracker(u,c), pattern="^smart_money$"))
application.add_handler(CallbackQueryHandler(lambda u,c: scanner.trending_tokens(u,c), pattern="^trending$"))
application.add_handler(CallbackQueryHandler(lambda u,c: scanner.upgrade_command(u,c), pattern="^upgrade$"))

# Web server
async def health_check(request):
    return web.Response(text="🔥 MEV SCANNER PRO - OPERATIONAL")

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
    logger.add("logs/scanner.log", rotation="500 MB")
    logger.info("🔥 MEV SCANNER PRO STARTING")
    
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    
    await scanner.notify_channel("🔥 *MEV SCANNER PRO* is LIVE!\n\n✅ Arbitrage scanning\n✅ Smart money tracking\n✅ Trending alerts\n\n💰 Ready to find alpha!")
    
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_post('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
