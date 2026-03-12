"""Whale Monitor - Synchronous Version"""
import requests
import time
import threading
from typing import Dict, List, Callable
import logging
from config import config
from database import db

logger = logging.getLogger(__name__)

class WhaleMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.callbacks: List[Callable] = []
        self.is_running = False
        self.known_whales = []
        self.monitor_thread = None
    
    def start(self):
        self.is_running = True
        wallets = db.get_monitored_wallets()
        for w in wallets:
            self.known_whales.append(w["address"])
        logger.info(f"✅ Whale monitor started ({len(self.known_whales)} wallets)")
        
        # Start monitoring in background thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        self.is_running = False
        self.session.close()
    
    def on_whale_movement(self, callback: Callable):
        self.callbacks.append(callback)
    
    def _monitor_loop(self):
        while self.is_running:
            try:
                for whale in self.known_whales:
                    self._check_transactions(whale)
                    time.sleep(1)
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)
    
    def _check_transactions(self, address: str):
        try:
            url = config.HELIUS_RPC_URL
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": 3}]
            }
            resp = self.session.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                sigs = data.get("result", [])
                for sig in sigs:
                    self._process_signature(sig["signature"], address)
        except Exception as e:
            logger.error(f"Check error: {e}")
    
    def _process_signature(self, signature: str, whale: str):
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
            callback(alert)
    
    def add_whale(self, address: str, label: str = ""):
        if address not in self.known_whales:
            self.known_whales.append(address)
            db.add_monitored_wallet(address, label, True)

whale_monitor = WhaleMonitor()
