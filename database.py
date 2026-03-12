"""Database module using direct Supabase HTTP API"""
import os
import requests
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Simple Supabase client using HTTP REST API"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _request(self, method: str, endpoint: str, data=None, params=None) -> Any:
        """Make HTTP request to Supabase"""
        url = f"{self.url}/rest/v1/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, params=params, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data, params=params, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Database request failed: {e}")
            raise
    
    def insert(self, table: str, data: Dict) -> Dict:
        """Insert data into table"""
        result = self._request("POST", table, data=data)
        return result[0] if isinstance(result, list) else result
    
    def select(self, table: str, columns: str = "*", filters: Optional[Dict] = None) -> List[Dict]:
        """Select data from table"""
        params = {"select": columns}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        return self._request("GET", table, params=params) or []
    
    def update(self, table: str, data: Dict, filters: Dict) -> List[Dict]:
        """Update data in table"""
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        return self._request("PATCH", table, data=data, params=params) or []
    
    def delete(self, table: str, filters: Dict) -> None:
        """Delete data from table"""
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        
        self._request("DELETE", table, params=params)

# Global client instance
db = SupabaseClient()

# Trade operations
def save_trade(trade_data: Dict) -> Dict:
    """Save a trade to database"""
    return db.insert("trades", trade_data)

def get_trades(limit: int = 100) -> List[Dict]:
    """Get recent trades"""
    return db.select("trades", columns="*")

def update_trade(trade_id: str, updates: Dict) -> List[Dict]:
    """Update a trade"""
    return db.update("trades", updates, {"id": trade_id})

# User operations  
def get_user(user_id: int) -> Optional[Dict]:
    """Get user by ID"""
    users = db.select("users", filters={"user_id": str(user_id)})
    return users[0] if users else None

def save_user(user_data: Dict) -> Dict:
    """Save or update user"""
    return db.insert("users", user_data)

# Whale alert operations
def save_whale_alert(alert_data: Dict) -> Dict:
    """Save whale alert"""
    return db.insert("whale_alerts", alert_data)

def get_recent_whale_alerts(limit: int = 50) -> List[Dict]:
    """Get recent whale alerts"""
    return db.select("whale_alerts", columns="*")
