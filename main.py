#!/usr/bin/env python3
"""IceAlpha Hunter Pro - Main Entry"""
import sys
import os
import asyncio
import logging
import threading
from flask import Flask, jsonify

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_running = False

@app.route('/')
def health():
    return jsonify({"status": "healthy", "service": "IceAlpha Hunter Pro", "version": "2.0"})

@app.route('/status')
def status():
    return jsonify({
        "bot_running": bot_running,
        "auto_trade": os.getenv("AUTO_TRADE_ENABLED", "false"),
        "wallet": os.getenv("WALLET_PUBLIC_KEY", "")[:8] + "..." if os.getenv("WALLET_PUBLIC_KEY") else "Not set"
    })

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

async def main_async():
    global bot_running
    
    from config import config
    from database import db
    from wallet import wallet
    from telegram_bot import telegram_bot
    from trading_engine import trading_engine
    from whale_monitor import whale_monitor
    
    if not config.is_configured:
        logger.error("❌ Missing configuration!")
        logger.error("Required: BOT_TOKEN, HELIUS_API_KEY, WALLET_PUBLIC_KEY, DATABASE_URL")
        return 1
    
    logger.info(f"🚀 Starting IceAlpha Hunter Pro...")
    logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
    logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
    logger.info(f"💳 Wallet: {wallet.address[:8]}...")
    
    try:
        await trading_engine.start()
        await whale_monitor.start()
        bot_running = True
        telegram_bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    finally:
        bot_running = False
        await whale_monitor.stop()
        await trading_engine.stop()
        telegram_bot.stop()
    return 0

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Health check server started")
    
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Main error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
