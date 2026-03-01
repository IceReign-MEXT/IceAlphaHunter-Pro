import requests
import os
import base58
from solders.keypair import Keypair
from solana.rpc.api import Client

def buy_token(mint_address):
    priv_key = os.getenv("BOT_PRIVATE_KEY")
    amount = int(float(os.getenv("DEFAULT_AMOUNT_SOL", 0.1)) * 10**9)
    
    # 1. Get the best price from Jupiter V6
    quote_url = f"https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112&outputMint={mint_address}&amount={amount}&slippageBps=100"
    quote = requests.get(quote_url).json()
    
    # 2. In a live trade, this would sign and blast via Helius Fast Sender
    print(f"💰 EXECUTING BUY: {amount} Lamports into {mint_address}")
    return quote
