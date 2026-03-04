#!/bin/bash
set -e

echo "🚀 Installing dependencies..."

# Upgrade pip first
pip install --upgrade pip

# Install with no deps first, then resolve
pip install python-telegram-bot==20.7 --no-deps
pip install python-dotenv==1.0.0 --no-deps
pip install requests==2.31.0 --no-deps
pip install solathon==1.0.0 --no-deps
pip install aiohttp==3.9.1 --no-deps
pip install websockets==12.0 --no-deps
pip install cryptography==41.0.7 --no-deps

# Now install all remaining deps
pip install -r requirements.txt --no-cache-dir

echo "✅ Build complete!"
