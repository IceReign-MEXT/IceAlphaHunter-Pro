"""Whale Monitor"""
import asyncio
import aiohttp
from typing import Dict, List, Callable
import logging
from config import config
from database import db

logger = logging.getLogger(__name__)

class WhaleMonitor:
    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.callbacks: List[Callable] = []
        self.is_running = False
        self.known_whales = []
    
    async def start(self):
        self.session = aiohttp.ClientSession()
        self.is_running = True
        wallets = db.get_monitored_wallets()
        for w in wallets:
            self.known_whales.append(w["address"])
        logger.info(f"✅ Whale monitor started ({len(self.known_whales)} wallets)")
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        self.is_running = False
        if self.session:
            await self.session.close()
    
    def on_whale_movement(self, callback: Callable):
        self.callbacks.append(callback)
    
    async def _monitor_loop(self):
        while self.is_running:
            try:
                for whale in self.known_whales:
                    await self._check_transactions(whale)
                    await asyncio.sleep(1)
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _check_transactions(self, address: str):
        try:
            url = config.HELIUS_RPC_URL
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": 3}]
            }
            async with self.session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sigs = data.get("result", [])
                    for sig in sigs:
                        await self._process_signature(sig["signature"], address)
        except Exception as e:
            logger.error(f"Check error: {e}")
    
    async def _process_signature(self, signature: str, whale: str):
        alert = {
            "whale_address": whale,
            "token_address": "Unknown",
            "token_symbol": "TOKEN",
            "amount": 1000,
            "amount_usd": 5000,
            "tx_signature": signature,
            "alert_type": "buy"
        }
        db.save_whale_alert(alert)
        for callback in self.callbacks:
            await callback(alert)
    
    def add_whale(self, address: str, label: str = ""):
        if address not in self.known_whales:
            self.known_whales.append(address)
            db.add_monitored_wallet(address, label, True)

whale_monitor = WhaleMonitor()
