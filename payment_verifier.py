import os
from dotenv import load_dotenv
from etherscan import Etherscan
from web3 import Web3
from solana.rpc.api import Client as SolanaClient

# --- LOAD ENV VARIABLES ---
load_dotenv()

ETH_WALLET = os.getenv("ETH_WALLET")
SOL_WALLET = os.getenv("SOL_WALLET")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
SOLANA_RPC_URL = os.getenv("SOL_RPC_URL", "https://api.mainnet-beta.solana.com")

# Subscription amounts
SUBSCRIPTION_AMOUNT_ETH = 0.1
SUBSCRIPTION_AMOUNT_SOL = 0.5  # Example: 0.5 SOL per subscription

# Confirmation requirements
MIN_CONFIRMATIONS_ETH = 2
MIN_CONFIRMATIONS_SOL = 2

# Initialize clients
eth_client = Etherscan(ETHERSCAN_API_KEY) if ETHERSCAN_API_KEY else None
sol_client = SolanaClient(SOLANA_RPC_URL)
SUBSCRIPTION_AMOUNT_WEI = Web3.to_wei(SUBSCRIPTION_AMOUNT_ETH, 'ether')
used_tx_hashes = set()

def check_payment_on_blockchain(tx_hash, currency="ETH"):
    """
    Verify payment in ETH or SOL.
    Returns: dict(status, message)
    """
    if tx_hash in used_tx_hashes:
        return {"status": "pending", "message": "This transaction has already been used."}

    try:
        if currency.upper() == "ETH":
            if not eth_client:
                return {"status": "error", "message": "Etherscan API Key not set."}

            tx = eth_client.get_transaction_by_hash(tx_hash)
            if not tx:
                return {"status": "pending", "message": "Transaction not found. Waiting for network confirmation."}

            receipt = eth_client.get_transaction_receipt(tx_hash)
            if not receipt or receipt.status == '0':
                return {"status": "pending", "message": "Transaction failed or not yet confirmed."}

            latest_block = int(eth_client.get_block_number())
            tx_block = int(tx['blockNumber'])
            confirmations = latest_block - tx_block + 1
            if confirmations < MIN_CONFIRMATIONS_ETH:
                return {"status": "pending", "message": f"{confirmations}/{MIN_CONFIRMATIONS_ETH} ETH confirmations. Waiting..."}

            tx_value = int(tx['value'])
            if tx_value < SUBSCRIPTION_AMOUNT_WEI:
                return {"status": "pending", "message": f"Payment too low. Expected {SUBSCRIPTION_AMOUNT_ETH} ETH."}

            if tx['to'].lower() != ETH_WALLET.lower():
                return {"status": "pending", "message": "Payment sent to wrong ETH wallet."}

        elif currency.upper() == "SOL":
            # Get confirmed transaction from Solana
            result = sol_client.get_confirmed_transaction(tx_hash)
            if not result['result']:
                return {"status": "pending", "message": "SOL transaction not found or not confirmed."}

            tx_info = result['result']['transaction']
            meta = result['result']['meta']
            if meta['err']:
                return {"status": "pending", "message": "SOL transaction failed."}

            # Check destination and amount (simplified)
            sol_amount = 0
            for instr in tx_info['message']['instructions']:
                if instr['program'] == 'system':
                    lamports = int(instr['data'], 16)
                    sol_amount += lamports / 1e9

            if sol_amount < SUBSCRIPTION_AMOUNT_SOL:
                return {"status": "pending", "message": f"Payment too low. Expected {SUBSCRIPTION_AMOUNT_SOL} SOL."}

            if SOL_WALLET not in str(tx_info):
                return {"status": "pending", "message": "Payment sent to wrong SOL wallet."}

        else:
            return {"status": "error", "message": f"Unsupported currency: {currency}"}

        # ✅ Success
        used_tx_hashes.add(tx_hash)
        return {"status": "success", "message": f"{currency.upper()} payment verified. Access granted."}

    except Exception as e:
        return {"status": "error", "message": f"Verification failed: {str(e)}"}
