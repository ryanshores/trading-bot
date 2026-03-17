# Trading Bot Configuration
# Fill in your API keys and settings here

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExchangeConfig:
    """Exchange API configuration"""

    name: str = "kraken"  # or "coinbase", "kraken", "binance
    api_key: str = ""  # FILL IN: Your API key
    api_secret: str = ""  # FILL IN: Your API secret
    # testnet: bool = True  # Use testnet for paper trading
    testnet: bool = False


@dataclass
class TradingConfig:
    """Trading parameters"""

    symbol: str = "BTCUSDT"  # Trading pair
    timeframe: str = "1m"  # Candlestick timeframe (1m, 5m, 15m, 1h, 4h, 1d)
    paper_trading: bool = True  # True = fake money, False = real trades

    # Risk Management - ADJUST THESE
    max_position_size: float = 100.0  # Max $ to allocate per trade
    stop_loss_percent: float = 2.0  # Stop loss at -2%
    take_profit_percent: float = 4.0  # Take profit at +4%
    max_open_positions: int = 3  # Max concurrent trades
    daily_loss_limit: float = 1000.0  # Max daily loss before stopping


@dataclass
class StrategyConfig:
    """Strategy-specific settings"""

    strategy_name: str = "trend_following"  # See strategies/ folder

    # Trend Following Parameters
    short_ma_period: int = 20  # Short moving average
    long_ma_period: int = 50  # Long moving average
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    # Mean Reversion Parameters
    bollinger_period: int = 20
    bollinger_std: float = 2.0


@dataclass
class NotificationConfig:
    """Discord notification settings"""

    # Get webhook URL from Discord:
    # Server Settings -> Integrations -> Webhooks -> New Webhook
    discord_webhook_url: str = ""  # FILL IN: Your Discord webhook URL
    notify_on_buy: bool = True
    notify_on_sell: bool = True
    notify_on_error: bool = True
    daily_summary: bool = True
    summary_time: str = "20:00"  # Send summary at 8 PM


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
                "Set them in config.py or enable paper_trading=True."
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
