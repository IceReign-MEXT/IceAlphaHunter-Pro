"""Subscription & Fee Management"""
import os
from datetime import datetime, timedelta
from typing import Dict
import logging
from database import db

logger = logging.getLogger(__name__)

TIERS = {
    'free': {'name': 'Free', 'price': 0, 'alerts': False, 'auto': False, 'max': 0},
    'basic': {'name': 'Basic', 'price': 0.5, 'alerts': True, 'auto': False, 'max': 5},
    'pro': {'name': 'Pro', 'price': 1.5, 'alerts': True, 'auto': True, 'max': 20},
    'whale': {'name': 'Whale', 'price': 5.0, 'alerts': True, 'auto': True, 'max': 100}
}

FEE = 0.02  # 2% fee

class SubscriptionManager:
    def get_user_sub(self, user_id: int) -> Dict:
        user = db.get_user(user_id)
        if not user:
            return {'tier': 'free', 'active': True}
        expires = user.get('subscription_expires')
        active = expires > datetime.now() if expires else user.get('subscription_type', 'free') == 'free'
        return {'tier': user.get('subscription_type', 'free'), 'active': active}
    
    def can_use(self, user_id: int, feature: str) -> bool:
        sub = self.get_user_sub(user_id)
        tier = TIERS.get(sub['tier'], TIERS['free'])
        return tier.get(feature, False)
    
    def calc_fee(self, profit: float) -> float:
        return profit * FEE if profit > 0 else 0
    
    def get_text(self, user_id: int) -> str:
        sub = self.get_user_sub(user_id)
        tier = TIERS[sub['tier']]
        txt = f"<b>💎 {tier['name']} Plan</b>\n"
        txt += f"Status: {'✅ Active' if sub['active'] else '❌ Expired'}\n"
        txt += f"{'✅' if tier['alerts'] else '❌'} Whale Alerts\n"
        txt += f"{'✅' if tier['auto'] else '❌'} Auto-Trading\n"
        txt += f"📊 {tier['max']} trades/day\n"
        txt += f"\n💰 2% fee on profits"
        return txt

subscription_manager = SubscriptionManager()
