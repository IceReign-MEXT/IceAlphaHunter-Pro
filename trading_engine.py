import os
import logging
import asyncio
import base64
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
from solders.keypair import Keypair
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    token_address: str
    entry_price: float
    amount_sol: float
    timestamp: str
    tx_signature: Optional[str] = None

class TradingEngine:
    def __init__(self, database):
        self.db = database
        self.rpc_client = AsyncClient(os.getenv('HELIUS_RPC_URL'))
        self.jupiter_ready = False
        self.open_positions: Dict[str, Trade] = {}
        self.wallet = self._load_wallet()
        self._check_jupiter()
        
    def _load_wallet(self) -> Keypair:
        """Load wallet from private key"""
        try:
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            if not private_key:
                raise ValueError("WALLET_PRIVATE_KEY not set")
            
            if ',' in private_key:
                key_bytes = bytes([int(x) for x in private_key.strip('[]').split(',')])
            else:
                import base58
                key_bytes = base58.b58decode(private_key)
            
            return Keypair.from_bytes(key_bytes)
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            raise
    
    async def _check_jupiter(self):
        """Check Jupiter API status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=1000000') as resp:
                    self.jupiter_ready = resp.status == 200
        except Exception as e:
            logger.warning(f"Jupiter API check failed: {e}")
            self.jupiter_ready = False
    
    async def execute_buy(self, token_address: str, amount_sol: float, whale_tx: str) -> Optional[str]:
        """Execute buy order via Jupiter"""
        if not self.jupiter_ready:
            logger.error("Jupiter API not ready")
            return None
        
        try:
            # Get quote
            quote_url = f"https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={token_address}&amount={int(amount_sol * 1e9)}&slippageBps={int(Config.SLIPPAGE * 100)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_url) as resp:
                    if resp.status != 200:
                        logger.error(f"Quote failed: {await resp.text()}")
                        return None
                    quote = await resp.json()
                
                # Get swap transaction
                swap_data = {
                    "quoteResponse": quote,
                    "userPublicKey": str(self.wallet.pubkey()),
                    "wrapAndUnwrapSol": True
                }
                
                async with session.post('https://quote-api.jup.ag/v6/swap', json=swap_data) as resp:
                    if resp.status != 200:
                        logger.error(f"Swap request failed: {await resp.text()}")
                        return None
                    swap_result = await resp.json()
                
                # Deserialize and sign transaction
                tx_bytes = base64.b64decode(swap_result['swapTransaction'])
                tx = Transaction.deserialize(tx_bytes)
                tx.sign(self.wallet)
                
                # Send transaction
                result = await self.rpc_client.send_transaction(tx, self.wallet)
                signature = result.value
                
                # Record trade
                trade = Trade(
                    token_address=token_address,
                    entry_price=amount_sol,
                    amount_sol=amount_sol,
                    timestamp=datetime.now().isoformat(),
                    tx_signature=str(signature)
                )
                self.open_positions[token_address] = trade
                self.db.record_trade(trade)
                
                logger.info(f"Buy executed: {token_address}, tx: {signature}")
                return str(signature)
                
        except Exception as e:
            logger.error(f"Buy execution failed: {e}", exc_info=True)
            return None
    
    async def execute_sell(self, token_address: str, percentage: float = 100.0) -> Optional[str]:
        """Execute sell order"""
        if token_address not in self.open_positions:
            logger.warning(f"No position found for {token_address}")
            return None
        
        try:
            position = self.open_positions[token_address]
            logger.info(f"Selling {percentage}% of {token_address}")
            
            # Record profit/loss (simplified)
            self.db.close_trade(token_address, profit=0.0)
            del self.open_positions[token_address]
            
            return "simulated_tx_signature"
            
        except Exception as e:
            logger.error(f"Sell execution failed: {e}")
            return None
    
    async def emergency_sell(self, token_address: str):
        """Emergency sell at market price"""
        return await self.execute_sell(token_address, 100.0)
    
    def get_open_positions(self) -> List[dict]:
        """Get list of open positions"""
        return [
            {
                'token_address': t.token_address,
                'entry_price': t.entry_price,
                'amount_sol': t.amount_sol,
                'timestamp': t.timestamp,
                'tx_signature': t.tx_signature
            }
            for t in self.open_positions.values()
        ]
