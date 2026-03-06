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
        self._local_trades = []
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("✅ Database connected")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
        else:
            logger.warning("⚠️ Database credentials not set - using local storage")
    
    def record_trade(self, trade):
        """Record new trade"""
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
        """Close trade"""
        if not self.client:
            return self._local_close_trade(token_address, profit)
        
        try:
            data = {
                'status': 'closed',
                'profit': profit,
                'close_time': datetime.now().isoformat()
            }
            result = self.client.table('trades').update(data).eq('token_address', token_address).eq('status', 'open').execute()
            logger.info(f"Trade closed: {token_address}")
            return result
        except Exception as e:
            logger.error(f"Failed to close trade: {e}")
            return self._local_close_trade(token_address, profit)
    
    def get_total_trades(self) -> int:
        """Get total trades"""
        if not self.client:
            return len(self._local_trades)
        try:
            result = self.client.table('trades').select('*', count='exact').execute()
            return result.count
        except:
            return 0
    
    def get_win_rate(self) -> float:
        """Calculate win rate"""
        if not self.client:
            return self._local_win_rate()
        try:
            result = self.client.table('trades').select('profit').eq('status', 'closed').execute()
            if not result.data:
                return 0.0
            wins = sum(1 for t in result.data if t.get('profit', 0) > 0)
            return (wins / len(result.data) * 100)
        except:
            return 0.0
    
    def get_performance_stats(self) -> Dict:
        """Get performance stats"""
        if not self.client:
            return self._local_stats()
        try:
            result = self.client.table('trades').select('*').execute()
            trades = result.data or []
            closed = [t for t in trades if t.get('status') == 'closed']
            wins = [t for t in closed if t.get('profit', 0) > 0]
            profits = [t.get('profit', 0) for t in closed]
            
            return {
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(closed) - len(wins),
                'win_rate': (len(wins) / len(closed) * 100) if closed else 0,
                'avg_profit': sum(profits) / len(profits) if profits else 0,
                'best_trade': max(profits) if profits else 0,
                'worst_trade': min(profits) if profits else 0,
            }
        except:
            return self._empty_stats()
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades"""
        if not self.client:
            return list(reversed(self._local_trades[-limit:]))
        try:
            result = self.client.table('trades').select('*').eq('status', 'closed').order('close_time', desc=True).limit(limit).execute()
            return result.data or []
        except:
            return []
    
    def get_top_trades(self, limit: int = 5) -> List[Dict]:
        """Get top trades"""
        if not self.client:
            sorted_trades = sorted(self._local_trades, key=lambda x: x.get('profit', 0), reverse=True)
            return sorted_trades[:limit]
        try:
            result = self.client.table('trades').select('*').eq('status', 'closed').order('profit', desc=True).limit(limit).execute()
            return result.data or []
        except:
            return []
    
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
        return len(wins) / len(closed) * 100 if closed else 0.0
    
    def _local_stats(self):
        return self._empty_stats()
    
    def _empty_stats(self):
        return {
            'total_trades': 0, 'wins': 0, 'losses': 0,
            'win_rate': 0, 'avg_profit': 0, 'best_trade': 0,
            'worst_trade': 0
        }
