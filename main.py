#!/usr/bin/env python3
"""IceAlpha Hunter Pro - MEV Whale Sniper Bot"""
import asyncio
import logging
import sys
from telegram_bot import TelegramBot
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    logger.info("🚀 Starting IceAlpha Hunter Pro...")
    
    # Validate configuration
    if not config.is_configured:
        logger.error("❌ Missing critical configuration. Check .env file.")
        logger.error("Required: BOT_TOKEN, HELIUS_API_KEY, WALLET_PRIVATE_KEY, DATABASE_URL")
        sys.exit(1)
    
    logger.info("✅ Configuration validated")
    logger.info(f"💰 Auto-trading: {'ENABLED' if config.AUTO_TRADE_ENABLED else 'DISABLED'}")
    logger.info(f"🎯 Min whale size: ${config.MIN_WHALE_AMOUNT_USD:,.0f}")
    
    # Initialize and run bot
    bot = TelegramBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
