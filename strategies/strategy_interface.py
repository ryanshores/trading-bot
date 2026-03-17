"""
Strategy Interface
Abstract base class for trading strategies
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd

class StrategyInterface(ABC):
    """Abstract interface for trading strategies"""
    
    def __init__(self, config):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """
        Analyze market data and generate trading signal
        
        Args:
            data: DataFrame with OHLCV data
        
        Returns:
            Signal dict or None:
            {
                'action': 'buy' or 'sell',
                'confidence': 0.0 to 1.0,
                'reason': 'description of signal',
                'metadata': {...}
            }
        """
        pass
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate strategy-specific indicators"""
        pass