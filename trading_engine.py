"""Trading Engine - Solders-free version for Termux"""
import aiohttp
import asyncio
import base58
from typing import Dict, Optional, Any
from dataclasses import dataclass
from config import config

@dataclass
class SwapResult:
    success: bool
    signature: Optional[str]
    error: Optional[str]
    input_amount: float
    output_amount: float
    price_impact: float

class TradingEngine:
    def __init__(self):
        self.wallet_public = config.WALLET_PUBLIC_KEY
        self.rpc_url = config.HELIUS_RPC_URL
        self.jupiter_quote_url = config.JUPITER_QUOTE_API
        self.jupiter_swap_url = config.JUPITER_SWAP_API
        self.slippage_bps = config.SLIPPAGE_BPS
        
        print(f"⚠️  TradingEngine initialized in MONITOR-ONLY mode")
        print(f"   Wallet: {self.wallet_public[:20]}...")
        print(f"   Auto-trade: {config.AUTO_TRADE_ENABLED}")
    
    async def get_quote(self, input_mint: str, output_mint: str, 
                       amount_lamports: int) -> Optional[Dict]:
        """Get Jupiter quote"""
        url = f"{self.jupiter_quote_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_lamports),
            "slippageBps": self.slippage_bps
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception as e:
            print(f"Quote error: {e}")
            return None
    
    async def buy_token(self, token_mint: str, sol_amount: float) -> SwapResult:
        """Buy token (simulated in Termux)"""
        if not config.AUTO_TRADE_ENABLED:
            return SwapResult(
                success=False, 
                error="AUTO_TRADE_DISABLED", 
                signature=None,
                input_amount=sol_amount,
                output_amount=0,
                price_impact=0
            )
        
        # In production on Render, this would execute real swap
        # For Termux testing, we simulate
        print(f"📝 SIMULATED BUY: {sol_amount} SOL -> {token_mint[:8]}...")
        return SwapResult(
            success=True,
            signature="SIMULATED_" + token_mint[:8],
            error=None,
            input_amount=sol_amount,
            output_amount=sol_amount * 100,  # Simulated
            price_impact=0.5
        )
    
    async def sell_token(self, token_mint: str, token_amount: float,
                         decimals: int = 9) -> SwapResult:
        """Sell token (simulated in Termux)"""
        print(f"📝 SIMULATED SELL: {token_amount} tokens -> SOL")
        return SwapResult(
            success=True,
            signature="SIMULATED_SELL_" + token_mint[:8],
            error=None,
            input_amount=token_amount,
            output_amount=token_amount * 0.01,  # Simulated
            price_impact=0.5
        )
    
    def calculate_position_size(self, whale_amount_usd: float) -> float:
        """Calculate position"""
        base = min(whale_amount_usd * 0.05, config.MAX_POSITION_SOL)
        return max(base, 0.1)
    
    async def validate_token(self, token_mint: str) -> Dict[str, Any]:
        """Validate token"""
        validation = {'valid': False, 'reason': '', 'liquidity': 0}
        
        if len(token_mint) != 44:
            validation['reason'] = 'Invalid address'
            return validation
        
        # Check Jupiter route
        quote = await self.get_quote(
            "So11111111111111111111111111111111111111112",
            token_mint,
            100_000_000
        )
        
        if quote and quote.get('routePlan'):
            validation['valid'] = True
            validation['liquidity'] = float(quote.get('inAmount', 0)) / 1e9
        else:
            validation['reason'] = 'No liquidity'
        
        return validation
    
    async def close(self):
        """Cleanup"""
        pass
