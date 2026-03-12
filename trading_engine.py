"""Trading Engine"""
import asyncio
import aiohttp
from typing import Dict, Optional
from decimal import Decimal
import logging
from config import config
from wallet import wallet
from database import db

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.is_running = True
        logger.info("✅ Trading engine started")
    
    async def stop(self):
        self.is_running = False
        if self.session:
            await self.session.close()
    
    async def get_token_price(self, token_address: str) -> Optional[Decimal]:
        try:
            url = f"{config.JUPITER_QUOTE_API}/quote"
            params = {
                "inputMint": token_address,
                "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "amount": "1000000000",
                "slippageBps": "50"
            }
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    out_amount = int(data.get("outAmount", 0))
                    return Decimal(out_amount) / Decimal(1_000_000)
                return None
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            return None
    
    async def buy_token(self, token_address: str, amount_sol: float) -> bool:
        if not config.AUTO_TRADE_ENABLED:
            logger.info("Auto-trading disabled")
            return False
        
        try:
            db.save_trade({
                "tx_signature": f"pending_{token_address[:8]}",
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
    
    async def sell_token(self, token_address: str, percentage: float = 100) -> bool:
        if not config.AUTO_TRADE_ENABLED:
            return False
        logger.info(f"🔴 Sell order: {percentage}% of {token_address[:8]}")
        return True

trading_engine = TradingEngine()
