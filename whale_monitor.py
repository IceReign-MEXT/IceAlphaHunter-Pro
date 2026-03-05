"""Helius WebSocket Whale Transaction Monitor"""
import asyncio
import aiohttp
import json
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from config import config

@dataclass
class WhaleTrade:
    signature: str
    trader_address: str
    token_mint: str
    token_symbol: str
    amount_usd: float
    amount_tokens: float
    transaction_type: str  # 'buy' or 'sell'
    timestamp: datetime
    raw_data: Dict

class WhaleMonitor:
    def __init__(self):
        self.helius_ws_url = f"wss://mainnet.helius-rpc.com/?api-key={config.HELIUS_API_KEY}"
        self.http_url = f"https://mainnet.helius-rpc.com/?api-key={config.HELIUS_API_KEY}"
        self.callbacks: List[Callable[[WhaleTrade], None]] = []
        self.min_amount_usd = config.MIN_WHALE_AMOUNT_USD
        self.running = False
        self.known_tokens: Dict[str, str] = {}  # mint -> symbol cache
        
    def on_whale_detected(self, callback: Callable[[WhaleTrade], None]):
        """Register callback for whale detection"""
        self.callbacks.append(callback)
    
    async def _fetch_token_symbol(self, mint: str) -> str:
        """Fetch token metadata from Helius"""
        if mint in self.known_tokens:
            return self.known_tokens[mint]
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAsset",
                    "params": {"id": mint}
                }
                async with session.post(self.http_url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get('result', {})
                        symbol = result.get('symbol', result.get('name', 'UNKNOWN'))
                        self.known_tokens[mint] = symbol
                        return symbol
        except Exception:
            pass
        
        return "UNKNOWN"
    
    async def _parse_transaction(self, tx_data: Dict) -> Optional[WhaleTrade]:
        """Parse Helius transaction for whale activity"""
        try:
            signature = tx_data.get('signature', '')
            account_data = tx_data.get('accountData', [])
            token_changes = []
            
            # Look for token balance changes
            for account in account_data:
                if account.get('tokenBalanceChanges'):
                    for change in account['tokenBalanceChanges']:
                        mint = change.get('mint', '')
                        raw_amount = abs(float(change.get('rawTokenAmount', {}).get('tokenAmount', 0)))
                        decimals = int(change.get('rawTokenAmount', {}).get('decimals', 9))
                        
                        # Skip SOL (wrapped SOL handled separately)
                        if mint == 'So11111111111111111111111111111111111111112':
                            continue
                        
                        amount_tokens = raw_amount / (10 ** decimals)
                        
                        # Calculate USD value (approximate using SOL price if needed)
                        # For now, use raw amount as proxy
                        # In production, fetch real price from Jupiter or Birdeye
                        
                        token_changes.append({
                            'mint': mint,
                            'amount': amount_tokens,
                            'owner': change.get('account', '')
                        })
            
            if not token_changes:
                return None
            
            # Find largest token change (the main trade)
            main_change = max(token_changes, key=lambda x: x['amount'])
            
            # Estimate USD value (placeholder - integrate price oracle)
            # In production: fetch real-time price from Jupiter/Birdeye
            estimated_usd = main_change['amount'] * 0.01  # Placeholder price
            
            if estimated_usd < self.min_amount_usd:
                return None
            
            # Determine buy/sell by checking native balance change
            native_changes = tx_data.get('nativeBalanceChanges', [])
            is_buy = False
            
            for change in native_changes:
                if change.get('account') == main_change['owner']:
                    # If SOL decreased significantly, likely a buy
                    if float(change.get('amount', 0)) < -0.05:  # 0.05 SOL threshold
                        is_buy = True
                        break
            
            token_symbol = await self._fetch_token_symbol(main_change['mint'])
            
            return WhaleTrade(
                signature=signature,
                trader_address=main_change['owner'],
                token_mint=main_change['mint'],
                token_symbol=token_symbol,
                amount_usd=estimated_usd,
                amount_tokens=main_change['amount'],
                transaction_type='buy' if is_buy else 'sell',
                timestamp=datetime.now(),
                raw_data=tx_data
            )
            
        except Exception as e:
            print(f"Parse error: {e}")
            return None
    
    async def start_monitoring(self):
        """Start WebSocket connection to Helius"""
        self.running = True
        
        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(self.helius_ws_url) as ws:
                        print("🔗 Connected to Helius WebSocket")
                        
                        # Subscribe to transactions
                        subscribe_msg = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "transactionSubscribe",
                            "params": [
                                {"mentionsAccountOrProgram": "*"},  # All transactions
                                {
                                    "commitment": "confirmed",
                                    "encoding": "jsonParsed",
                                    "transactionDetails": "full",
                                    "showRewards": False,
                                    "maxSupportedTransactionVersion": 0
                                }
                            ]
                        }
                        
                        await ws.send_str(json.dumps(subscribe_msg))
                        
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                
                                # Handle subscription confirmation
                                if 'result' in data:
                                    print(f"✅ Subscription confirmed: {data['result']}")
                                    continue
                                
                                # Handle transaction
                                if 'params' in data and 'result' in data['params']:
                                    tx_data = data['params']['result']
                                    whale_trade = await self._parse_transaction(tx_data)
                                    
                                    if whale_trade:
                                        print(f"🐋 WHALE DETECTED: {whale_trade.token_symbol} "
                                              f"${whale_trade.amount_usd:,.2f} "
                                              f"({whale_trade.transaction_type.upper()})")
                                        
                                        # Notify all callbacks
                                        for callback in self.callbacks:
                                            try:
                                                await callback(whale_trade)
                                            except Exception as e:
                                                print(f"Callback error: {e}")
                            
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                print(f"WebSocket error: {ws.exception()}")
                                break
                            
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                print("WebSocket closed")
                                break
                                
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(5)  # Reconnect delay
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
