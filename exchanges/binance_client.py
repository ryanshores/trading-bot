"""
Binance Exchange Client
Full WebSocket and REST API implementation
"""

import asyncio
import aiohttp
import pandas as pd
import hmac
import hashlib
import time
from typing import Dict, List, Optional
from datetime import datetime
import websockets
import json

from exchanges.exchange_interface import ExchangeInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)

class BinanceClient(ExchangeInterface):
    """
    Full Binance exchange implementation
    - REST API for orders and account data
    - WebSocket for real-time market data
    - Automatic reconnection
    """
    
    def __init__(self, config):
        super().__init__(config)
        # Use testnet for paper trading
        self.base_url = "https://testnet.binance.vision" if config.testnet else "https://api.binance.com"
        self.ws_url = "wss://testnet.binance.vision/ws" if config.testnet else "wss://stream.binance.com:9443/ws"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
        self.ws_task = None
        self.price_data = {}
        
    async def connect(self):
        """Connect to Binance REST API"""
        self.session = aiohttp.ClientSession()
        
        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/api/v3/ping") as resp:
                if resp.status == 200:
                    self.connected = True
                    logger.info(f"🔗 Connected to Binance ({'testnet' if self.config.testnet else 'live'})")
                else:
                    logger.error(f"Failed to connect: {resp.status}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC signature for authenticated requests"""
        return hmac.new(
            self.config.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make authenticated or unauthenticated request"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if signed and self.config.api_key:
            # Add timestamp and signature
            params = params or {}
            params['timestamp'] = int(time.time() * 1000)
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            params['signature'] = self._generate_signature(query_string)
            headers['X-MBX-APIKEY'] = self.config.api_key
        
        try:
            if method == "GET":
                async with self.session.get(url, params=params, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"API Error: {data}")
                        return {}
                    return data
            elif method == "POST":
                async with self.session.post(url, data=params, headers=headers) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"API Error: {data}")
                        return {}
                    return data
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {}
        
    async def get_market_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """
        Fetch candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Candlestick interval (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch (max 1000)
        """
        await self.connect()
        
        endpoint = "/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        data = await self._make_request("GET", endpoint, params)
        
        if not data:
            logger.error("Failed to fetch market data")
            return pd.DataFrame()
        
        return self._parse_klines(data)
    
    def _parse_klines(self, data: List) -> pd.DataFrame:
        """Parse Binance kline data to DataFrame"""
        # Binance returns: [
        #   [timestamp, open, high, low, close, volume, close_time, ...]
        # ]
        df_data = []
        for kline in data:
            df_data.append({
                'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        df = pd.DataFrame(df_data)
        return df
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balances (requires API key)"""
        if not self.config.api_key:
            logger.warning("No API key provided, returning dummy balance")
            return {"USDT": 10000.0, "BTC": 0.0}
        
        endpoint = "/api/v3/account"
        data = await self._make_request("GET", endpoint, signed=True)
        
        if not data or 'balances' not in data:
            logger.error("Failed to fetch account balance")
            return {}
        
        balances = {}
        for asset in data['balances']:
            free = float(asset['free'])
            locked = float(asset['locked'])
            if free > 0 or locked > 0:
                balances[asset['asset']] = free + locked
        
        return balances
    
    async def place_order(self, symbol: str, side: str, quantity: float, 
                         order_type: str = "market", price: float = None) -> Dict:
        """
        Place an order (requires API key)
        
        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            quantity: Amount to trade
            order_type: "MARKET" or "LIMIT"
            price: Limit price (required for LIMIT orders)
        """
        if not self.config.api_key:
            logger.warning("No API key - simulating order")
            return {
                "orderId": f"SIM_{int(time.time())}",
                "status": "FILLED",
                "symbol": symbol,
                "side": side,
                "executedQty": quantity,
                "simulated": True
            }
        
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity
        }
        
        if order_type.upper() == "LIMIT" and price:
            params["price"] = price
            params["timeInForce"] = "GTC"  # Good Till Canceled
        
        data = await self._make_request("POST", endpoint, params, signed=True)
        
        if data:
            logger.info(f"✅ Order placed: {side.upper()} {quantity} {symbol} @ {data.get('price', 'MARKET')}")
            return data
        else:
            logger.error("Failed to place order")
            return {}
    
    async def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """Check order status"""
        if not self.config.api_key:
            return {"orderId": order_id, "status": "FILLED", "simulated": True}
        
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        
        return await self._make_request("GET", endpoint, params, signed=True)
    
    async def start_websocket(self, symbols: List[str]):
        """Start WebSocket connection for real-time price data"""
        streams = '/'.join([f"{s.lower()}@ticker" for s in symbols])
        ws_url = f"{self.ws_url}/{streams}"
        
        self.ws_task = asyncio.create_task(self._websocket_handler(ws_url))
        logger.info(f"📡 WebSocket started for {symbols}")
    
    async def _websocket_handler(self, ws_url: str):
        """Handle WebSocket connection with auto-reconnect"""
        while self.connected:
            try:
                async with websockets.connect(ws_url) as ws:
                    self.ws_connection = ws
                    async for message in ws:
                        data = json.loads(message)
                        self._process_ws_message(data)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket disconnected, reconnecting...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)
    
    def _process_ws_message(self, data: Dict):
        """Process incoming WebSocket message"""
        if 's' in data:  # Symbol
            symbol = data['s']
            self.price_data[symbol] = {
                'price': float(data.get('c', 0)),  # Current price
                'change_24h': float(data.get('P', 0)),  # 24h change %
                'volume': float(data.get('v', 0)),  # Volume
                'timestamp': datetime.now()
            }
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get latest price from WebSocket"""
        if symbol in self.price_data:
            return self.price_data[symbol]['price']
        return None
    
    async def close(self):
        """Close all connections"""
        self.connected = False
        
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_connection:
            await self.ws_connection.close()
        
        if self.session:
            await self.session.close()
        
        logger.info("🔌 Disconnected from Binance")