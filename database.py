"""Supabase PostgreSQL Database Manager"""
import os
import sys

# Load .env BEFORE anything else
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', '')

class Database:
    def __init__(self):
        self.connection_string = DATABASE_URL
        if not self.connection_string:
            print("⚠️  WARNING: DATABASE_URL not set, using SQLite fallback")
            self._init_sqlite()
        else:
            self._init_postgres()
    
    def _init_sqlite(self):
        """Fallback to SQLite for testing"""
        import sqlite3
        self.sqlite_db = 'trades.db'
        conn = sqlite3.connect(self.sqlite_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signature TEXT UNIQUE,
                token_mint TEXT,
                token_symbol TEXT,
                entry_price REAL,
                exit_price REAL,
                amount REAL,
                profit_sol REAL DEFAULT 0,
                profit_usd REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                whale_signature TEXT,
                whale_amount_usd REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS whale_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signature TEXT UNIQUE,
                trader_address TEXT,
                token_mint TEXT,
                token_symbol TEXT,
                amount_usd REAL,
                amount_tokens REAL,
                transaction_type TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                followed INTEGER DEFAULT 0,
                our_trade_id INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_stats (
                id INTEGER PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                profitable_trades INTEGER DEFAULT 0,
                total_profit_sol REAL DEFAULT 0,
                total_profit_usd REAL DEFAULT 0,
                whales_detected INTEGER DEFAULT 0,
                whales_followed INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM bot_stats")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO bot_stats DEFAULT VALUES")
        
        conn.commit()
        conn.close()
        print("✅ SQLite database initialized")
    
    def _init_postgres(self):
        """Initialize PostgreSQL"""
        try:
            self._test_connection()
            self._init_tables()
        except Exception as e:
            print(f"❌ PostgreSQL failed: {e}")
            print("🔄 Falling back to SQLite...")
            self._init_sqlite()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        if not DATABASE_URL:
            import sqlite3
            conn = sqlite3.connect(self.sqlite_db)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
            return
            
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
    
    def _test_connection(self):
        """Test database connection"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL connected: {version[0][:50]}...")
    
    def _init_tables(self):
        """Initialize PostgreSQL tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
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
            
            cursor.execute("SELECT COUNT(*) FROM bot_stats")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO bot_stats DEFAULT VALUES")
            
            conn.commit()
            print("✅ PostgreSQL tables initialized")
    
    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        """Log new trade"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if DATABASE_URL:
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
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO trades (
                        signature, token_mint, token_symbol, entry_price, 
                        amount, whale_signature, whale_amount_usd, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        """Close trade"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if DATABASE_URL:
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
            else:
                cursor.execute("""
                    UPDATE trades 
                    SET status = 'closed', 
                        exit_price = ?, 
                        profit_sol = ?, 
                        profit_usd = ?,
                        closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (exit_price, profit_sol, profit_usd, trade_id))
            
            result = cursor.fetchone()
            conn.commit()
            return result is not None
    
    def log_whale_alert(self, alert_data: Dict[str, Any]) -> int:
        """Log whale detection"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if DATABASE_URL:
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
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO whale_alerts (
                        signature, trader_address, token_mint, token_symbol,
                        amount_usd, amount_tokens, transaction_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
            return result[0] if result else None
    
    def mark_whale_followed(self, alert_id: int, trade_id: int):
        """Mark whale as followed"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if DATABASE_URL:
                cursor.execute("""
                    UPDATE whale_alerts 
                    SET followed = TRUE, our_trade_id = %s
                    WHERE id = %s
                """, (trade_id, alert_id))
            else:
                cursor.execute("""
                    UPDATE whale_alerts 
                    SET followed = 1, our_trade_id = ?
                    WHERE id = ?
                """, (trade_id, alert_id))
            
            conn.commit()
    
    def get_open_trades(self) -> List[Dict]:
        """Get open trades"""
        with self._get_connection() as conn:
            if DATABASE_URL:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE status = 'open' 
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE status = 'open' 
                    ORDER BY created_at DESC
                """)
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        with self._get_connection() as conn:
            if DATABASE_URL:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable_trades,
                        SUM(profit_sol) as total_profit_sol,
                        SUM(profit_usd) as total_profit_usd
                    FROM trades 
                    WHERE status = 'closed'
                """)
                return dict(cursor.fetchone())
            else:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable_trades,
                        SUM(profit_sol) as total_profit_sol,
                        SUM(profit_usd) as total_profit_usd
                    FROM trades 
                    WHERE status = 'closed'
                """)
                row = cursor.fetchone()
                return {
                    'total_trades': row[0],
                    'profitable_trades': row[1],
                    'total_profit_sol': row[2],
                    'total_profit_usd': row[3]
                }

# Global instance
db = Database()
