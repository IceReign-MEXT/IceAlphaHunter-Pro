import os
import sys
import logging
import asyncio
from telegram_bot import TelegramBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    try:
        logger.info("🚀 Starting IceAlphaHunter Pro...")
        
        required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'HELIUS_RPC_URL', 'WALLET_PRIVATE_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            logger.error(f"❌ Missing env vars: {', '.join(missing)}")
            sys.exit(1)
        
        bot = TelegramBot()
        await bot.start()
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
