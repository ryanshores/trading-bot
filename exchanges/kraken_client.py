"""
Kraken Exchange Client
Full WebSocket and REST API implementation
"""

import asyncio
import aiohttp
import pandas as pd
import hmac
import hashlib
import base64
import time
import urllib.parse
from typing import Dict, List, Optional
from datetime import datetime
import websockets
import json

from exchanges.exchange_interface import ExchangeInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)


class KrakenClient(ExchangeInterface):
    """
    Full Kraken exchange implementation
    - REST API for orders and account data
    - WebSocket for real-time market data
    - Automatic reconnection
    """

    def __init__(self, config):
        super().__init__(config)
        self.base_url = "https://api.kraken.com"
        self.ws_url = "wss://ws.kraken.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws_connection = None
        self.ws_task = None
        self.price_data = {}

        self._nonce_counter = int(time.time() * 1000)

    async def connect(self):
        """Connect to Kraken REST API"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(timeout=timeout)

        # Test connection
        try:
            async with self.session.get(f"{self.base_url}/0/public/Time") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("error") and len(data["error"]) > 0:
                        logger.error(f"Kraken API error: {data['error']}")
                        raise Exception(f"Kraken connection failed: {data['error']}")
                    self.connected = True
                    logger.info("🔗 Connected to Kraken")
                else:
                    logger.error(f"Failed to connect: {resp.status}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def _get_nonce(self) -> int:
        """Generate unique nonce for Kraken API"""
        self._nonce_counter += 1
        return self._nonce_counter

    def _generate_signature(self, endpoint: str, data: Dict, nonce: int) -> str:
        """Generate HMAC-SHA512 signature for authenticated requests"""
        # Kraken signature: HMAC-SHA512 of (nonce + postdata) with SHA256(endpoint) as key
        post_data = urllib.parse.urlencode(data)

        # SHA256 of nonce + postdata
        sha256 = hashlib.sha256()
        sha256.update((str(nonce) + post_data).encode("utf-8"))

        # HMAC-SHA512 with base64 decoded secret
        hmac_sha512 = hmac.new(
            base64.b64decode(self.config.api_secret),
            sha256.digest() + endpoint.encode("utf-8"),
            hashlib.sha512,
        )

        return base64.b64encode(hmac_sha512.digest()).decode("utf-8")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        signed: bool = False,
    ) -> Dict:
        """Make authenticated or unauthenticated request"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        data = {}

        if signed and self.config.api_key:
            nonce = self._get_nonce()
            params = params or {}
            params["nonce"] = nonce

            signature = self._generate_signature(endpoint, params, nonce)
            headers["API-Key"] = self.config.api_key
            headers["API-Sign"] = signature
            data = params

        try:
            if method == "GET":
                async with self.session.get(url, params=params) as resp:
                    result = await resp.json()
                    if result.get("error") and len(result["error"]) > 0:
                        logger.error(f"Kraken API Error: {result['error']}")
                        return {}
                    return result.get("result", {})
            elif method == "POST":
                async with self.session.post(url, data=data, headers=headers) as resp:
                    result = await resp.json()
                    if result.get("error") and len(result["error"]) > 0:
                        logger.error(f"Kraken API Error: {result['error']}")
                        return {}
                    return result.get("result", {})
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {}

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize trading pair symbol for Kraken

        Kraken uses different symbols:
        - BTC/USD -> XXBTZUSD
        - ETH/USD -> XETHZUSD

        Common mappings:
        - BTC -> XXBT
        - USD -> ZUSD
        """
        symbol_map = {
            "BTCUSDT": "XXBTZUSD",
            "ETHUSDT": "XETHZUSD",
            "BTCUSD": "XXBTZUSD",
            "ETHUSD": "XETHZUSD",
            "XRPUSD": "XXRPZUSD",
            "LTCUSD": "XLTCZUSD",
        }

        return symbol_map.get(symbol.upper(), symbol.upper())

    def _denormalize_symbol(self, kraken_symbol: str) -> str:
        """
        Convert Kraken symbol back to standard format
        """
        reverse_map = {
            "XXBTZUSD": "BTCUSD",
            "XETHZUSD": "ETHUSD",
            "XXRPZUSD": "XRPUSD",
            "XLTCZUSD": "LTCUSD",
        }
        return reverse_map.get(kraken_symbol, kraken_symbol)

    async def get_market_data(
        self, symbol: str, interval: int = 60, limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch OHLC data from Kraken

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Candle interval in minutes (1, 5, 15, 30, 60, 240, 1440)
            limit: Number of candles to fetch
        """
        await self.connect()

        kraken_symbol = self._normalize_symbol(symbol)

        # Kraken interval mapping (in minutes)
        kraken_intervals = {1: 1, 5: 5, 15: 15, 30: 30, 60: 60, 240: 240, 1440: 1440}
        kraken_interval = kraken_intervals.get(interval, 60)

        endpoint = "/0/public/OHLC"
        since = int(time.time()) - (kraken_interval * 60 * limit)
        params = {
            "pair": kraken_symbol,
            "interval": kraken_interval,
            "since": since,
        }

        data = await self._make_request("GET", endpoint, params)

        if not data:
            logger.error("Failed to fetch market data")
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        return self._parse_ohlc(data, kraken_symbol)

    def _parse_ohlc(self, data: Dict, symbol: str) -> pd.DataFrame:
        """Parse Kraken OHLC data to DataFrame"""
        # Kraken returns: {"XXBTZUSD": [[time, etime, open, high, low, close, vwap, volume, count], ...]}
        df_data = []

        ohlc_data = data.get(symbol, [])
        if not ohlc_data:
            # Try to find the key dynamically
            for key in data:
                if isinstance(data[key], list):
                    ohlc_data = data[key]
                    break

        for candle in ohlc_data[-100:]:  # Last 100 candles
            try:
                df_data.append(
                    {
                        "timestamp": datetime.fromtimestamp(float(candle[0])),
                        "open": float(candle[2]),
                        "high": float(candle[3]),
                        "low": float(candle[4]),
                        "close": float(candle[5]),
                        "volume": float(candle[7]),
                    }
                )
            except (IndexError, ValueError) as e:
                logger.warning(f"Error parsing candle: {e}")
                continue

        df = pd.DataFrame(df_data)
        return df

    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balances (requires API key)"""
        if not self.config.api_key:
            logger.warning("No API key provided, returning dummy balance")
            return {"USD": 10000.0, "BTC": 0.0}

        endpoint = "/0/private/Balance"
        data = await self._make_request("POST", endpoint, signed=True)

        if not data:
            logger.error("Failed to fetch account balance")
            return {}

        balances = {}
        for asset, amount in data.items():
            # Kraken asset names: XXBT, ZUSD, etc.
            free = float(amount)
            if free > 0:
                # Normalize asset names
                if asset == "XXBT":
                    asset = "BTC"
                elif asset == "ZUSD":
                    asset = "USD"
                elif asset == "XETH":
                    asset = "ETH"
                balances[asset] = free

        return balances

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float = None,
    ) -> Dict:
        """
        Place an order (requires API key)

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "buy" or "sell"
            quantity: Amount to trade
            order_type: "market" or "limit"
            price: Limit price (required for LIMIT orders)
        """
        if not self.config.api_key:
            logger.warning("No API key - simulating order")
            return {
                "txid": [f"SIM_{int(time.time())}"],
                "status": "filled",
                "symbol": symbol,
                "side": side,
                "executedQty": quantity,
                "simulated": True,
            }

        kraken_symbol = self._normalize_symbol(symbol)

        endpoint = "/0/private/AddOrder"
        params = {
            "pair": kraken_symbol,
            "type": side.lower(),
            "ordertype": order_type.lower(),
            "volume": quantity,
        }

        if order_type.lower() == "limit" and price:
            params["price"] = price

        data = await self._make_request("POST", endpoint, params, signed=True)

        if data:
            txid = data.get("txid", [])
            logger.info(
                f"✅ Order placed: {side.upper()} {quantity} {symbol} @ {order_type}"
            )
            return {
                "txid": txid,
                "status": "pending",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "type": order_type,
            }
        else:
            logger.error("Failed to place order")
            return {}

    async def get_order_status(self, txid: str) -> Dict:
        """Check order status"""
        if not self.config.api_key:
            return {"txid": txid, "status": "filled", "simulated": True}

        endpoint = "/0/private/QueryOrders"
        params = {"txid": txid}

        data = await self._make_request("POST", endpoint, params, signed=True)

        if data:
            order = data.get(txid, {})
            return {
                "txid": txid,
                "status": order.get("status", "unknown"),
                "vol_exec": float(order.get("vol_exec", 0)),
                "price": float(order.get("price", 0)),
            }

        return {"txid": txid, "status": "unknown"}

    async def start_websocket(self, symbols: List[str]):
        """Start WebSocket connection for real-time price data"""
        # Cancel existing WebSocket task if any
        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        kraken_symbols = [self._normalize_symbol(s) for s in symbols]

        # Kraken WebSocket subscription
        subscribe_msg = {
            "event": "subscribe",
            "pair": kraken_symbols,
            "subscription": {"name": "ticker"},
        }

        async def ws_handler():
            async with websockets.connect(self.ws_url) as ws:
                await ws.send(json.dumps(subscribe_msg))
                async for message in ws:
                    try:
                        data = json.loads(message)
                        self._process_ws_message(data)
                    except json.JSONDecodeError:
                        continue

        self.ws_task = asyncio.create_task(ws_handler())
        logger.info(f"📡 WebSocket started for {symbols}")

    def _process_ws_message(self, data):
        """Process incoming WebSocket message"""
        # Kraken ticker format: [channelID, data, channelName, pair]
        if isinstance(data, list) and len(data) >= 4:
            try:
                pair = data[-1]  # e.g., "XBT/USD"
                ticker_data = data[1]

                if ticker_data:
                    self.price_data[pair.replace("/", "")] = {
                        "price": float(ticker_data["c"][0]),  # Current close price
                        "volume": float(ticker_data["v"][1]),  # 24h volume
                        "change_24h": float(ticker_data["p"][1]),  # 24h change
                        "timestamp": datetime.now(),
                    }
            except (IndexError, KeyError, TypeError):
                pass

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get latest price from WebSocket"""
        kraken_symbol = self._normalize_symbol(symbol)
        if kraken_symbol in self.price_data:
            return self.price_data[kraken_symbol]["price"]

        # Try alternate format
        alt_symbol = symbol.replace("USDT", "USD").replace("USD", "/USD")
        if alt_symbol in self.price_data:
            return self.price_data[alt_symbol]["price"]

        return None

    async def close(self):
        """Close all connections"""
        self.connected = False

        if self.ws_task and not self.ws_task.done():
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass

        if self.ws_connection:
            try:
                await self.ws_connection.close()
            except Exception:
                pass

        if self.session and not self.session.closed:
            await self.session.close()

        logger.info("🔌 Disconnected from Kraken")
