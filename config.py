"""Configuration"""
import os
from dotenv import load_dotenv

# Load .env immediately
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
    CHANNEL_ID = os.getenv("CHANNEL_ID", "")
    
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
    HELIUS_RPC_URL = os.getenv("HELIUS_RPC_URL", "")
    WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")
    WALLET_PUBLIC_KEY = os.getenv("WALLET_PUBLIC_KEY", "")
    
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    MIN_WHALE_AMOUNT_USD = float(os.getenv("MIN_WHALE_AMOUNT_USD", "1000"))
    MAX_POSITION_SOL = float(os.getenv("MAX_POSITION_SOL", "1.0"))
    SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS", "100"))
    AUTO_TRADE_ENABLED = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    PORT = int(os.getenv("PORT", "10000"))
    
    JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6"
    JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
    
    @property
    def is_configured(self):
        return all([self.BOT_TOKEN, self.HELIUS_API_KEY, self.WALLET_PUBLIC_KEY])

config = Config()
