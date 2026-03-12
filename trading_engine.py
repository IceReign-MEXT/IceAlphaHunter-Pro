"""Trading Engine - Synchronous Version"""
import requests
from typing import Dict, Optional
from decimal import Decimal
import logging
from config import config
from wallet import wallet
from database import db

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self):
        self.session = requests.Session()
        self.is_running = False
    
    def start(self):
        self.is_running = True
        logger.info("✅ Trading engine started")
    
    def stop(self):
        self.is_running = False
        self.session.close()
    
    def get_token_price(self, token_address: str) -> Optional[Decimal]:
        try:
            url = f"{config.JUPITER_QUOTE_API}/quote"
            params = {
                "inputMint": token_address,
                "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "amount": "1000000000",
                "slippageBps": "50"
            }
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                out_amount = int(data.get("outAmount", 0))
                return Decimal(out_amount) / Decimal(1_000_000)
            return None
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            return None
    
    def buy_token(self, token_address: str, amount_sol: float) -> bool:
        if not config.AUTO_TRADE_ENABLED:
            logger.info("Auto-trading disabled")
            return False
        
        try:
            db.save_trade({
                "tx_signature": f"pending_{token_address[:8]}_{int(time.time())}",
                "token_address": token_address,
                "token_symbol": "UNKNOWN",
                "entry_price": 0,
                "amount": amount_sol,
                "status": "pending"
            })
            logger.info(f"🟢 Buy order: {amount_sol} SOL -> {token_address[:8]}")
            return True
        except Exception as e:
            logger.error(f"Buy error: {e}")
            return False
    
    def sell_token(self, token_address: str, percentage: float = 100) -> bool:
        if not config.AUTO_TRADE_ENABLED:
            return False
        logger.info(f"🔴 Sell order: {percentage}% of {token_address[:8]}")
        return True

import time
trading_engine = TradingEngine()
