"""Database - With Fallback"""
import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Try to load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

DATABASE_URL = os.getenv('DATABASE_URL', '')

class Database:
    def __init__(self):
        self.connection_string = DATABASE_URL
        self.sqlite_db = 'trades.db'
        self.using_postgres = False
        
        if DATABASE_URL and 'postgresql' in DATABASE_URL:
            try:
                self._init_postgres()
                self.using_postgres = True
                logger.info("✅ Using PostgreSQL")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL failed: {e}")
                logger.info("🔄 Falling back to SQLite")
                self._init_sqlite()
        else:
            self._init_sqlite()
            logger.info("✅ Using SQLite")
    
    def _init_sqlite(self):
        """Initialize SQLite"""
        try:
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
        except Exception as e:
            logger.error(f"SQLite init error: {e}")
            raise
    
    def _init_postgres(self):
        """Initialize PostgreSQL"""
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(self.connection_string)
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
        conn.close()
    
    @contextmanager
    def _get_connection(self):
        if self.using_postgres:
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.sqlite_db)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.using_postgres:
                    from psycopg2.extras import RealDictCursor
                    cursor.execute("""
                        INSERT INTO trades (signature, token_mint, token_symbol, entry_price, 
                        amount, whale_signature, whale_amount_usd, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                        INSERT OR IGNORE INTO trades (signature, token_mint, token_symbol, entry_price, 
                        amount, whale_signature, whale_amount_usd, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                return result[0] if result else cursor.lastrowid if not self.using_postgres else None
        except Exception as e:
            logger.error(f"Log trade error: {e}")
            return None
    
    def close_trade(self, trade_id: int, exit_price: float, 
                   profit_sol: float, profit_usd: float, 
                   exit_signature: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.using_postgres:
                    cursor.execute("""
                        UPDATE trades SET status = 'closed', exit_price = %s, 
                        profit_sol = %s, profit_usd = %s, closed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (exit_price, profit_sol, profit_usd, trade_id))
                else:
                    cursor.execute("""
                        UPDATE trades SET status = 'closed', exit_price = ?, 
                        profit_sol = ?, profit_usd = ?, closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (exit_price, profit_sol, profit_usd, trade_id))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Close trade error: {e}")
            return False
    
    def log_whale_alert(self, alert_data: Dict[str, Any]) -> int:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.using_postgres:
                    cursor.execute("""
                        INSERT INTO whale_alerts (signature, trader_address, token_mint, token_symbol,
                        amount_usd, amount_tokens, transaction_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                        INSERT OR IGNORE INTO whale_alerts (signature, trader_address, token_mint, token_symbol,
                        amount_usd, amount_tokens, transaction_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
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
                return result[0] if result else cursor.lastrowid if not self.using_postgres else None
        except Exception as e:
            logger.error(f"Log whale error: {e}")
            return None
    
    def mark_whale_followed(self, alert_id: int, trade_id: int):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if self.using_postgres:
                    cursor.execute("""
                        UPDATE whale_alerts SET followed = TRUE, our_trade_id = %s WHERE id = %s
                    """, (trade_id, alert_id))
                else:
                    cursor.execute("""
                        UPDATE whale_alerts SET followed = 1, our_trade_id = ? WHERE id = ?
                    """, (trade_id, alert_id))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Mark followed error: {e}")
    
    def get_open_trades(self) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                if self.using_postgres:
                    from psycopg2.extras import RealDictCursor
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY created_at DESC")
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY created_at DESC")
                    columns = [description[0] for description in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Get open trades error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        try:
            with self._get_connection() as conn:
                if self.using_postgres:
                    from psycopg2.extras import RealDictCursor
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable_trades,
                        SUM(profit_sol) as total_profit_sol,
                        SUM(profit_usd) as total_profit_usd
                        FROM trades WHERE status = 'closed'
                    """)
                    return dict(cursor.fetchone())
                else:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_sol > 0 THEN 1 ELSE 0 END) as profitable_trades,
                        SUM(profit_sol) as total_profit_sol,
                        SUM(profit_usd) as total_profit_usd
                        FROM trades WHERE status = 'closed'
                    """)
                    row = cursor.fetchone()
                    return {
                        'total_trades': row[0] or 0,
                        'profitable_trades': row[1] or 0,
                        'total_profit_sol': row[2] or 0,
                        'total_profit_usd': row[3] or 0
                    }
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            return {
                'total_trades': 0,
                'profitable_trades': 0,
                'total_profit_sol': 0,
                'total_profit_usd': 0
            }

# Create instance with error handling
try:
    db = Database()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    # Create dummy db object
    class DummyDB:
        def log_trade(self, *args, **kwargs): return None
        def close_trade(self, *args, **kwargs): return False
        def log_whale_alert(self, *args, **kwargs): return None
        def mark_whale_followed(self, *args, **kwargs): pass
        def get_open_trades(self, *args, **kwargs): return []
        def get_stats(self, *args, **kwargs): return {'total_trades': 0, 'profitable_trades': 0, 'total_profit_sol': 0, 'total_profit_usd': 0}
    db = DummyDB()
    logger.warning("⚠️ Using dummy database - no persistence!")
