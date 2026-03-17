"""
Performance Tracker
Logs and analyzes trading performance
"""

import json
import aiofiles
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)


class PerformanceTracker:
    """
    Track trading performance metrics

    Metrics:
    - Total PnL
    - Win rate
    - Average win/loss
    - Sharpe ratio (simplified)
    - Max drawdown
    """

    def __init__(self, log_file: str = "trades.json"):
        self.log_file = Path(log_file)
        self.trades: List[Dict] = []
        self.daily_stats = {"trades": 0, "wins": 0, "losses": 0, "total_pnl": 0.0}

    async def record_trade(self, position: Dict, exit_price: float, pnl: float):
        """Record a completed trade"""
        trade = {
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "size": position["size"],
            "pnl": pnl,
            "timestamp": datetime.now().isoformat(),
            "duration": str(datetime.now() - position["timestamp"]),
        }
        self.trades.append(trade)

        # Update stats
        self.daily_stats["trades"] += 1
        self.daily_stats["total_pnl"] += pnl
        if pnl > 0:
            self.daily_stats["wins"] += 1
        else:
            self.daily_stats["losses"] += 1

        # Save to file
        await self._save_trade(trade)

    def log_status(self, balance: float, open_positions: List[Dict]):
        """Log current status"""
        unrealized_pnl = sum(
            pos.get("size", 0) * 0.01  # Placeholder
            for pos in open_positions
        )

        logger.info(
            f"📊 Status: Balance ${balance:.2f} | "
            f"Open: {len(open_positions)} | "
            f"Today's PnL: ${self.daily_stats['total_pnl']:.2f}"
        )

    def print_summary(self):
        """Print performance summary"""
        if not self.trades:
            logger.info("No trades recorded yet")
            return

        total_trades = len(self.trades)
        wins = sum(1 for t in self.trades if t["pnl"] > 0)
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        total_pnl = sum(t["pnl"] for t in self.trades)
        avg_win = (
            sum(t["pnl"] for t in self.trades if t["pnl"] > 0) / wins if wins > 0 else 0
        )
        avg_loss = (
            sum(t["pnl"] for t in self.trades if t["pnl"] < 0) / losses
            if losses > 0
            else 0
        )

        logger.info("=" * 50)
        logger.info("📈 PERFORMANCE SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Win Rate: {win_rate:.1f}% ({wins}W / {losses}L)")
        logger.info(f"Total PnL: ${total_pnl:.2f}")
        logger.info(f"Avg Win: ${avg_win:.2f}")
        logger.info(f"Avg Loss: ${avg_loss:.2f}")
        logger.info("=" * 50)

    async def _save_trade(self, trade: Dict):
        """Append trade to log file"""
        mode = "a" if self.log_file.exists() else "w"
        async with aiofiles.open(self.log_file, mode) as f:
            await f.write(json.dumps(trade) + "\n")
