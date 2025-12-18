import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    # Updated table to include referral tracking
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  expiry_date TEXT,
                  referral_count INTEGER DEFAULT 0,
                  trial_used INTEGER DEFAULT 0)''')
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

def add_subscription(user_id, hours):
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    # Get current expiry if it exists, otherwise start from now
    if check_premium(user_id):
        c.execute("SELECT expiry_date FROM users WHERE user_id = ?", (user_id,))
        current_expiry = datetime.strptime(c.fetchone()[0], '%Y-%m-%d %H:%M:%S')
        new_expiry = current_expiry + timedelta(hours=hours)
    else:
        new_expiry = datetime.now() + timedelta(hours=hours)

    expiry_str = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_date) VALUES (?, ?)", (user_id, expiry_str))
    conn.commit()
    conn.close()

def add_referral(referrer_id):
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    # Increment referral count
    c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (referrer_id,))

    # Check if they hit the 3-referral milestone
    c.execute("SELECT referral_count, trial_used FROM users WHERE user_id = ?", (referrer_id,))
    res = c.fetchone()
    if res and res[0] >= 3 and res[1] == 0:
        # Reset count, mark trial as used, and give 24 hours
        c.execute("UPDATE users SET referral_count = 0, trial_used = 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()
        conn.close()
        add_subscription(referrer_id, 24)
        return True # Reward granted
    conn.commit()
    conn.close()
    return False

def get_user_stats(user_id):
    conn = sqlite3.connect('ice_alpha.db')
    c = conn.cursor()
    c.execute("SELECT referral_count, trial_used FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res if res else (0, 0)
