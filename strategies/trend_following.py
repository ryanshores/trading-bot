"""
Trend Following Strategy
Uses Moving Average Crossover + RSI
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

from strategies.strategy_interface import StrategyInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)

class TrendFollowingStrategy(StrategyInterface):
    """
    Trend Following Strategy
    
    Rules:
    - BUY: Short MA crosses above Long MA AND RSI < 70
    - SELL: Short MA crosses below Long MA OR RSI > 70
    
    TODO: Adjust parameters in config.py
    """
    
    def __init__(self, config):
        super().__init__(config)
        self.short_period = config.short_ma_period
        self.long_period = config.long_ma_period
        self.rsi_period = config.rsi_period
        self.rsi_overbought = config.rsi_overbought
        self.rsi_oversold = config.rsi_oversold
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate MA and RSI indicators"""
        df = data.copy()
        
        # Moving Averages
        df['ma_short'] = df['close'].rolling(window=self.short_period).mean()
        df['ma_long'] = df['close'].rolling(window=self.long_period).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD (bonus indicator)
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        return df
    
    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal based on indicators"""
        df = self.calculate_indicators(data)
        
        if len(df) < self.long_period:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Check for MA crossover
        short_above_long = latest['ma_short'] > latest['ma_long']
        prev_short_above_long = prev['ma_short'] > prev['ma_long']
        
        # Golden Cross (bullish)
        if short_above_long and not prev_short_above_long and latest['rsi'] < self.rsi_overbought:
            return {
                'action': 'buy',
                'confidence': min(1.0, (self.rsi_overbought - latest['rsi']) / 40),
                'reason': f"MA Crossover (Golden Cross) + RSI {latest['rsi']:.1f}",
                'metadata': {
                    'ma_short': latest['ma_short'],
                    'ma_long': latest['ma_long'],
                    'rsi': latest['rsi']
                }
            }
        
        # Death Cross (bearish)
        if not short_above_long and prev_short_above_long:
            return {
                'action': 'sell',
                'confidence': 0.8,
                'reason': f"MA Crossover (Death Cross) + RSI {latest['rsi']:.1f}",
                'metadata': {
                    'ma_short': latest['ma_short'],
                    'ma_long': latest['ma_long'],
                    'rsi': latest['rsi']
                }
            }
        
        # RSI Overbought
        if latest['rsi'] > self.rsi_overbought:
            return {
                'action': 'sell',
                'confidence': (latest['rsi'] - self.rsi_overbought) / 30,
                'reason': f"RSI Overbought ({latest['rsi']:.1f})",
                'metadata': {'rsi': latest['rsi']}
            }
        
        return None