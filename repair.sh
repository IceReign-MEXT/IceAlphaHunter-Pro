#!/bin/bash
echo "=========================================="
echo "  ICE ALPHA HUNTER PRO - REPAIR TOOL"
echo "=========================================="

# Step 1: Clean up corrupted packages
echo ""
echo "📦 STEP 1: Cleaning up corrupted packages..."
pip uninstall -y python-telegram-bot httpx httpcore supabase solana solders websockets aiohttp 2>/dev/null
pip install --upgrade pip

# Step 2: Install CORRECT versions in order
echo ""
echo "📦 STEP 2: Installing correct versions..."

# Base HTTP stack (must be first)
pip install --no-cache-dir httpcore==0.17.3 httpx==0.24.1

# Telegram (compatible with httpx 0.24.1)
pip install --no-cache-dir python-telegram-bot==20.4

# Database stack (compatible with httpx 0.24.1)
pip install --no-cache-dir \
    websockets==11.0.3 \
    aiohttp==3.9.1 \
    postgrest==0.15.0 \
    gotrue==2.1.0 \
    storage3==0.7.0 \
    supafunc==0.3.3 \
    realtime==1.0.2 \
    supabase==2.3.4

# Solana stack
pip install --no-cache-dir solana==0.30.2 solders==0.20.0 base58==2.1.1

# Utilities
pip install --no-cache-dir \
    python-dotenv==1.0.0 \
    requests==2.31.0 \
    pydantic==2.5.3 \
    cryptography==41.0.7 \
    PyJWT==2.8.0

echo ""
echo "✅ Packages installed"

# Step 3: Verify
echo ""
echo "🔍 STEP 3: Verifying..."
python3 -c "
import telegram
import httpx
import httpcore
import supabase
import solana.rpc.async_api
import solders.keypair
print('✅ All critical imports working')
"

# Step 4: Check .env
echo ""
echo "🔧 STEP 4: Environment check..."
if [ -f .env ]; then
    echo "✅ .env file exists"
    # Show what's missing
    for var in TELEGRAM_CHAT_ID HELIUS_RPC_URL WALLET_PRIVATE_KEY WALLET_ADDRESS; do
        if grep -q "^${var}=" .env 2>/dev/null; then
            echo "  ✅ $var set"
        else
            echo "  ❌ $var MISSING"
        fi
    done
else
    echo "❌ .env file not found!"
    echo "Create .env with:"
    echo "TELEGRAM_BOT_TOKEN=your_token"
    echo "TELEGRAM_CHAT_ID=your_chat_id"
    echo "HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key"
    echo "WALLET_PRIVATE_KEY=your_key"
    echo "WALLET_ADDRESS=your_address"
fi

echo ""
echo "=========================================="
echo "  REPAIR COMPLETE"
echo "=========================================="
