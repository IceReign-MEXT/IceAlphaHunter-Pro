import os
import json
import asyncio
import aiohttp
from typing import Dict, Optional
from solathon import Client, Keypair, Transaction
from solathon.core.instructions import transfer
from dotenv import load_dotenv

load_dotenv()

class AutoTrader:
    def __init__(self):
        self.client = Client(os.getenv("RPC_URL"))
        self.wallet = Keypair.from_private_key(os.getenv("BOT_PRIVATE_KEY"))
        self.jupiter_api = "https://quote-api.jup.ag/v6"
        
        # Trading config
        self.max_slippage = 50  # 0.5%
        self.min_profit = 1.1   # 10% profit target
        self.stop_loss = 0.85   # 15% stop loss
        
    async def execute_buy(self, token_address: str, sol_amount: float):
        """Buy token via Jupiter"""
        try:
            print(f"🛒 Buying {token_address} with {sol_amount} SOL")
            
            # Get quote from Jupiter
            quote_url = f"{self.jupiter_api}/quote"
            params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                "outputMint": token_address,
                "amount": int(sol_amount * 1e9),  # Convert to lamports
                "slippageBps": self.max_slippage
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_url, params=params) as resp:
                    if resp.status != 200:
                        print(f"❌ Quote failed: {await resp.text()}")
                        return None
                    
                    quote_data = await resp.json()
                    
                # Get swap transaction
                swap_url = f"{self.jupiter_api}/swap"
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(self.wallet.public_key),
                    "wrapAndUnwrapSol": True
                }
                
                async with session.post(swap_url, json=swap_payload) as resp:
                    swap_data = await resp.json()
                    
                    if 'swapTransaction' not in swap_data:
                        print(f"❌ No swap transaction returned")
                        return None
                    
                    # Deserialize and sign transaction
                    # Note: This is simplified - real implementation needs proper serialization
                    print(f"✅ Swap transaction ready")
                    return swap_data
                    
        except Exception as e:
            print(f"❌ Buy failed: {e}")
            return None
    
    async def execute_sell(self, token_address: str, percentage: int = 100):
        """Sell token via Jupiter"""
        try:
            print(f"💰 Selling {percentage}% of {token_address}")
            
            # Get token balance
            balance = await self.get_token_balance(token_address)
            sell_amount = int(balance * (percentage / 100))
            
            if sell_amount == 0:
                print("❌ No balance to sell")
                return None
            
            # Get quote (reverse of buy)
            quote_url = f"{self.jupiter_api}/quote"
            params = {
                "inputMint": token_address,
                "outputMint": "So11111111111111111111111111111111111111112",  # SOL
                "amount": sell_amount,
                "slippageBps": self.max_slippage
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_url, params=params) as resp:
                    quote_data = await resp.json()
                    
                # Execute swap
                swap_url = f"{self.jupiter_api}/swap"
                swap_payload = {
                    "quoteResponse": quote_data,
                    "userPublicKey": str(self.wallet.public_key),
                    "wrapAndUnwrapSol": True
                }
                
                async with session.post(swap_url, json=swap_payload) as resp:
                    swap_data = await resp.json()
                    print(f"✅ Sell transaction ready")
                    return swap_data
                    
        except Exception as e:
            print(f"❌ Sell failed: {e}")
            return None
    
    async def get_token_balance(self, token_address: str) -> int:
        """Get SPL token balance"""
        try:
            # This is simplified - real implementation needs token account lookup
            return 0
        except:
            return 0
    
    async def monitor_and_sell(self, token_address: str, buy_price: float):
        """Monitor position and take profit/stop loss"""
        while True:
            try:
                # Get current price (from Jupiter or Birdeye)
                current_price = await self.get_token_price(token_address)
                
                pnl_ratio = current_price / buy_price
                
                if pnl_ratio >= self.min_profit:
                    print(f"🎯 Profit target reached: {pnl_ratio:.2f}x")
                    await self.execute_sell(token_address, 100)
                    break
                    
                elif pnl_ratio <= self.stop_loss:
                    print(f"🛑 Stop loss hit: {pnl_ratio:.2f}x")
                    await self.execute_sell(token_address, 100)
                    break
                    
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Error monitoring: {e}")
                await asyncio.sleep(5)
    
    async def get_token_price(self, token_address: str) -> float:
        """Get token price in SOL"""
        try:
            # Use Jupiter price API
            url = f"https://price.jup.ag/v4/price?ids={token_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    return data.get('data', {}).get(token_address, {}).get('price', 0)
        except:
            return 0

# Run standalone test
if __name__ == "__main__":
    trader = AutoTrader()
    # Test with dummy data
    asyncio.run(trader.execute_buy("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 0.1))

