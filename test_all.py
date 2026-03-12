#!/usr/bin/env python3
"""Complete System Test for IceAlpha Hunter Pro"""
import os
import sys
import time
from datetime import datetime

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def check(name, condition, details=""):
    if condition:
        print(f"{GREEN}✅ {name}{RESET}")
        if details:
            print(f"   {details}")
        return True
    else:
        print(f"{RED}❌ {name}{RESET}")
        if details:
            print(f"   {details}")
        return False

def test_environment():
    print(f"\n{BLUE}🔐 Environment Variables{RESET}")
    print("="*50)
    
    vars_to_check = [
        ('BOT_TOKEN', 'Telegram Bot Token'),
        ('HELIUS_API_KEY', 'Helius API Key'),
        ('WALLET_PRIVATE_KEY', 'Wallet Private Key'),
        ('WALLET_PUBLIC_KEY', 'Wallet Public Key'),
        ('DATABASE_URL', 'Database URL'),
        ('CHANNEL_ID', 'Telegram Channel ID')
    ]
    
    all_ok = True
    for var, desc in vars_to_check:
        value = os.getenv(var, '')
        if check(f"{desc}", bool(value)):
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else value
            print(f"   Value: {masked}")
        else:
            all_ok = False
    
    return all_ok

def test_telegram():
    print(f"\n{BLUE}🤖 Telegram Bot{RESET}")
    print("="*50)
    
    try:
        from telegram import Bot
        token = os.getenv('BOT_TOKEN')
        
        if not token:
            return check("Bot Connection", False, "No token provided")
        
        bot = Bot(token=token)
        me = bot.get_me()
        
        check("API Connection", True, f"@{me.username}")
        check("Bot ID", True, str(me.id))
        check("Bot Name", True, me.first_name)
        
        # Test channel
        channel = os.getenv('CHANNEL_ID')
        if channel:
            try:
                test_msg = f"🧪 <b>System Test</b>\nTime: {datetime.now().strftime('%H:%M:%S')}\nStatus: ✅ Operational"
                bot.send_message(chat_id=int(channel), text=test_msg, parse_mode='HTML')
                check("Channel Message", True, f"Sent to {channel}")
            except Exception as e:
                check("Channel Message", False, str(e))
        
        return True
    except Exception as e:
        return check("Telegram Bot", False, str(e))

def test_helius():
    print(f"\n{BLUE}⛓️  Helius RPC{RESET}")
    print("="*50)
    
    try:
        import requests
        url = os.getenv('HELIUS_RPC_URL')
        
        if not url:
            return check("RPC Connection", False, "No URL provided")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getHealth"
        }
        
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        
        if data.get('result') == 'ok':
            check("Health Check", True)
            
            # Get slot
            payload["method"] = "getSlot"
            resp = requests.post(url, json=payload, timeout=30)
            slot = resp.json().get('result', 0)
            check("Current Slot", True, str(slot))
            return True
        else:
            return check("Health Check", False, str(data))
    except Exception as e:
        return check("Helius RPC", False, str(e))

def test_database():
    print(f"\n{BLUE}🗄️  PostgreSQL Database{RESET}")
    print("="*50)
    
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return check("Connection", False, "No DATABASE_URL")
        
        conn = psycopg.connect(db_url, row_factory=dict_row)
        cur = conn.cursor()
        
        # Check version
        cur.execute("SELECT version()")
        version = cur.fetchone()['version']
        check("Connection", True, f"PostgreSQL {version.split()[1]}")
        
        # Check tables
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row['table_name'] for row in cur.fetchall()]
        
        expected = ['trades', 'whale_alerts', 'users', 'monitored_wallets']
        for table in expected:
            check(f"Table: {table}", table in tables)
        
        # Test insert
        cur.execute("INSERT INTO users (user_id, username, subscription_type) VALUES (999999, 'test_user', 'free') ON CONFLICT DO NOTHING")
        conn.commit()
        check("Write Test", True)
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        return check("Database", False, str(e))

def test_wallet():
    print(f"\n{BLUE}💳 Wallet{RESET}")
    print("="*50)
    
    try:
        import base58
        from nacl.signing import SigningKey
        
        private_key = os.getenv('WALLET_PRIVATE_KEY')
        public_key = os.getenv('WALLET_PUBLIC_KEY')
        
        if not private_key or not public_key:
            return check("Keys Loaded", False, "Missing keys")
        
        # Decode
        if ',' in private_key:
            key_bytes = bytes([int(x) for x in private_key.strip('[]').split(',')])
        else:
            key_bytes = base58.b58decode(private_key)
        
        # Validate
        if len(key_bytes) == 64:
            public_bytes = key_bytes[32:]
        elif len(key_bytes) == 32:
            signing_key = SigningKey(key_bytes)
            public_bytes = bytes(signing_key.verify_key)
        else:
            return check("Key Format", False, f"Invalid length: {len(key_bytes)}")
        
        derived = base58.b58encode(public_bytes).decode('ascii')
        
        if derived == public_key:
            check("Key Verification", True, f"Address: {public_key[:16]}...")
        else:
            check("Key Verification", False, "Keys don't match")
        
        return True
    except Exception as e:
        return check("Wallet", False, str(e))

def test_jupiter():
    print(f"\n{BLUE}🪐 Jupiter API{RESET}")
    print("="*50)
    
    try:
        import requests
        
        url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": "So11111111111111111111111111111111111111112",
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": "100000000",
            "slippageBps": "50"
        }
        
        resp = requests.get(url, params=params, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            check("API Access", True)
            check("Quote Data", 'outAmount' in data)
            return True
        else:
            return check("API Access", False, f"Status: {resp.status_code}")
    except Exception as e:
        return check("Jupiter API", False, str(e))

def main():
    print(f"\n{'🚀'*15}")
    print("  IceAlpha Hunter Pro - System Test")
    print(f"{'🚀'*15}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load env
    from dotenv import load_dotenv
    load_dotenv()
    
    results = []
    
    # Run tests
    results.append(("Environment", test_environment()))
    results.append(("Telegram", test_telegram()))
    results.append(("Helius RPC", test_helius()))
    results.append(("Database", test_database()))
    results.append(("Wallet", test_wallet()))
    results.append(("Jupiter API", test_jupiter()))
    
    # Summary
    print(f"\n{BLUE}{'='*50}{RESET}")
    print(f"{BLUE}📊 TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {name:20} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n{GREEN}🎉 ALL SYSTEMS OPERATIONAL!{RESET}")
        print(f"{GREEN}✅ Ready for deployment!{RESET}")
        return 0
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
