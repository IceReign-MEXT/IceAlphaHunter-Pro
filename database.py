"""SQLite Database - No external dependencies"""
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
        self.sqlite_db = 'trades.db'
        self._init_sqlite()
        logger.info("✅ SQLite database initialized")
    
    def _init_sqlite(self):
        """Initialize SQLite"""
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
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.sqlite_db)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def log_trade(self, trade_data: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
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
            conn.commit()
            return cursor.lastrowid
    
    def close_trade(self, trade_id: int, exit_price: float, 
                   profit_sol: float, profit_usd: float, 
                   exit_signature: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades 
                SET status = 'closed', 
                    exit_price = ?, 
                    profit_sol = ?, 
                    profit_usd = ?,
                    closed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (exit_price, profit_sol, profit_usd, trade_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def log_whale_alert(self, alert_data: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
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
            conn.commit()
            return cursor.lastrowid
    
    def mark_whale_followed(self, alert_id: int, trade_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE whale_alerts 
                SET followed = 1, our_trade_id = ?
                WHERE id = ?
            """, (trade_id, alert_id))
            conn.commit()
    
    def get_open_trades(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status = 'open' 
                ORDER BY created_at DESC
            """)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        with self._get_connection() as conn:
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
                'total_trades': row[0] or 0,
                'profitable_trades': row[1] or 0,
                'total_profit_sol': row[2] or 0,
                'total_profit_usd': row[3] or 0,
                'win_rate': 0  # Calculate if needed
            }

db = Database()
