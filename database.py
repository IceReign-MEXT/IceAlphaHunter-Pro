import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  expiry_date TEXT, 
                  points INTEGER DEFAULT 0,
                  referrer_id INTEGER)''')
    conn.commit()
    conn.close()

def check_premium(user_id):
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    if res and res[0]:
        expiry = datetime.strptime(res[0], '%Y-%m-%d %H:%M:%S')
        return expiry > datetime.now()
    return False

def add_subscription(user_id, days):
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    expiry = datetime.now() + timedelta(days=days)
    expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry_str))
    conn.commit()
    conn.close()
