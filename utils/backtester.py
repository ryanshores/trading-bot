"""
Backtesting Module
Test strategies on historical data before live trading
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from strategies.strategy_interface import StrategyInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)

class Backtester:
    """
    Simple backtesting engine
    
    Usage:
        backtester = Backtester(strategy, initial_balance=10000)
        results = backtester.run(historical_data)
    """
    
    def __init__(self, strategy: StrategyInterface, initial_balance: float = 10000.0):
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.trades: List[Dict] = []
        self.position = None
        
    def run(self, data: pd.DataFrame) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV data
        
        Returns:
            Backtest results dict
        """
        logger.info(f"🧪 Starting backtest with ${self.initial_balance:.2f}")
        
        for i in range(50, len(data)):  # Start after indicator warmup
            window = data.iloc[:i]
            current_price = window['close'].iloc[-1]
            
            # Get signal
            signal = self.strategy.generate_signal(window)
            
            if signal:
                if signal['action'] == 'buy' and not self.position:
                    self._open_position(current_price, signal)
                elif signal['action'] == 'sell' and self.position:
                    self._close_position(current_price, signal)
        
        # Close any open position at end
        if self.position:
            self._close_position(data['close'].iloc[-1], {'reason': 'end_of_data'})
        
        return self._generate_report()
    
    def _open_position(self, price: float, signal: Dict):
        """Open a position"""
        position_size = self.balance * 0.1  # Use 10% of balance
        self.balance -= position_size
        
        self.position = {
            'entry_price': price,
            'size': position_size,
            'signal': signal
        }
        
        logger.debug(f"📈 BACKTEST BUY: ${position_size:.2f} at ${price:.2f}")
    
    def _close_position(self, price: float, signal: Dict):
        """Close a position"""
        if not self.position:
            return
        
        pnl = (price - self.position['entry_price']) / self.position['entry_price'] * self.position['size']
        self.balance += self.position['size'] + pnl
        
        trade = {
            'entry': self.position['entry_price'],
            'exit': price,
            'pnl': pnl,
            'return_pct': (pnl / self.position['size']) * 100
        }
        self.trades.append(trade)
        
        emoji = "✅" if pnl > 0 else "❌"
        logger.debug(f"{emoji} BACKTEST SELL: PnL ${pnl:.2f}")
        
        self.position = None
    
    def _generate_report(self) -> Dict:
        """Generate backtest report"""
        if not self.trades:
            return {'error': 'No trades executed'}
        
        total_trades = len(self.trades)
        wins = sum(1 for t in self.trades if t['pnl'] > 0)
        losses = total_trades - wins
        
        total_pnl = self.balance - self.initial_balance
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        returns = [t['return_pct'] for t in self.trades]
        avg_return = np.mean(returns)
        max_return = max(returns)
        min_return = min(returns)
        
        report = {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_pnl': total_pnl,
            'total_return_pct': (total_pnl / self.initial_balance) * 100,
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'avg_return_pct': avg_return,
            'max_return_pct': max_return,
            'min_return_pct': min_return,
            'trades': self.trades
        }
        
        self._print_report(report)
        return report
    
    def _print_report(self, report: Dict):
        """Print formatted report"""
        logger.info("=" * 60)
        logger.info("📊 BACKTEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Initial Balance: ${report['initial_balance']:.2f}")
        logger.info(f"Final Balance:   ${report['final_balance']:.2f}")
        logger.info(f"Total PnL:       ${report['total_pnl']:.2f} ({report['total_return_pct']:.2f}%)")
        logger.info(f"Total Trades:    {report['total_trades']}")
        logger.info(f"Win Rate:        {report['win_rate']:.1f}%")
        logger.info(f"Avg Return:      {report['avg_return_pct']:.2f}%")
        logger.info(f"Max Return:      {report['max_return_pct']:.2f}%")
        logger.info(f"Min Return:      {report['min_return_pct']:.2f}%")
        logger.info("=" * 60)

if __name__ == "__main__":
    # Example usage
    from config import STRATEGY_CONFIG
    from strategies.trend_following import TrendFollowingStrategy
    
    # Create dummy data
    dates = pd.date_range(end=datetime.now(), periods=500, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(500).cumsum() + 50000,
        'high': np.random.randn(500).cumsum() + 50100,
        'low': np.random.randn(500).cumsum() + 49900,
        'close': np.random.randn(500).cumsum() + 50000,
        'volume': np.random.randint(100, 1000, 500)
    })
    
    strategy = TrendFollowingStrategy(STRATEGY_CONFIG)
    backtester = Backtester(strategy, initial_balance=10000.0)
    results = backtester.run(data)