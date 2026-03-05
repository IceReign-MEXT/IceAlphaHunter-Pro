#!/usr/bin/env python3
"""IceAlpha Hunter Pro - Robust Background Worker"""
import os
import sys
import traceback
from dotenv import load_dotenv

# Load .env FIRST before any other imports
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("🚀 Starting IceAlpha Hunter Pro...")
        
        # Check config
        from config import config
        logger.info(f"Config loaded: BOT_TOKEN={'✅' if config.BOT_TOKEN else '❌'}, "
                   f"HELIUS={'✅' if config.HELIUS_API_KEY else '❌'}, "
                   f"WALLET={'✅' if config.WALLET_PUBLIC_KEY else '❌'}")
        
        if not config.is_configured:
            logger.error("❌ Missing required configuration!")
            logger.error("Required: BOT_TOKEN, HELIUS_API_KEY, WALLET_PUBLIC_KEY")
            sys.exit(1)
        
        logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
        logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
        logger.info(f"🔗 Database URL: {'✅ Set' if config.DATABASE_URL else '⚠️ Not set (will use SQLite)'}")
        
        # Initialize database with error handling
        logger.info("💾 Initializing database...")
        try:
            from database import db
            logger.info("✅ Database initialized")
        except Exception as db_error:
            logger.error(f"❌ Database failed: {db_error}")
            logger.info("🔄 Continuing without database persistence...")
            db = None
        
        # Initialize trading engine
        logger.info("⚙️ Initializing trading engine...")
        from trading_engine import TradingEngine
        engine = TradingEngine()
        logger.info("✅ Trading engine ready")
        
        # Start bot
        logger.info("🤖 Starting Telegram bot...")
        from telegram_bot import TelegramBot
        bot = TelegramBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
