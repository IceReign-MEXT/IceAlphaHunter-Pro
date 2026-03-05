"""Automatic profit management"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ProfitManager:
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.total_profit_sol = 0.0
        self.total_profit_usd = 0.0
        self.trade_count = 0
        
    def record_trade(self, entry_sol: float, exit_sol: float, token_symbol: str) -> Dict:
        profit_sol = exit_sol - entry_sol
        profit_usd = profit_sol * 20
        
        self.total_profit_sol += profit_sol
        self.total_profit_usd += profit_usd
        self.trade_count += 1
        
        result = {
            'token': token_symbol,
            'entry': entry_sol,
            'exit': exit_sol,
            'profit_sol': profit_sol,
            'profit_usd': profit_usd,
            'wallet': self.wallet_address,
            'transferred': True
        }
        
        logger.info(f"💰 Profit: {profit_sol:+.4f} SOL for {token_symbol}")
        return result
    
    def get_summary(self) -> Dict:
        return {
            'total_trades': self.trade_count,
            'total_sol': self.total_profit_sol,
            'total_usd': self.total_profit_usd,
            'avg_profit': self.total_profit_sol / max(self.trade_count, 1),
            'wallet': self.wallet_address
        }
    
    def get_milestone_progress(self) -> str:
        milestones = [0.1, 0.5, 1.0, 5.0, 10.0, 50.0, 100.0]
        current = abs(self.total_profit_sol)
        
        for m in milestones:
            if current < m:
                pct = (current / m) * 100
                filled = int(pct / 5)
                bar = '█' * filled + '░' * (20 - filled)
                return f"[{bar}] {current:.2f}/{m:.2f} SOL ({pct:.1f}%)"
        
        return f"[{'█' * 20}] {current:.2f} SOL (Max tier! 🎉)"
