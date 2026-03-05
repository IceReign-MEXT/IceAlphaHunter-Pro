#!/usr/bin/env python3
"""IceAlpha Hunter Pro - Sync version for Render"""
import os
import sys

from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting IceAlpha Hunter Pro...")
    
    from config import config
    
    if not config.is_configured:
        logger.error("❌ Missing config")
        logger.error("Need: BOT_TOKEN, HELIUS_API_KEY, WALLET_PUBLIC_KEY")
        sys.exit(1)
    
    logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
    logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
    
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
