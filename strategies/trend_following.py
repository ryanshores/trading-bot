"""
Trend Following Strategy
Uses Moving Average Crossover + RSI + MACD
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
    - BUY: MA Golden Cross + RSI < overbought + MACD bullish
    - SELL: MA Death Cross + MACD bearish OR RSI > overbought
    """

    def __init__(self, config):
        super().__init__(config)
        self.short_period = config.short_ma_period
        self.long_period = config.long_ma_period
        self.rsi_period = config.rsi_period
        self.rsi_overbought = config.rsi_overbought
        self.rsi_oversold = config.rsi_oversold

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate MA, RSI, and MACD indicators"""
        df = data.copy()

        # Moving Averages
        df["ma_short"] = df["close"].rolling(window=self.short_period).mean()
        df["ma_long"] = df["close"].rolling(window=self.long_period).mean()

        # RSI with division by zero protection
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = np.where(loss != 0, gain / loss, np.inf)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].replace([np.inf, -np.inf], np.nan)

        # MACD (bonus indicator)
        exp1 = df["close"].ewm(span=12).mean()
        exp2 = df["close"].ewm(span=26).mean()
        df["macd"] = exp1 - exp2
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        return df

    def generate_signal(self, data: pd.DataFrame) -> Optional[Dict]:
        """Generate trading signal based on indicators"""
        df = self.calculate_indicators(data)

        if len(df) < self.long_period:
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        if (
            pd.isna(latest["ma_short"])
            or pd.isna(latest["ma_long"])
            or pd.isna(latest["rsi"])
            or pd.isna(latest["macd"])
            or pd.isna(latest["macd_signal"])
        ):
            return None
        if pd.isna(prev["ma_short"]) or pd.isna(prev["ma_long"]):
            return None

        # Check for MA crossover
        short_above_long = latest["ma_short"] > latest["ma_long"]
        prev_short_above_long = prev["ma_short"] > prev["ma_long"]

        # Golden Cross (bullish)
        macd_bullish = latest["macd"] > latest["macd_signal"]
        macd_bearish = latest["macd"] < latest["macd_signal"]
        macd_crossover_bullish = macd_bullish and (prev["macd"] <= prev["macd_signal"])
        macd_crossover_bearish = macd_bearish and (prev["macd"] >= prev["macd_signal"])

        if (
            short_above_long
            and not prev_short_above_long
            and latest["rsi"] < self.rsi_overbought
            and macd_bullish
        ):
            confidence = max(
                0.0,
                min(
                    1.0,
                    (self.rsi_overbought - latest["rsi"]) / 40
                    + (0.2 if macd_crossover_bullish else 0.0),
                ),
            )
            return {
                "action": "buy",
                "confidence": confidence,
                "reason": f"MA Golden Cross + RSI {latest['rsi']:.1f} + MACD bullish",
                "metadata": {
                    "ma_short": latest["ma_short"],
                    "ma_long": latest["ma_long"],
                    "rsi": latest["rsi"],
                    "macd": latest["macd"],
                    "macd_signal": latest["macd_signal"],
                    "macd_histogram": latest["macd_histogram"],
                },
            }

        if not short_above_long and prev_short_above_long and macd_bearish:
            return {
                "action": "sell",
                "confidence": 0.8 + (0.2 if macd_crossover_bearish else 0.0),
                "reason": f"MA Death Cross + RSI {latest['rsi']:.1f} + MACD bearish",
                "metadata": {
                    "ma_short": latest["ma_short"],
                    "ma_long": latest["ma_long"],
                    "rsi": latest["rsi"],
                    "macd": latest["macd"],
                    "macd_signal": latest["macd_signal"],
                    "macd_histogram": latest["macd_histogram"],
                },
            }

        if latest["rsi"] > self.rsi_overbought:
            return {
                "action": "sell",
                "confidence": max(
                    0.0, min(1.0, (latest["rsi"] - self.rsi_overbought) / 30)
                ),
                "reason": f"RSI Overbought ({latest['rsi']:.1f})",
                "metadata": {
                    "rsi": latest["rsi"],
                    "macd": latest["macd"],
                    "macd_signal": latest["macd_signal"],
                },
            }

        return None
