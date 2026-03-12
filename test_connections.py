import os
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

def test_telegram():
    try:
        from telegram import Bot
        token = os.getenv('BOT_TOKEN')
        if not token:
            print("❌ BOT_TOKEN not set")
            return False
        bot = Bot(token=token)
        me = bot.get_me()
        print(f"✅ Telegram Bot: @{me.username}")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

async def test_helius():
    try:
        from solana.rpc.async_api import AsyncClient
        rpc_url = os.getenv('HELIUS_RPC_URL')
        if not rpc_url:
            print("❌ HELIUS_RPC_URL not set")
            return False
        client = AsyncClient(rpc_url)
        slot = await client.get_slot()
        print(f"✅ Helius RPC: Slot {slot}")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Helius Error: {e}")
        return False

def test_supabase():
    try:
        import requests
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        if not url or not key:
            print("❌ Supabase credentials not set")
            return False
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        response = requests.get(f"{url}/rest/v1/trades?limit=1", headers=headers, timeout=10)
        print(f"✅ Supabase: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Supabase Error: {e}")
        return False

def test_wallet():
    try:
        import base58
        from nacl.signing import SigningKey
        private_key = os.getenv('WALLET_PRIVATE_KEY')
        if not private_key:
            print("❌ WALLET_PRIVATE_KEY not set")
            return False
        
        if ',' in private_key:
            key_bytes = bytes([int(x) for x in private_key.strip('[]').split(',')])
        else:
            key_bytes = base58.b58decode(private_key)
        
        # Derive public key
        if len(key_bytes) == 64:
            public_key_bytes = key_bytes[32:]
        else:
            signing_key = SigningKey(key_bytes[:32])
            public_key_bytes = bytes(signing_key.verify_key)
        
        public_key = base58.b58encode(public_key_bytes).decode('ascii')
        print(f"✅ Wallet: {public_key[:20]}...")
        return True
    except Exception as e:
        print(f"❌ Wallet Error: {e}")
        return False

async def main():
    print("🧪 TESTING CONNECTIONS")
    print("=" * 50)
    results = [test_telegram(), await test_helius(), test_supabase(), test_wallet()]
    print("=" * 50)
    if all(results):
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
