import os
import sys
import logging
import asyncio
from telegram_bot import TelegramBot

# Configure logging immediately
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
        
        # Check environment variables
        required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'HELIUS_RPC_URL', 'WALLET_PRIVATE_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
            sys.exit(1)
        
        # Initialize and start bot
        bot = TelegramBot()
        await bot.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
