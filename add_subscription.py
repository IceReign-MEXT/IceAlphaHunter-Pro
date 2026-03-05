# Add to main.py - Subscription tiers

SUBSCRIPTION_TIERS = {
    "free": {
        "max_trade": 1,  # SOL per trade
        "daily_limit": 3,  # trades per day
        "fee_percent": 1.0,  # 1% fee
        "features": ["basic_snipe"]
    },
    "pro": {
        "price_sol": 0.5,  # 0.5 SOL/month
        "max_trade": 5,
        "daily_limit": 20,
        "fee_percent": 0.5,  # 0.5% fee
        "features": ["mev_boost", "auto_tp_sl", "priority_support"]
    },
    "whale": {
        "price_sol": 2.0,  # 2 SOL/month
        "max_trade": 50,
        "daily_limit": 100,
        "fee_percent": 0.25,  # 0.25% fee
        "features": ["mev_boost", "auto_tp_sl", "copy_trading", "insider_alerts"]
    }
}
