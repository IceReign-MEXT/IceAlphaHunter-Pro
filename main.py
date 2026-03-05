#!/usr/bin/env python3
"""IceAlpha Hunter Pro - With Instance Lock"""
import sys
import os
import fcntl  # File lock to prevent double instances

# Add imghdr shim BEFORE anything else
if 'imghdr' not in sys.modules:
    import types
    imghdr = types.ModuleType('imghdr')
    imghdr.what = lambda filename, h=None: None
    sys.modules['imghdr'] = imghdr

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# INSTANCE LOCK - Prevents multiple bots running
LOCK_FILE = '/tmp/icealpha_bot.lock'

def acquire_lock():
    """Prevent multiple bot instances"""
    try:
        global lock_fd
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        logger.info("🔒 Instance lock acquired")
        return True
    except IOError:
        logger.error("❌ Another bot instance is already running!")
        logger.error("Wait 30 seconds and try again, or check Render dashboard")
        return False

def release_lock():
    """Release lock on exit"""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        os.remove(LOCK_FILE)
    except:
        pass

def main():
    """Main entry point"""
    if not acquire_lock():
        sys.exit(1)
    
    try:
        logger.info("🚀 Starting IceAlpha Hunter Pro...")
        
        from config import config
        
        if not config.is_configured:
            logger.error("❌ Missing config: BOT_TOKEN, HELIUS_API_KEY, or WALLET_PUBLIC_KEY")
            sys.exit(1)
        
        logger.info(f"💰 Auto-trade: {config.AUTO_TRADE_ENABLED}")
        logger.info(f"🎯 Min whale: ${config.MIN_WHALE_AMOUNT_USD}")
        
        from telegram_bot import TelegramBot
        bot = TelegramBot()
        
        try:
            bot.run()
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
    finally:
        release_lock()

if __name__ == "__main__":
    main()
