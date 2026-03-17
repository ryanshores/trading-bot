"""
Trading Bot Core Engine
Main orchestrator that connects exchange, strategy, and execution
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List
import pandas as pd

from config import (
    EXCHANGE_CONFIG,
    TRADING_CONFIG,
    STRATEGY_CONFIG,
    NOTIFICATION_CONFIG,
    validate_config,
)
from exchanges.exchange_interface import ExchangeInterface
from strategies.strategy_interface import StrategyInterface
from utils.logger import setup_logger
from utils.risk_manager import RiskManager
from utils.performance_tracker import PerformanceTracker
from utils.notifier import get_notifier

# Validate configuration before starting
validate_config()

logger = setup_logger(__name__)


class TradingBot:
    """
    Main trading bot class.

    Usage:
        bot = TradingBot()
        await bot.run()
    """

    def __init__(self):
        self.exchange: Optional[ExchangeInterface] = None
        self.strategy: Optional[StrategyInterface] = None
        self.risk_manager = RiskManager()
        self.performance = PerformanceTracker()
        self.notifier = get_notifier(NOTIFICATION_CONFIG.discord_webhook_url)
        self.running = False

        # Paper trading account
        self.paper_balance = 10000.0  # Start with $10k fake money
        self.open_positions: List[Dict] = []

    async def initialize(self):
        """Initialize exchange connection and strategy"""
        logger.info("🚀 Initializing Trading Bot...")

        # Load exchange (fill in exchange_interface.py)
        self.exchange = await self._load_exchange()

        # Load strategy (fill in strategies/ folder)
        self.strategy = await self._load_strategy()

        # Send startup notification
        if NOTIFICATION_CONFIG.discord_webhook_url:
            await self.notifier.notify_startup(
                TRADING_CONFIG.symbol, STRATEGY_CONFIG.strategy_name, self.paper_balance
            )

        logger.info(
            f"✅ Bot initialized: {TRADING_CONFIG.symbol} on {EXCHANGE_CONFIG.name}"
        )
        logger.info(f"💰 Paper Trading: ${self.paper_balance:.2f} starting balance")

    async def _load_exchange(self) -> ExchangeInterface:
        """Load exchange interface based on config"""
        if EXCHANGE_CONFIG.name == "binance":
            from exchanges.binance_client import BinanceClient

            return BinanceClient(EXCHANGE_CONFIG)
        elif EXCHANGE_CONFIG.name == "kraken":
            from exchanges.kraken_client import KrakenClient

            return KrakenClient(EXCHANGE_CONFIG)
        else:
            raise ValueError(
                f"Unknown exchange: {EXCHANGE_CONFIG.name}. "
                "Supported exchanges: binance, kraken"
            )

    async def _load_strategy(self) -> StrategyInterface:
        """STUB: Load trading strategy"""
        # TODO: Implement your strategy in strategies/
        if STRATEGY_CONFIG.strategy_name == "trend_following":
            from strategies.trend_following import TrendFollowingStrategy

            return TrendFollowingStrategy(STRATEGY_CONFIG)
        elif STRATEGY_CONFIG.strategy_name == "mean_reversion":
            from strategies.mean_reversion import MeanReversionStrategy

            return MeanReversionStrategy(STRATEGY_CONFIG)
        else:
            raise ValueError(f"Unknown strategy: {STRATEGY_CONFIG.strategy_name}")

    async def run(self):
        """Main trading loop"""
        await self.initialize()
        self.running = True

        logger.info("🤖 Bot is running! Press Ctrl+C to stop.")

        try:
            while self.running:
                # 1. Fetch latest market data
                market_data = await self.exchange.get_market_data(TRADING_CONFIG.symbol)

                # Check for empty data
                if market_data.empty:
                    logger.warning("Empty market data, skipping cycle")
                    await asyncio.sleep(self._get_sleep_interval())
                    continue

                # 2. Get strategy signal
                signal = self.strategy.generate_signal(market_data)

                # 3. Check risk management
                if signal and self.risk_manager.can_trade(self.open_positions):
                    # 4. Execute trade
                    await self._execute_trade(signal, market_data)

                # 5. Check existing positions (stop loss, take profit)
                await self._check_positions(market_data)

                # 6. Log performance
                self.performance.log_status(self.paper_balance, self.open_positions)

                # Wait for next candle
                await asyncio.sleep(self._get_sleep_interval())

        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
        finally:
            await self.shutdown()

    async def _execute_trade(self, signal: Dict, market_data: pd.DataFrame):
        """Execute a trade (paper or real)"""
        action = signal["action"]  # 'buy' or 'sell'
        price = market_data["close"].iloc[-1]

        if TRADING_CONFIG.paper_trading:
            # Paper trade
            if action == "buy":
                position_size = min(
                    TRADING_CONFIG.max_position_size, self.paper_balance * 0.1
                )
                # Skip if position size too small
                if position_size < 1.0:
                    logger.debug(f"Position size too small: ${position_size:.2f}")
                    return

                self.paper_balance -= position_size

                position = {
                    "id": len(self.open_positions),
                    "entry_price": price,
                    "size": position_size,
                    "stop_loss": price * (1 - TRADING_CONFIG.stop_loss_percent / 100),
                    "take_profit": price
                    * (1 + TRADING_CONFIG.take_profit_percent / 100),
                    "timestamp": datetime.now(),
                }
                self.open_positions.append(position)
                logger.info(f"📈 PAPER BUY: ${position_size:.2f} at ${price:.2f}")

                # Send Discord notification
                if NOTIFICATION_CONFIG.notify_on_buy:
                    await self.notifier.notify_buy(
                        TRADING_CONFIG.symbol,
                        price,
                        position_size,
                        signal.get("confidence", 0.5),
                        signal.get("reason", "Strategy signal"),
                    )

        else:
            # Real trade - IMPLEMENT HERE
            # TODO: Add real exchange order execution
            pass

    async def _check_positions(self, market_data: pd.DataFrame):
        """Check open positions for stop loss / take profit"""
        current_price = market_data["close"].iloc[-1]

        for position in self.open_positions[:]:
            # Check stop loss
            if current_price <= position["stop_loss"]:
                await self._close_position(position, current_price, "stop_loss")
            # Check take profit
            elif current_price >= position["take_profit"]:
                await self._close_position(position, current_price, "take_profit")

    async def _close_position(self, position: Dict, exit_price: float, reason: str):
        """Close a position"""
        pnl = (
            (exit_price - position["entry_price"])
            / position["entry_price"]
            * position["size"]
        )
        self.paper_balance += position["size"] + pnl
        self.open_positions.remove(position)

        emoji = "✅" if pnl > 0 else "❌"
        logger.info(
            f"{emoji} PAPER CLOSE ({reason}): PnL ${pnl:.2f} | Balance: ${self.paper_balance:.2f}"
        )
        await self.performance.record_trade(position, exit_price, pnl)
        self.risk_manager.update_daily_pnl(pnl)

        # Send Discord notification
        if NOTIFICATION_CONFIG.notify_on_sell:
            await self.notifier.notify_sell(
                TRADING_CONFIG.symbol, exit_price, pnl, reason
            )

    def _get_sleep_interval(self) -> int:
        """Get sleep time based on timeframe"""
        intervals = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }
        return intervals.get(TRADING_CONFIG.timeframe, 3600)

    async def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("🧹 Shutting down...")
        if self.exchange:
            await self.exchange.close()
        if self.notifier:
            await self.notifier.close()
        self.performance.print_summary()
        logger.info(f"💰 Final Balance: ${self.paper_balance:.2f}")


if __name__ == "__main__":
    bot = TradingBot()
    asyncio.run(bot.run())
