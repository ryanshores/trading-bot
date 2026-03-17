"""
Discord Notification Module
Send trade alerts and status updates to Discord
"""

import aiohttp
from datetime import datetime
from typing import Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class DiscordNotifier:
    """
    Discord webhook notifier for trade alerts
    
    Setup:
    1. Create a Discord webhook in your server
    2. Add webhook URL to config.py
    3. Bot will send alerts automatically
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def _send_embed(self, title: str, description: str, color: int, fields: list = None):
        """Send Discord embed message"""
        if not self.enabled:
            return
        
        await self._ensure_session()
        
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Trading Bot"
            }
        }
        
        if fields:
            embed["fields"] = fields
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            async with self.session.post(self.webhook_url, json=payload) as resp:
                if resp.status == 204:
                    logger.debug(f"Discord notification sent: {title}")
                else:
                    logger.error(f"Discord error: {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
    
    async def notify_buy(self, symbol: str, price: float, size: float, confidence: float, reason: str):
        """Send buy notification"""
        fields = [
            {"name": "Symbol", "value": symbol, "inline": True},
            {"name": "Price", "value": f"${price:,.2f}", "inline": True},
            {"name": "Size", "value": f"${size:,.2f}", "inline": True},
            {"name": "Confidence", "value": f"{confidence:.1%}", "inline": True},
            {"name": "Reason", "value": reason, "inline": False}
        ]
        
        await self._send_embed(
            title="📈 BUY SIGNAL",
            description=f"Bot has opened a long position on {symbol}",
            color=0x00ff00,  # Green
            fields=fields
        )
    
    async def notify_sell(self, symbol: str, price: float, pnl: float, reason: str):
        """Send sell/close notification"""
        emoji = "✅" if pnl > 0 else "❌"
        color = 0x00ff00 if pnl > 0 else 0xff0000
        
        fields = [
            {"name": "Symbol", "value": symbol, "inline": True},
            {"name": "Exit Price", "value": f"${price:,.2f}", "inline": True},
            {"name": "PnL", "value": f"${pnl:,.2f}", "inline": True},
            {"name": "Reason", "value": reason, "inline": False}
        ]
        
        await self._send_embed(
            title=f"{emoji} POSITION CLOSED",
            description=f"Position closed on {symbol}",
            color=color,
            fields=fields
        )
    
    async def notify_error(self, error_message: str):
        """Send error notification"""
        await self._send_embed(
            title="⚠️ BOT ERROR",
            description=error_message,
            color=0xffa500  # Orange
        )
    
    async def notify_daily_summary(self, trades: int, wins: int, losses: int, pnl: float, balance: float):
        """Send daily performance summary"""
        win_rate = (wins / trades * 100) if trades > 0 else 0
        emoji = "🟢" if pnl > 0 else "🔴"
        
        fields = [
            {"name": "Total Trades", "value": str(trades), "inline": True},
            {"name": "Win Rate", "value": f"{win_rate:.1f}%", "inline": True},
            {"name": "Wins/Losses", "value": f"{wins}/{losses}", "inline": True},
            {"name": "Daily PnL", "value": f"${pnl:,.2f}", "inline": True},
            {"name": "Balance", "value": f"${balance:,.2f}", "inline": True}
        ]
        
        await self._send_embed(
            title=f"{emoji} DAILY SUMMARY",
            description="Trading performance for today",
            color=0x00ff00 if pnl > 0 else 0xff0000,
            fields=fields
        )
    
    async def notify_startup(self, symbol: str, strategy: str, balance: float):
        """Send startup notification"""
        fields = [
            {"name": "Symbol", "value": symbol, "inline": True},
            {"name": "Strategy", "value": strategy, "inline": True},
            {"name": "Balance", "value": f"${balance:,.2f}", "inline": True}
        ]
        
        await self._send_embed(
            title="🚀 BOT STARTED",
            description="Trading bot is now running",
            color=0x0099ff,  # Blue
            fields=fields
        )
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()

# Global notifier instance
_notifier: Optional[DiscordNotifier] = None

def get_notifier(webhook_url: Optional[str] = None) -> DiscordNotifier:
    """Get or create Discord notifier singleton"""
    global _notifier
    if _notifier is None:
        _notifier = DiscordNotifier(webhook_url)
    return _notifier