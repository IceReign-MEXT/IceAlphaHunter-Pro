"""Wallet Management"""
import os
import base58
from nacl.signing import SigningKey
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Wallet:
    """Solana Wallet Handler"""
    
    def __init__(self):
        self.private_key_str = os.getenv("WALLET_PRIVATE_KEY", "")
        self.public_key_str = os.getenv("WALLET_PUBLIC_KEY", "")
        self._load_keypair()
    
    def _load_keypair(self):
        """Load keypair from private key"""
        if not self.private_key_str:
            logger.warning("No private key configured")
            return
        
        try:
            if ',' in self.private_key_str:
                key_bytes = bytes([int(x) for x in self.private_key_str.strip('[]').split(',')])
            else:
                key_bytes = base58.b58decode(self.private_key_str)
            
            if len(key_bytes) == 64:
                private_bytes = key_bytes[:32]
                public_bytes = key_bytes[32:]
            elif len(key_bytes) == 32:
                private_bytes = key_bytes
                signing_key = SigningKey(private_bytes)
                public_bytes = bytes(signing_key.verify_key)
            else:
                raise ValueError(f"Invalid key length: {len(key_bytes)}")
            
            self._signing_key = SigningKey(private_bytes)
            self._public_key = public_bytes
            logger.info(f"✅ Wallet loaded: {self.address[:8]}...")
            
        except Exception as e:
            logger.error(f"❌ Failed to load wallet: {e}")
            raise
    
    @property
    def address(self) -> str:
        """Get wallet address"""
        if hasattr(self, '_public_key'):
            return base58.b58encode(self._public_key).decode('ascii')
        return self.public_key_str
    
    def sign_message(self, message: bytes) -> bytes:
        """Sign a message"""
        if not hasattr(self, '_signing_key'):
            raise ValueError("Wallet not initialized")
        return self._signing_key.sign(message).signature

wallet = Wallet()
