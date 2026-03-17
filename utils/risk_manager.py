"""
Risk Manager
Handles position sizing, stop losses, and risk limits
"""

from typing import Dict, List
from config import TRADING_CONFIG
from utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskManager:
    """
    Risk Management System
    
    Enforces:
    - Max position size
    - Max open positions
    - Stop losses
    - Daily loss limits
    """
    
    def __init__(self):
        self.max_position = TRADING_CONFIG.max_position_size
        self.max_positions = TRADING_CONFIG.max_open_positions
        self.stop_loss = TRADING_CONFIG.stop_loss_percent
        self.take_profit = TRADING_CONFIG.take_profit_percent
        self.daily_loss_limit = 1000.0  # $1000 max daily loss
        self.daily_pnl = 0.0
        
    def can_trade(self, open_positions: List[Dict]) -> bool:
        """Check if we can open a new position"""
        # Check position count
        if len(open_positions) >= self.max_positions:
            logger.debug(f"Max positions reached: {len(open_positions)}/{self.max_positions}")
            return False
        
        # Check daily loss limit
        if self.daily_pnl <= -self.daily_loss_limit:
            logger.warning(f"Daily loss limit hit: ${self.daily_pnl:.2f}")
            return False
        
        return True
    
    def calculate_position_size(self, available_balance: float, 
                               signal_confidence: float) -> float:
        """
        Calculate position size based on confidence and risk
        
        Args:
            available_balance: Current available balance
            signal_confidence: 0.0 to 1.0 confidence score
        
        Returns:
            Position size in dollars
        """
        # Base size: 10% of balance or max position, whichever is smaller
        base_size = min(available_balance * 0.1, self.max_position)
        
        # Scale by confidence (higher confidence = larger position)
        position_size = base_size * signal_confidence
        
        # Ensure minimum position size
        if position_size < 10.0:
            logger.warning(f"Position size ${position_size:.2f} too small, skipping")
            return 0.0
        
        return position_size
    
    def calculate_stop_loss(self, entry_price: float, side: str = "buy") -> float:
        """Calculate stop loss price"""
        if side == "buy":
            return entry_price * (1 - self.stop_loss / 100)
        else:
            return entry_price * (1 + self.stop_loss / 100)
    
    def calculate_take_profit(self, entry_price: float, side: str = "buy") -> float:
        """Calculate take profit price"""
        if side == "buy":
            return entry_price * (1 + self.take_profit / 100)
        else:
            return entry_price * (1 - self.take_profit / 100)
    
    def update_daily_pnl(self, pnl: float):
        """Update daily PnL tracking"""
        self.daily_pnl += pnl
        
    def reset_daily_stats(self):
        """Reset daily statistics (call at market open)"""
        self.daily_pnl = 0.0