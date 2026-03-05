#!/usr/bin/env python3
"""Generate Solana wallet using nacl"""
import nacl.signing
import nacl.encoding
import base58
import json

# Generate ed25519 keypair
signing_key = nacl.signing.SigningKey.generate()
verify_key = signing_key.verify_key

# Get bytes
secret_bytes = signing_key.encode()
public_bytes = verify_key.encode()

# Base58 encode (Solana format)
private_key = base58.b58encode(secret_bytes + public_bytes).decode()
public_key = base58.b58encode(public_bytes).decode()

# Save backup
wallet_data = list(secret_bytes + public_bytes)
with open('bot-wallet.json', 'w') as f:
    json.dump(wallet_data, f)

print("="*60)
print("🔐 SOLANA WALLET GENERATED")
print("="*60)
print(f"Public Key:  {public_key}")
print(f"Private Key: {private_key}")
print("="*60)
print("⚠️  SAVE THESE IMMEDIATELY")
print("Then run: rm gen_wallet.py bot-wallet.json")
print("="*60)
