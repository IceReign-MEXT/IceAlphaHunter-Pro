"""PostgreSQL Database Module - psycopg v3"""
import os
import psycopg
from psycopg.rows import dict_row
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """PostgreSQL Database Handler using psycopg v3"""
    
    def __init__(self):
        self.connection_string = os.getenv("DATABASE_URL", "")
        self.conn = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        try:
            self.conn = psycopg.connect(self.connection_string, row_factory=dict_row)
            logger.info("✅ Database connected (psycopg v3)")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def init_tables(self):
        tables = [
            """
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                tx_signature VARCHAR(100) UNIQUE,
                token_address VARCHAR(50),
                token_symbol VARCHAR(20),
                entry_price DECIMAL(20, 10),
                exit_price DECIMAL(20, 10),
                amount DECIMAL(20, 10),
                profit_sol DECIMAL(20, 10),
                profit_usd DECIMAL(20, 10),
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS whale_alerts (
                id SERIAL PRIMARY KEY,
                whale_address VARCHAR(50),
                token_address VARCHAR(50),
                token_symbol VARCHAR(20),
                amount DECIMAL(20, 10),
                amount_usd DECIMAL(20, 2),
                tx_signature VARCHAR(100),
                alert_type VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                username VARCHAR(50),
                subscription_type VARCHAR(20) DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS monitored_wallets (
                id SERIAL PRIMARY KEY,
                address VARCHAR(50) UNIQUE,
                label VARCHAR(50),
                is_whale BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        with self.conn.cursor() as cur:
            for sql in tables:
                cur.execute(sql)
        self.conn.commit()
        logger.info("✅ Database tables initialized")
    
    def save_trade(self, trade_data: Dict) -> int:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trades (tx_signature, token_address, token_symbol, entry_price, amount, status)
                VALUES (%(tx_signature)s, %(token_address)s, %(token_symbol)s, %(entry_price)s, %(amount)s, %(status)s)
                ON CONFLICT (tx_signature) DO NOTHING
                RETURNING id
            """, trade_data)
            result = cur.fetchone()
            self.conn.commit()
            return result["id"] if result else 0
    
    def get_trades(self, limit: int = 100) -> List[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT %s", (limit,))
            return cur.fetchall()
    
    def save_whale_alert(self, alert_data: Dict) -> int:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO whale_alerts (whale_address, token_address, token_symbol, amount, amount_usd, tx_signature, alert_type)
                VALUES (%(whale_address)s, %(token_address)s, %(token_symbol)s, %(amount)s, %(amount_usd)s, %(tx_signature)s, %(alert_type)s)
                RETURNING id
            """, alert_data)
            result = cur.fetchone()
            self.conn.commit()
            return result["id"] if result else 0
    
    def get_recent_whale_alerts(self, limit: int = 50) -> List[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM whale_alerts ORDER BY created_at DESC LIMIT %s", (limit,))
            return cur.fetchall()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone()
    
    def save_user(self, user_data: Dict):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username, subscription_type)
                VALUES (%(user_id)s, %(username)s, %(subscription_type)s)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
            """, user_data)
            self.conn.commit()
    
    def add_monitored_wallet(self, address: str, label: str = "", is_whale: bool = False):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO monitored_wallets (address, label, is_whale)
                VALUES (%s, %s, %s)
                ON CONFLICT (address) DO NOTHING
            """, (address, label, is_whale))
            self.conn.commit()
    
    def get_monitored_wallets(self) -> List[Dict]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM monitored_wallets")
            return cur.fetchall()

db = Database()
