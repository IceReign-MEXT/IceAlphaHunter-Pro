import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client: Optional[Client] = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("✅ Database connected")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
        else:
            logger.warning("⚠️ Database credentials not set - using local storage")
    
    def record_trade(self, trade):
        """Record new trade in database"""
        if not self.client:
            return self._local_record_trade(trade)
        
        try:
            data = {
                'token_address': trade.token_address,
                'entry_price': trade.entry_price,
                'amount_sol': trade.amount_sol,
                'timestamp': trade.timestamp,
                'tx_signature': trade.tx_signature,
                'status': 'open',
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('trades').insert(data).execute()
            logger.info(f"Trade recorded: {trade.token_address}")
            return result
        except Exception as e:
            logger.error(f"Failed to record trade: {e}")
            return self._local_record_trade(trade)
    
    def close_trade(self, token_address: str, profit: float):
        """Close trade and record PnL"""
        if not self.client:
            return self._local_close_trade(token_address, profit)
        
        try:
            data = {
                'status': 'closed',
                'profit': profit,
                'close_time': datetime.now().isoformat()
            }
            
            result = self.client.table('trades').update(data).eq('token_address', token_address).eq('status', 'open').execute()
            logger.info(f"Trade closed: {token_address}, PnL: {profit}")
            return result
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            return self._local_close_trade(token_address, profit)
    
    def get_total_trades(self) -> int:
        """Get total number of trades"""
        if not self.client:
            return len(self._local_trades)
        
        try:
            result = self.client.table('trades').select('*', count='exact').execute()
            return result.count
        except Exception as e:
            logger.error(f"Failed to get trade count: {e}")
            return 0
    
    def get_win_rate(self) -> float:
        """Calculate win rate percentage"""
        if not self.client:
            return self._local_win_rate()
        
        try:
            result = self.client.table('trades').select('profit').eq('status', 'closed').execute()
            if not result.data:
                return 0.0
            
            wins = sum(1 for t in result.data if t.get('profit', 0) > 0)
            total = len(result.data)
            return (wins / total * 100) if total > 0 else 0.0
        except Exception as e:
            logger.error(f"Failed to calculate win rate: {e}")
            return 0.0
    
    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics"""
        if not self.client:
            return self._local_stats()
        
        try:
            result = self.client.table('trades').select('*').execute()
            trades = result.data or []
            
            if not trades:
                return self._empty_stats()
            
            closed_trades = [t for t in trades if t.get('status') == 'closed']
            wins = [t for t in closed_trades if t.get('profit', 0) > 0]
            losses = [t for t in closed_trades if t.get('profit', 0) <= 0]
            
            profits = [t.get('profit', 0) for t in closed_trades]
            
            return {
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': (len(wins) / len(closed_trades) * 100) if closed_trades else 0,
                'avg_profit': sum(profits) / len(profits) if profits else 0,
                'best_trade': max(profits) if profits else 0,
                'worst_trade': min(profits) if profits else 0,
                'whales_detected': len(trades),  # Simplified
                'whales_followed': len(trades),
                'conversion_rate': 100.0 if trades else 0
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return self._empty_stats()
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent closed trades"""
        if not self.client:
            return list(reversed(self._local_trades[-limit:]))
        
        try:
            result = self.client.table('trades').select('*').eq('status', 'closed').order('close_time', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get recent trades: {e}")
            return []
    
    def get_top_trades(self, limit: int = 5) -> List[Dict]:
        """Get top performing trades"""
        if not self.client:
            sorted_trades = sorted(self._local_trades, key=lambda x: x.get('profit', 0), reverse=True)
            return sorted_trades[:limit]
        
        try:
            result = self.client.table('trades').select('*').eq('status', 'closed').order('profit', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get top trades: {e}")
            return []
    
    # Local storage fallback methods
    def __init_local_storage(self):
        self._local_trades = []
        self._local_stats_cache = {}
    
    def _local_record_trade(self, trade):
        self._local_trades.append({
            'token_address': trade.token_address,
            'entry_price': trade.entry_price,
            'amount_sol': trade.amount_sol,
            'timestamp': trade.timestamp,
            'tx_signature': trade.tx_signature,
            'status': 'open',
            'profit': 0
        })
        return True
    
    def _local_close_trade(self, token_address: str, profit: float):
        for trade in self._local_trades:
            if trade['token_address'] == token_address and trade['status'] == 'open':
                trade['status'] = 'closed'
                trade['profit'] = profit
                trade['close_time'] = datetime.now().isoformat()
                return True
        return False
    
    def _local_win_rate(self):
        closed = [t for t in self._local_trades if t['status'] == 'closed']
        if not closed:
            return 0.0
        wins = [t for t in closed if t.get('profit', 0) > 0]
        return len(wins) / len(closed) * 100
    
    def _local_stats(self):
        return self._empty_stats()  # Simplified for brevity
    
    def _empty_stats(self):
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0,
            'win_rate': 0, 'avg_profit': 0, 'best_trade': 0,
            'worst_trade': 0, 'whales_detected': 0,
            'whales_followed': 0, 'conversion_rate': 0
        }

# Initialize local storage
Database._local_trades = []
Database.__init_local_storage = lambda self: None
