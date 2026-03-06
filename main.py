#!/usr/bin/env python3
"""IceAlpha Hunter Pro"""
import asyncio
import logging
import sys
from telegram_bot import TelegramBot
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def main():
    """Main"""
    logger.info("🚀 Starting IceAlpha Hunter Pro...")
    
    if not config.is_configured:
        logger.error("❌ Missing config. Check .env")
        logger.error("Need: BOT_TOKEN, HELIUS_API_KEY, WALLET_PRIVATE_KEY, DATABASE_URL")
        sys.exit(1)
    
    logger.info("✅ Config valid")
    logger.info(f"💰 Auto-trade: {'ON' if config.AUTO_TRADE_ENABLED else 'OFF'}")
    logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD:,.0f}")
    
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
