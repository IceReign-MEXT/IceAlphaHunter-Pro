#!/usr/bin/env python3
"""IceAlpha Hunter Pro - With health endpoint"""
import os
import sys
import threading
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Create Flask app for health checks (keeps Render happy)
app = Flask(__name__)

@app.route('/')
def health():
    return {
        "status": "running",
        "bot": "IceAlpha Hunter Pro",
        "version": "1.0"
    }, 200

@app.route('/health')
def health_check():
    return {"status": "healthy"}, 200

def run_flask():
    """Run Flask in background thread"""
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)

def main():
    logger.info("🚀 Starting IceAlpha Hunter Pro...")
    
    from config import config
    
    if not config.is_configured:
        logger.error("❌ Missing config")
        sys.exit(1)
    
    logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
    logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
    logger.info(f"🌐 Health endpoint: http://0.0.0.0:{config.PORT}/health")
    
    # Start Flask for health checks
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Health endpoint started")
    
    # Start Telegram bot
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        raise

if __name__ == "__main__":
    main()
