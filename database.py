"""Supabase PostgreSQL Database Manager"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from config import config

class Database:
    def __init__(self):
        self.connection_string = config.DATABASE_URL
        # Verify connection on init
        self._test_connection()
        self._init_tables()
    
    def _test_connection(self):
        """Test database connection"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"✅ Database connected: {version[0][:50]}...")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _init_tables(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    signature VARCHAR(100) UNIQUE,
                    token_mint VARCHAR(50),
                    token_symbol VARCHAR(20),
                    entry_price DECIMAL(20, 10),
                    exit_price DECIMAL(20, 10),
                    amount DECIMAL(20, 10),
                    profit_sol DECIMAL(20, 10) DEFAULT 0,
                    profit_usd DECIMAL(20, 10) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'open',
                    whale_signature VARCHAR(100),
                    whale_amount_usd DECIMAL(20, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    metadata JSONB
                )
            """)
            
            # Whale alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_alerts (
                    id SERIAL PRIMARY KEY,
                    signature VARCHAR(100) UNIQUE,
                    trader_address VARCHAR(50),
                    token_mint VARCHAR(50),
                    token_symbol VARCHAR(20),
                    amount_usd DECIMAL(20, 2),
                    amount_tokens DECIMAL(20, 10),
                    transaction_type VARCHAR(10),
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    followed BOOLEAN DEFAULT FALSE,
                    our_trade_id INTEGER REFERENCES trades(id)
                )
            """)
            
            # Bot stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id SERIAL PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    profitable_trades INTEGER DEFAULT 0,
                    total_profit_sol DECIMAL(20, 10) DEFAULT 0,
                    total_profit_usd DECIMAL(20, 10) DEFAULT 0,
                    whales_detected INTEGER DEFAULT 0,
                    whales_followed INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert initial stats row if empty
            cursor.execute("SELECT COUNT(*) FROM bot_stats")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO bot_stats DEFAULT VALUES")
            
            conn.commit()
            print("✅ Database tables initialized")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        """Log new trade to database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    signature, token_mint, token_symbol, entry_price, 
                    amount, whale_signature, whale_amount_usd, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signature) DO NOTHING
                RETURNING id
            """, (
                trade_data.get('signature'),
                trade_data.get('token_mint'),
                trade_data.get('token_symbol'),
                trade_data.get('entry_price', 0),
                trade_data.get('amount', 0),
                trade_data.get('whale_signature'),
                trade_data.get('whale_amount_usd', 0),
                json.dumps(trade_data.get('metadata', {}))
            ))
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
    
    def close_trade(self, trade_id: int, exit_price: float, 
                   profit_sol: float, profit_usd: float, 
                   exit_signature: str) -> bool:
        """Close trade with profit/loss data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades 
                SET status = 'closed', 
                    exit_price = %s, 
                    profit_sol = %s, 
                    profit_usd = %s,
                    closed_at = CURRENT_TIMESTAMP,
                    metadata = jsonb_set(metadata, '{exit_signature}', %s)
                WHERE id = %s
                RETURNING id
            """, (exit_price, profit_sol, profit_usd, 
                  json.dumps(exit_signature), trade_id))
            result = cursor.fetchone()
            conn.commit()
            return result is not None
    
    def log_whale_alert(self, alert_data: Dict[str, Any]) -> int:
        """Log whale detection"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO whale_alerts (
                    signature, trader_address, token_mint, token_symbol,
                    amount_usd, amount_tokens, transaction_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signature) DO NOTHING
                RETURNING id
            """, (
                alert_data.get('signature'),
                alert_data.get('trader_address'),
                alert_data.get('token_mint'),
                alert_data.get('token_symbol'),
                alert_data.get('amount_usd', 0),
                alert_data.get('amount_tokens', 0),
                alert_data.get('type', 'buy')
            ))
            result = cursor.fetchone()
            
            # Update stats
            cursor.execute("""
                UPDATE bot_stats 
                SET whales_detected = whales_detected + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
            
            conn.commit()
            return result[0] if result else None
    
    def mark_whale_followed(self, alert_id: int, trade_id: int):
        """Mark whale alert as followed with our trade"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE whale_alerts 
                SET followed = TRUE, our_trade_id = %s
                WHERE id = %s
            """, (trade_id, alert_id))
            
            cursor.execute("""
                UPDATE bot_stats 
                SET whales_followed = whales_followed + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """)
            conn.commit()
    
    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status = 'open' 
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get comprehensive bot statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Trade stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable_trades,
                    SUM(profit_sol) as total_profit_sol,
                    SUM(profit_usd) as total_profit_usd,
                    AVG(profit_sol) as avg_profit_sol
                FROM trades 
                WHERE status = 'closed'
            """)
            trade_stats = dict(cursor.fetchone())
            
            # Bot stats
            cursor.execute("SELECT * FROM bot_stats WHERE id = 1")
            bot_stats = dict(cursor.fetchone() or {})
            
            # Recent whales
            cursor.execute("""
                SELECT COUNT(*) as whales_24h 
                FROM whale_alerts 
                WHERE detected_at > NOW() - INTERVAL '24 hours'
            """)
            whales_24h = cursor.fetchone()[0]
            
            return {
                **trade_stats,
                **bot_stats,
                'whales_24h': whales_24h,
                'win_rate': (trade_stats['profitable_trades'] / trade_stats['total_trades'] * 100) 
                           if trade_stats['total_trades'] else 0
            }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades for display"""
        with self._get_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM trades 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Global instance
db = Database()
