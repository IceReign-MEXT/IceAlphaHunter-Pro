"""Professional Jupiter v6 Trading Engine"""
import aiohttp
import asyncio
import base58
import base64
from decimal import Decimal
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from config import config

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts

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
        self.wallet = self._load_wallet()
        self.rpc_client = AsyncClient(config.HELIUS_RPC_URL)
        self.jupiter_quote_url = config.JUPITER_QUOTE_API
        self.jupiter_swap_url = config.JUPITER_SWAP_API
        self.slippage_bps = config.SLIPPAGE_BPS
        self.max_retries = 3
        
    def _load_wallet(self) -> Keypair:
        """Load wallet from private key"""
        try:
            secret_key = base58.b58decode(config.WALLET_PRIVATE_KEY)
            return Keypair.from_bytes(secret_key)
        except Exception as e:
            raise ValueError(f"Invalid wallet private key: {e}")
    
    async def get_quote(self, input_mint: str, output_mint: str, 
                       amount_lamports: int) -> Optional[Dict]:
        """Get swap quote from Jupiter v6"""
        url = f"{self.jupiter_quote_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_lamports),
            "slippageBps": self.slippage_bps,
            "onlyDirectRoutes": "false",
            "asLegacyTransaction": "false"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"Quote error: {resp.status} - {error_text}")
                    return None
    
    async def execute_swap(self, quote: Dict, 
                          priority_fee: int = 10000) -> SwapResult:
        """Execute swap with transaction signing"""
        try:
            swap_payload = {
                "quoteResponse": quote,
                "userPublicKey": str(self.wallet.pubkey()),
                "wrapAndUnwrapSol": True,
                "prioritizationFeeLamports": priority_fee
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.jupiter_swap_url, 
                    json=swap_payload,
                    timeout=30
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        return SwapResult(False, None, f"Swap API error: {error}", 0, 0, 0)
                    
                    swap_data = await resp.json()
            
            tx_base64 = swap_data.get('swapTransaction')
            if not tx_base64:
                return SwapResult(False, None, "No transaction in response", 0, 0, 0)
            
            raw_tx = base64.b64decode(tx_base64)
            transaction = VersionedTransaction.from_bytes(raw_tx)
            
            signed_tx = VersionedTransaction(transaction.message, [self.wallet])
            
            opts = TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            result = await self.rpc_client.send_transaction(signed_tx, opts=opts)
            
            signature = result.value
            
            confirmed = await self._confirm_transaction(signature)
            
            if confirmed:
                out_amount = float(quote.get('outAmount', 0)) / (10 ** quote.get('outputDecimals', 9))
                in_amount = float(quote.get('inAmount', 0)) / (10 ** quote.get('inputDecimals', 9))
                price_impact = float(quote.get('priceImpactPct', 0)) * 100
                
                return SwapResult(True, str(signature), None, in_amount, out_amount, price_impact)
            else:
                return SwapResult(False, str(signature), "Transaction not confirmed", 0, 0, 0)
                
        except Exception as e:
            return SwapResult(False, None, f"Swap execution error: {str(e)}", 0, 0, 0)
    
    async def _confirm_transaction(self, signature: str, 
                                    max_timeout: int = 60) -> bool:
        """Wait for transaction confirmation"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < max_timeout:
            try:
                response = await self.rpc_client.get_signature_statuses([signature])
                if response.value[0] is not None:
                    status = response.value[0]
                    if status.confirmation_status in ["confirmed", "finalized"]:
                        return True
                    if status.err:
                        return False
            except Exception:
                pass
            await asyncio.sleep(2)
        
        return False
    
    async def buy_token(self, token_mint: str, sol_amount: float) -> SwapResult:
        """Buy token with SOL"""
        lamports = int(sol_amount * 1_000_000_000)
        
        quote = await self.get_quote(
            "So11111111111111111111111111111111111111112",
            token_mint,
            lamports
        )
        
        if not quote:
            return SwapResult(False, None, "Failed to get quote", 0, 0, 0)
        
        return await self.execute_swap(quote)
    
    async def sell_token(self, token_mint: str, token_amount: float,
                         decimals: int = 9) -> SwapResult:
        """Sell token for SOL"""
        raw_amount = int(token_amount * (10 ** decimals))
        
        quote = await self.get_quote(
            token_mint,
            "So11111111111111111111111111111111111111112",
            raw_amount
        )
        
        if not quote:
            return SwapResult(False, None, "Failed to get quote", 0, 0, 0)
        
        return await self.execute_swap(quote)
    
    def calculate_position_size(self, whale_amount_usd: float) -> float:
        """Calculate safe position size"""
        base_position = min(whale_amount_usd * 0.05, config.MAX_POSITION_SOL)
        return max(base_position, 0.1)
    
    async def validate_token(self, token_mint: str) -> Dict[str, Any]:
        """Token validation"""
        validation = {
            'valid': False,
            'reason': '',
            'liquidity': 0
        }
        
        if len(token_mint) != 44:
            validation['reason'] = 'Invalid address format'
            return validation
        
        try:
            quote = await self.get_quote(
                "So11111111111111111111111111111111111111112",
                token_mint,
                100_000_000
            )
            
            if quote and quote.get('routePlan'):
                validation['valid'] = True
                validation['liquidity'] = float(quote.get('inAmount', 0)) / 1_000_000_000
            else:
                validation['reason'] = 'No liquidity routes found'
                
        except Exception as e:
            validation['reason'] = f'Validation error: {str(e)}'
        
        return validation

    async def close(self):
        """Cleanup"""
        await self.rpc_client.close()
