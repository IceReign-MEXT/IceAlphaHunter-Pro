import os
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_telegram():
    """Test Telegram bot connection"""
    try:
        from telegram import Bot
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN not set")
            return False
        
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"✅ Telegram Bot: @{me.username} (ID: {me.id})")
        return True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

async def test_helius():
    """Test Helius RPC connection"""
    try:
        from solana.rpc.async_api import AsyncClient
        rpc_url = os.getenv('HELIUS_RPC_URL')
        if not rpc_url:
            print("❌ HELIUS_RPC_URL not set")
            return False
        
        client = AsyncClient(rpc_url)
        health = await client.get_health()
        slot = await client.get_slot()
        print(f"✅ Helius RPC: Healthy (Slot: {slot.value})")
        await client.close()
        return True
    except Exception as e:
        print(f"❌ Helius Error: {e}")
        return False

async def test_supabase():
    """Test Supabase connection"""
    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            print("❌ Supabase credentials not set")
            return False
        
        client = create_client(url, key)
        # Try a simple query
        response = client.table('trades').select('*').limit(1).execute()
        print(f"✅ Supabase: Connected")
        return True
    except Exception as e:
        print(f"❌ Supabase Error: {e}")
        print("   (This is OK if tables don't exist yet)")
        return False

async def test_wallet():
    """Test wallet loading"""
    try:
        from solders.keypair import Keypair
        import base58
        
        private_key = os.getenv('WALLET_PRIVATE_KEY')
        if not private_key:
            print("❌ WALLET_PRIVATE_KEY not set")
            return False
        
        if ',' in private_key:
            key_bytes = bytes([int(x) for x in private_key.strip('[]').split(',')])
        else:
            key_bytes = base58.b58decode(private_key)
        
        keypair = Keypair.from_bytes(key_bytes)
        print(f"✅ Wallet: {keypair.pubkey()}")
        return True
    except Exception as e:
        print(f"❌ Wallet Error: {e}")
        return False

async def main():
    print("🧪 TESTING CONNECTIONS")
    print("=" * 50)
    
    results = await asyncio.gather(
        test_telegram(),
        test_helius(),
        test_supabase(),
        test_wallet()
    )
    
    print("=" * 50)
    if all(results):
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
