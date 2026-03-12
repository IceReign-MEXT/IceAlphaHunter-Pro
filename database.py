"""PostgreSQL Database Module - Robust Version"""
import os
import sys
import time
import logging

logger = logging.getLogger(__name__)

# Try different PostgreSQL libraries
def get_db_lib():
    try:
        import psycopg
        return 'psycopg'
    except ImportError:
        try:
            import psycopg2
            return 'psycopg2'
        except ImportError:
            return None

DB_LIB = get_db_lib()

if DB_LIB == 'psycopg':
    import psycopg
    from psycopg.rows import dict_row
elif DB_LIB == 'psycopg2':
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    logger.error("No PostgreSQL library found!")
    # Create mock database for testing
    class MockDB:
        def save_trade(self, x): return 1
        def get_trades(self, x): return []
        def save_whale_alert(self, x): return 1
        def get_recent_whale_alerts(self, x): return []
        def get_user(self, x): return None
        def save_user(self, x): pass
        def add_monitored_wallet(self, *x): pass
        def get_monitored_wallets(self): return []
    
    db = MockDB()
    logger.warning("Using MOCK database - install psycopg for real database")
    sys.exit(0)

class Database:
    """PostgreSQL Database Handler"""
    
    def __init__(self):
        self.connection_string = self._fix_connection_string(os.getenv("DATABASE_URL", ""))
        self.conn = None
        self._connect_with_retry()
        self.init_tables()
    
    def _fix_connection_string(self, url):
        """Fix Render PostgreSQL URL format if needed"""
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    
    def _connect_with_retry(self, max_retries=3):
        """Connect with retry logic"""
        for i in range(max_retries):
            try:
                if DB_LIB == 'psycopg':
                    self.conn = psycopg.connect(self.connection_string, row_factory=dict_row)
                else:
                    self.conn = psycopg2.connect(self.connection_string)
                    self.conn.autocommit = True
                logger.info(f"✅ Database connected ({DB_LIB})")
                return
            except Exception as e:
                logger.error(f"❌ DB connection attempt {i+1} failed: {e}")
                if i < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
    
    def init_tables(self):
        tables = [
            """CREATE TABLE IF NOT EXISTS trades (
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
            )""",
            """CREATE TABLE IF NOT EXISTS whale_alerts (
                id SERIAL PRIMARY KEY,
                whale_address VARCHAR(50),
                token_address VARCHAR(50),
                token_symbol VARCHAR(20),
                amount DECIMAL(20, 10),
                amount_usd DECIMAL(20, 2),
                tx_signature VARCHAR(100),
                alert_type VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                username VARCHAR(50),
                subscription_type VARCHAR(20) DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS monitored_wallets (
                id SERIAL PRIMARY KEY,
                address VARCHAR(50) UNIQUE,
                label VARCHAR(50),
                is_whale BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        try:
            with self.conn.cursor() as cur:
                for sql in tables:
                    cur.execute(sql)
            if DB_LIB == 'psycopg':
                self.conn.commit()
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.error(f"❌ Table creation error: {e}")
    
    def save_trade(self, trade_data: dict) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO trades (tx_signature, token_address, token_symbol, entry_price, amount, status)
                    VALUES (%(tx_signature)s, %(token_address)s, %(token_symbol)s, %(entry_price)s, %(amount)s, %(status)s)
                    ON CONFLICT (tx_signature) DO NOTHING
                    RETURNING id
                """, trade_data)
                result = cur.fetchone()
                if DB_LIB == 'psycopg':
                    self.conn.commit()
                return result["id"] if result and DB_LIB == 'psycopg' else result[0] if result else 0
        except Exception as e:
            logger.error(f"Save trade error: {e}")
            return 0
    
    def get_trades(self, limit: int = 100):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                if DB_LIB == 'psycopg':
                    return rows
                else:
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get trades error: {e}")
            return []
    
    def save_whale_alert(self, alert_data: dict) -> int:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO whale_alerts (whale_address, token_address, token_symbol, amount, amount_usd, tx_signature, alert_type)
                    VALUES (%(whale_address)s, %(token_address)s, %(token_symbol)s, %(amount)s, %(amount_usd)s, %(tx_signature)s, %(alert_type)s)
                    RETURNING id
                """, alert_data)
                result = cur.fetchone()
                if DB_LIB == 'psycopg':
                    self.conn.commit()
                return result["id"] if result and DB_LIB == 'psycopg' else result[0] if result else 0
        except Exception as e:
            logger.error(f"Save alert error: {e}")
            return 0
    
    def get_recent_whale_alerts(self, limit: int = 50):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM whale_alerts ORDER BY created_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                if DB_LIB == 'psycopg':
                    return rows
                else:
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get alerts error: {e}")
            return []
    
    def get_user(self, user_id: int):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def save_user(self, user_data: dict):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, username, subscription_type)
                    VALUES (%(user_id)s, %(username)s, %(subscription_type)s)
                    ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
                """, user_data)
                if DB_LIB == 'psycopg':
                    self.conn.commit()
        except Exception as e:
            logger.error(f"Save user error: {e}")
    
    def add_monitored_wallet(self, address: str, label: str = "", is_whale: bool = False):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitored_wallets (address, label, is_whale)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (address) DO NOTHING
                """, (address, label, is_whale))
                if DB_LIB == 'psycopg':
                    self.conn.commit()
        except Exception as e:
            logger.error(f"Add wallet error: {e}")
    
    def get_monitored_wallets(self):
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM monitored_wallets")
                rows = cur.fetchall()
                if DB_LIB == 'psycopg':
                    return rows
                else:
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get wallets error: {e}")
            return []

db = Database()
