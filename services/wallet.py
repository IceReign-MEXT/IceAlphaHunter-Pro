import base58
from solathon import Keypair

def create_burner():
    # Generate a fresh keypair
    kp = Keypair()
    pub_key = str(kp.public_key)
    # Get the private key string
    priv_key = kp.private_key
    return pub_key, priv_key

if __name__ == "__main__":
    pub, priv = create_burner()
    print("\n⚔️ NEW BOT WALLET GENERATED")
    print("================================")
    print(f"PUBLIC ADDRESS: {pub}")
    print(f"PRIVATE KEY:    {priv}")
    print("================================\n")
