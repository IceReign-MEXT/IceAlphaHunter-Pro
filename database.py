"""
Simple JSON-based trade tracking
Upgrade to PostgreSQL for production
"""

import json
import os
from datetime import datetime
from typing import List, Dict

DB_FILE = "trades.json"

class Database:
    def __init__(self):
        self.db_file = DB_FILE
        
    def log_trade(self, trade: Dict):
        """Log trade to database"""
        trade['logged_at'] = datetime.now().isoformat()
        
        trades = self.get_all_trades()
        trades.append(trade)
        
        with open(self.db_file, 'w') as f:
            json.dump(trades, f, indent=2)
    
    def get_all_trades(self) -> List[Dict]:
        """Get all trades"""
        if not os.path.exists(self.db_file):
            return []
        
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        trades = self.get_all_trades()
        
        if not trades:
            return {"total": 0, "profit": 0, "win_rate": 0}
        
        profitable = sum(1 for t in trades if t.get('profit', 0) > 0)
        total_profit = sum(t.get('profit', 0) for t in trades)
        
        return {
            "total": len(trades),
            "profitable": profitable,
            "win_rate": (profitable / len(trades)) * 100,
            "total_profit": total_profit,
            "avg_profit": total_profit / len(trades)
        }

if __name__ == "__main__":
    db = Database()
    print("Database loaded")
