from etherscan import Etherscan
import os
from web3 import Web3 # Still needed for amount conversion

# --- Configuration ---
SUBSCRIPTION_AMOUNT_ETH = 0.1
target_wallet = os.getenv("ETH_WALLET")

def check_payment_on_blockchain(tx_hash, target_wallet):
    """
    Checks payment using the Etherscan API for speed and reliability.
    """
    try:
        api_key = os.getenv("ETHERSCAN_API_KEY")
        if not api_key:
            return {"status": "error", "message": "Etherscan API Key not set."}

        eth = Etherscan(api_key)

        # 1. Get Transaction Receipt Status
        receipt = eth.get_transaction_receipt(tx_hash)
        if receipt is None or receipt.status == '0':
            return {"status": "pending", "message": "TX not confirmed, or it failed/reverted."}

        # 2. Get Transaction Details
        tx = eth.get_transaction_by_hash(tx_hash)

        # Convert 0.1 ETH to Wei for comparison
        SUBSCRIPTION_AMOUNT_WEI = Web3.to_wei(SUBSCRIPTION_AMOUNT_ETH, 'ether')

        tx_value = int(tx['value'])

        # 3. Validation Checks
        if tx_value >= SUBSCRIPTION_AMOUNT_WEI and tx['to'] == target_wallet.lower():
            return {"status": "success", "message": "Payment verified. Access granted."}
        else:
            return {"status": "pending", "message": "Amount or destination incorrect."}

    except Exception as e:
        return {"status": "error", "message": f"Verification failed: {str(e)}"}
