import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ProfitManager:
    def __init__(self, database):
        self.db = database
        self.wallet_address = os.getenv('WALLET_ADDRESS', 'Not configured')
        self.sol_price = 20.0
    
    def get_total_profit(self) -> float:
        """Get total profit in SOL"""
        try:
            return sum(t.get('profit', 0) for t in self.db.get_recent_trades(limit=1000))
        except Exception as e:
            logger.error(f"Failed to get profit: {e}")
            return 0.0
    
    def get_total_profit_usd(self) -> float:
        """Get total profit in USD"""
        return self.get_total_profit() * self.sol_price
    
    def get_profit_summary(self) -> Dict:
        """Get profit summary"""
        total_sol = self.get_total_profit()
        target = 0.1
        progress = (total_sol / target * 100) if target > 0 else 0
        
        return {
            'available_sol': total_sol,
            'available_usd': total_sol * self.sol_price,
            'unrealized_sol': 0.0,
            'total_sol': total_sol,
            'current': total_sol,
            'target': target,
            'progress': min(progress, 100)
        }
