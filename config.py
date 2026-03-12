"""Centralized configuration management"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
    
    # Solana
    HELIUS_API_KEY: str = os.getenv("HELIUS_API_KEY", "")
    HELIUS_RPC_URL: str = os.getenv("HELIUS_RPC_URL", "")
    WALLET_PRIVATE_KEY: str = os.getenv("WALLET_PRIVATE_KEY", "")
    WALLET_PUBLIC_KEY: str = os.getenv("WALLET_PUBLIC_KEY", "")
    
    # Database (PostgreSQL direct)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Trading Settings
    MIN_WHALE_AMOUNT_USD: float = float(os.getenv("MIN_WHALE_AMOUNT_USD", "5000"))
    MAX_POSITION_SOL: float = float(os.getenv("MAX_POSITION_SOL", "10"))
    SLIPPAGE_BPS: int = int(os.getenv("SLIPPAGE_BPS", "100"))
    JITO_TIP_LAMPORTS: int = int(os.getenv("JITO_TIP_LAMPORTS", "10000"))
    AUTO_TRADE_ENABLED: bool = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
    
    # Server
    PORT: int = int(os.getenv("PORT", "10000"))
    
    # Jupiter API
    JUPITER_QUOTE_API: str = "https://quote-api.jup.ag/v6"
    JUPITER_SWAP_API: str = "https://quote-api.jup.ag/v6/swap"
    
    @property
    def is_configured(self) -> bool:
        """Check if critical config is present"""
        return all([
            self.BOT_TOKEN,
            self.HELIUS_API_KEY,
            self.WALLET_PUBLIC_KEY,
            self.DATABASE_URL
        ])
    
    @property
    def channel_id_int(self) -> int:
        """Get channel ID as integer"""
        try:
            return int(self.CHANNEL_ID)
        except:
            return 0

config = Config()
