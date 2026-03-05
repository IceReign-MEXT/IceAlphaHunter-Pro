from solders.keypair import Keypair
import base58
import os
from dotenv import load_dotenv

load_dotenv()

def generate_wallet():
    """Generate new Solana wallet"""
    keypair = Keypair()
    private_key = list(keypair.to_bytes_array())
    public_key = str(keypair.pubkey())
    
    print("🆕 NEW WALLET GENERATED")
    print("=" * 50)
    print(f"📍 Public Key: {public_key}")
    print(f"🔑 Private Key (save this!): {private_key}")
    print(f"🔑 Private Key (base58): {base58.b58encode(bytes(private_key)).decode()}")
    print("=" * 50)
    print("⚠️  SAVE THESE IN YOUR .env FILE!")
    print("⚠️  NEVER SHARE YOUR PRIVATE KEY!")
    
    return {
        'public_key': public_key,
        'private_key': private_key,
        'private_key_base58': base58.b58encode(bytes(private_key)).decode()
    }

def load_existing_wallet():
    """Load and display existing wallet from .env"""
    private_key = os.getenv('WALLET_PRIVATE_KEY')
    if not private_key:
        print("❌ No wallet found in .env")
        return None
    
    try:
        if ',' in private_key:
            key_bytes = bytes([int(x) for x in private_key.strip('[]').split(',')])
        else:
            key_bytes = base58.b58decode(private_key)
        
        keypair = Keypair.from_bytes(key_bytes)
        print("✅ WALLET LOADED")
        print(f"📍 Address: {keypair.pubkey()}")
        return keypair
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        return None

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "new":
        generate_wallet()
    else:
        print("Usage: python gen_wallet.py new")
        print("Or run without args to load existing wallet from .env")
        load_existing_wallet()
