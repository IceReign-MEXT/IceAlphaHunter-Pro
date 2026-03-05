#!/usr/bin/env python3
"""IceAlpha Hunter Pro"""
import os
import sys

# Ensure .env is loaded first
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting IceAlpha Hunter Pro...")
    
    from config import config
    
    if not config.is_configured:
        logger.error("❌ Missing config")
        logger.error("Need: BOT_TOKEN, HELIUS_API_KEY, WALLET_PUBLIC_KEY")
        sys.exit(1)
    
    logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
    logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
    logger.info(f"💾 Database: {'PostgreSQL' if config.DATABASE_URL else 'SQLite'}")
    
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
