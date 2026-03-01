from solathon import Client, Keypair, Transaction
import os
from dotenv import load_dotenv

load_dotenv()

def withdraw(destination_addr):
    client = Client(os.getenv("RPC_URL"))
    # The bot's key from .env
    wallet = Keypair.from_private_key(os.getenv("BOT_PRIVATE_KEY"))
    
    # This is a simplified version; in reality, you'd send a transfer transaction
    print(f"📦 Initiating withdrawal from {wallet.public_key}")
    print(f"🚀 Destination: {destination_addr}")
    print("⚠️ Use your Phantom App to import the Private Key for the fastest withdrawal.")

if __name__ == "__main__":
    dest = input("Enter your Safe Wallet Address: ")
    withdraw(dest)
