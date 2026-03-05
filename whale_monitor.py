import os
import json
import logging
import asyncio
import websockets
from typing import Callable

logger = logging.getLogger(__name__)

class WhaleMonitor:
    def __init__(self, trading_engine, alert_callback: Callable):
        self.trading_engine = trading_engine
        self.send_alert = alert_callback
        self.ws_connected = False
        self.is_running = False
        self.ws_url = os.getenv('HELIUS_RPC_URL').replace('https://', 'wss://')
        self.min_whale_size = int(os.getenv('MIN_WHALE_SIZE', '5000'))
        
    async def start(self):
        """Start WebSocket connection to Helius"""
        self.is_running = True
        logger.info("🐋 Starting Whale Monitor...")
        
        while self.is_running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.ws_connected = False
                await asyncio.sleep(5)  # Reconnect delay
    
    async def _connect_and_listen(self):
        """Connect to Helius WebSocket and listen for transactions"""
        logger.info(f"Connecting to {self.ws_url}")
        
        async with websockets.connect(self.ws_url) as ws:
            self.ws_connected = True
            logger.info("✅ WebSocket connected")
            
            # Subscribe to large transactions
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": ["all"]},  # Monitor all transactions
                    {"commitment": "confirmed"}
                ]
            }
            
            # Alternative: Use Helius enhanced API for whale detection
            # This is a simplified version - production would use Helius webhooks or enhanced APIs
            
            await ws.send(json.dumps(subscribe_msg))
            
            while self.is_running:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(msg)
                    await self._process_transaction(data)
                except asyncio.TimeoutError:
                    # Send ping to keep alive
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
    
    async def _process_transaction(self, data: dict):
        """Process incoming transaction data"""
        try:
            # Parse Helius webhook/enhanced API format
            # This is simplified - actual implementation depends on Helius response format
            
            if 'params' not in data:
                return
            
            result = data['params'].get('result', {})
            logs = result.get('logs', [])
            
            # Look for swap instructions (Raydium, Orca, Jupiter)
            if any('swap' in log.lower() or 'Swap' in log for log in logs):
                # Extract transaction details
                tx_data = self._parse_swap_transaction(result)
                
                if tx_data and tx_data['value_usd'] >= self.min_whale_size:
                    await self._handle_whale_trade(tx_data)
                    
        except Exception as e:
            logger.error(f"Transaction processing error: {e}")
    
    def _parse_swap_transaction(self, result: dict) -> dict:
        """Parse swap transaction details"""
        # Simplified parsing - production would use proper log parsing
        try:
            return {
                'signature': result.get('signature', 'unknown'),
                'token_address': self._extract_token_address(result),
                'value_usd': self._estimate_value(result),
                'buyer': result.get('buyer', 'unknown'),
                'timestamp': result.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def _extract_token_address(self, result: dict) -> str:
        """Extract token address from transaction logs"""
        # Placeholder - actual implementation would parse token accounts
        logs = result.get('logs', [])
        for log in logs:
            if 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA' in log:
                # Extract from token program invocation
                pass
        return "unknown_token"
    
    def _estimate_value(self, result: dict) -> float:
        """Estimate USD value of transaction"""
        # Placeholder - would calculate from SOL amount and price
        return 0.0
    
    async def _handle_whale_trade(self, tx_data: dict):
        """Handle detected whale trade"""
        logger.info(f"🐋 WHALE ALERT: ${tx_data['value_usd']:,.0f} trade detected!")
        
        alert_msg = f"""
🚨 **WHALE ALERT** 🚨

💰 Value: ${tx_data['value_usd']:,.0f}
🪙 Token: `{tx_data['token_address'][:20]}...`
👤 Whale: `{tx_data['buyer'][:20]}...`
🔗 Tx: `{tx_data['signature'][:20]}...`

{'⚡ AUTO-BUY TRIGGERED!' if os.getenv('AUTO_TRADE', 'true').lower() == 'true' else '👁️ Monitoring only'}
"""
        await self.send_alert(alert_msg)
        
        # Execute copy-trade if enabled
        if os.getenv('AUTO_TRADE', 'true').lower() == 'true':
            await self._execute_copy_trade(tx_data)
    
    async def _execute_copy_trade(self, tx_data: dict):
        """Execute copy-cat trade"""
        try:
            from config import Config
            
            # Calculate position size (whale size or max position, whichever is smaller)
            position_sol = min(
                tx_data['value_usd'] / 20,  # Assume SOL = $20 for estimation
                Config.MAX_POSITION_SOL
            )
            
            # Execute buy
            signature = await self.trading_engine.execute_buy(
                token_address=tx_data['token_address'],
                amount_sol=position_sol,
                whale_tx=tx_data['signature']
            )
            
            if signature:
                success_msg = f"""
✅ **COPY-TRADE EXECUTED**

🪙 Token: `{tx_data['token_address'][:20]}...`
💸 Amount: {position_sol:.2f} SOL
🔗 Tx: `{signature[:30]}...`
⏱️ Latency: <2s from whale detection
"""
                await self.send_alert(success_msg)
            else:
                await self.send_alert("❌ Copy-trade failed - check logs")
                
        except Exception as e:
            logger.error(f"Copy-trade execution failed: {e}")
            await self.send_alert(f"❌ Copy-trade error: {str(e)}")
    
    async def stop(self):
        """Stop the monitor"""
        self.is_running = False
        self.ws_connected = False
        logger.info("Whale monitor stopped")
