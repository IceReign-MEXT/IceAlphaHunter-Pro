import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Bot configuration"""
    
    MIN_WHALE_SIZE = int(os.getenv('MIN_WHALE_SIZE', '5000'))
    MAX_POSITION_SOL = float(os.getenv('MAX_POSITION_SOL', '10.0'))
    SLIPPAGE = float(os.getenv('SLIPPAGE', '1.0'))
    TAKE_PROFIT = float(os.getenv('TAKE_PROFIT', '20.0'))
    STOP_LOSS = float(os.getenv('STOP_LOSS', '-10.0'))
    AUTO_TRADE = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
    
    HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')
    HELIUS_RPC_URL = os.getenv('HELIUS_RPC_URL')
    JUPITER_API_URL = os.getenv('JUPITER_API_URL', 'https://quote-api.jup.ag/v6')
    RUGCHECK_API_KEY = os.getenv('RUGCHECK_API_KEY')
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY')
    
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', TELEGRAM_CHAT_ID)
    
    JITO_BLOCK_ENGINE_URL = os.getenv('JITO_BLOCK_ENGINE_URL', 'https://mainnet.block-engine.jito.wtf')
    JITO_TIP_ACCOUNT = os.getenv('JITO_TIP_ACCOUNT', '96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5')
    
    @classmethod
    def reload(cls):
        load_dotenv(override=True)
        cls.MIN_WHALE_SIZE = int(os.getenv('MIN_WHALE_SIZE', '5000'))
        cls.MAX_POSITION_SOL = float(os.getenv('MAX_POSITION_SOL', '10.0'))
        cls.SLIPPAGE = float(os.getenv('SLIPPAGE', '1.0'))
        cls.AUTO_TRADE = os.getenv('AUTO_TRADE', 'true').lower() == 'true'
