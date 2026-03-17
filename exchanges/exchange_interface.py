"""
Exchange Interface
Abstract base class for exchange implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd

class ExchangeInterface(ABC):
    """Abstract interface for exchange connections"""
    
    def __init__(self, config):
        self.config = config
        self.connected = False
    
    @abstractmethod
    async def connect(self):
        """Connect to exchange WebSocket/API"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetch OHLCV data for symbol
        
        Returns DataFrame with columns:
        - timestamp, open, high, low, close, volume
        """
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balances"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, quantity: float, 
                         order_type: str = "market") -> Dict:
        """
        Place an order
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "buy" or "sell"
            quantity: Amount to trade
            order_type: "market" or "limit"
        
        Returns:
            Order details dict
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict:
        """Check order status"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close connection"""
        pass