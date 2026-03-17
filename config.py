# Trading Bot Configuration
# Configuration can be set via config.py OR environment variables
# Environment variables take precedence over defaults here

import os
from dataclasses import dataclass
from typing import Optional


def get_env(key: str, default: str = "") -> str:
    """Get environment variable with default"""
    return os.environ.get(key, default)


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable"""
    val = os.environ.get(key, "").lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float environment variable"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable"""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass
class ExchangeConfig:
    """Exchange API configuration"""

    # Environment: EXCHANGE_NAME (binance, kraken)
    name: str = get_env("EXCHANGE_NAME", "binance")
    # Environment: EXCHANGE_API_KEY
    api_key: str = get_env("EXCHANGE_API_KEY", "")
    # Environment: EXCHANGE_API_SECRET
    api_secret: str = get_env("EXCHANGE_API_SECRET", "")
    # Environment: EXCHANGE_TESTNET (true/false)
    testnet: bool = get_env_bool("EXCHANGE_TESTNET", True)


@dataclass
class TradingConfig:
    """Trading parameters"""

    # Environment: TRADING_SYMBOL
    symbol: str = get_env("TRADING_SYMBOL", "BTCUSDT")
    # Environment: TRADING_TIMEFRAME (1m, 5m, 15m, 1h, 4h, 1d)
    timeframe: str = get_env("TRADING_TIMEFRAME", "1h")
    # Environment: PAPER_TRADING (true/false)
    paper_trading: bool = get_env_bool("PAPER_TRADING", True)

    # Risk Management
    # Environment: MAX_POSITION_SIZE
    max_position_size: float = get_env_float("MAX_POSITION_SIZE", 100.0)
    # Environment: STOP_LOSS_PERCENT
    stop_loss_percent: float = get_env_float("STOP_LOSS_PERCENT", 2.0)
    # Environment: TAKE_PROFIT_PERCENT
    take_profit_percent: float = get_env_float("TAKE_PROFIT_PERCENT", 4.0)
    # Environment: MAX_OPEN_POSITIONS
    max_open_positions: int = get_env_int("MAX_OPEN_POSITIONS", 3)
    # Environment: DAILY_LOSS_LIMIT
    daily_loss_limit: float = get_env_float("DAILY_LOSS_LIMIT", 1000.0)


@dataclass
class StrategyConfig:
    """Strategy-specific settings"""

    # Environment: STRATEGY_NAME (trend_following, mean_reversion)
    strategy_name: str = get_env("STRATEGY_NAME", "trend_following")

    # Trend Following Parameters
    # Environment: STRATEGY_SHORT_MA
    short_ma_period: int = get_env_int("STRATEGY_SHORT_MA", 20)
    # Environment: STRATEGY_LONG_MA
    long_ma_period: int = get_env_int("STRATEGY_LONG_MA", 50)
    # Environment: STRATEGY_RSI_PERIOD
    rsi_period: int = get_env_int("STRATEGY_RSI_PERIOD", 14)
    # Environment: STRATEGY_RSI_OVERBOUGHT
    rsi_overbought: float = get_env_float("STRATEGY_RSI_OVERBOUGHT", 70.0)
    # Environment: STRATEGY_RSI_OVERSOLD
    rsi_oversold: float = get_env_float("STRATEGY_RSI_OVERSOLD", 30.0)

    # Mean Reversion Parameters
    # Environment: STRATEGY_BB_PERIOD
    bollinger_period: int = get_env_int("STRATEGY_BB_PERIOD", 20)
    # Environment: STRATEGY_BB_STD
    bollinger_std: float = get_env_float("STRATEGY_BB_STD", 2.0)


@dataclass
class NotificationConfig:
    """Discord notification settings"""

    # Environment: DISCORD_WEBHOOK_URL
    discord_webhook_url: str = get_env("DISCORD_WEBHOOK_URL", "")
    # Environment: NOTIFY_ON_BUY (true/false)
    notify_on_buy: bool = get_env_bool("NOTIFY_ON_BUY", True)
    # Environment: NOTIFY_ON_SELL (true/false)
    notify_on_sell: bool = get_env_bool("NOTIFY_ON_SELL", True)
    # Environment: NOTIFY_ON_ERROR (true/false)
    notify_on_error: bool = get_env_bool("NOTIFY_ON_ERROR", True)
    # Environment: DAILY_SUMMARY (true/false)
    daily_summary: bool = get_env_bool("DAILY_SUMMARY", True)
    # Environment: SUMMARY_TIME (HH:MM)
    summary_time: str = get_env("SUMMARY_TIME", "20:00")


# Global config instance
EXCHANGE_CONFIG = ExchangeConfig()
TRADING_CONFIG = TradingConfig()
STRATEGY_CONFIG = StrategyConfig()
NOTIFICATION_CONFIG = NotificationConfig()


def validate_config() -> bool:
    """Validate configuration before starting bot"""
    if not TRADING_CONFIG.paper_trading:
        if not EXCHANGE_CONFIG.api_key or not EXCHANGE_CONFIG.api_secret:
            raise ValueError(
                "API key and secret are required when paper_trading=False. "
                "Set them via EXCHANGE_API_KEY and EXCHANGE_API_SECRET environment "
                "variables or in config.py"
            )

    if TRADING_CONFIG.max_position_size <= 0:
        raise ValueError("max_position_size must be positive")

    if TRADING_CONFIG.stop_loss_percent <= 0 or TRADING_CONFIG.stop_loss_percent >= 100:
        raise ValueError("stop_loss_percent must be between 0 and 100")

    if TRADING_CONFIG.take_profit_percent <= 0:
        raise ValueError("take_profit_percent must be positive")

    if TRADING_CONFIG.daily_loss_limit <= 0:
        raise ValueError("daily_loss_limit must be positive")

    return True
