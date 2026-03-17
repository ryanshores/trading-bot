"""
Mean Reversion Strategy
Uses Bollinger Bands
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from strategies.strategy_interface import StrategyInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MeanReversionStrategy(StrategyInterface):
    """
    Mean Reversion Strategy using Bollinger Bands
    
    Rules:
    - BUY: Price touches lower band (oversold)
    - SELL: Price touches upper band (overbought)
    
    Assumes prices revert to mean over time
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.period = config.bollinger_period
        self.std_dev = config.bollinger_std
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        df = data.copy()
        
        # Middle Band (SMA)
        df['bb_middle'] = df['close'].rolling(window=self.period).mean()
        
        # Standard Deviation
        df['bb_std'] = df['close'].rolling(window=self.period).std()
        
        # Upper and Lower Bands
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * self.std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * self.std_dev)
        
        # %B indicator (where price is relative to bands)
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Bandwidth (volatility indicator)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """Generate signal based on Bollinger Bands"""
        df = self.calculate_indicators(data)
        
        if len(df) < self.period:
            return None
        
        latest = df.iloc[-1]
        
        # Price below lower band (oversold) - BUY
        if latest['close'] < latest['bb_lower']:
            return {
                'action': 'buy',
                'confidence': min(1.0, (latest['bb_lower'] - latest['close']) / latest['bb_std']),
                'reason': f"Price below lower Bollinger Band ({latest['bb_percent']:.2%})",
                'metadata': {
                    'bb_lower': latest['bb_lower'],
                    'bb_middle': latest['bb_middle'],
                    'bb_upper': latest['bb_upper'],
                    'bb_percent': latest['bb_percent']
                }
            }
        
        # Price above upper band (overbought) - SELL
        if latest['close'] > latest['bb_upper']:
            return {
                'action': 'sell',
                'confidence': min(1.0, (latest['close'] - latest['bb_upper']) / latest['bb_std']),
                'reason': f"Price above upper Bollinger Band ({latest['bb_percent']:.2%})",
                'metadata': {
                    'bb_lower': latest['bb_lower'],
                    'bb_middle': latest['bb_middle'],
                    'bb_upper': latest['bb_upper'],
                    'bb_percent': latest['bb_percent']
                }
            }
        
        return None