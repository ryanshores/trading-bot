# Trading Bot Framework

A Python-based paper trading bot framework with pluggable strategies, Discord notifications, and web dashboard.

## 🚀 Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure the bot:**
Edit `config.py`:
- Set your exchange API keys (or leave blank for paper trading)
- Add your Discord webhook URL (optional)
- Choose your strategy
- Adjust risk parameters

3. **Run the bot:**
```bash
python bot.py
```

4. **Start the dashboard** (in a new terminal):
```bash
python dashboard.py
```
Then open http://localhost:5000 in your browser.

## 📁 Project Structure

```
trading-bot/
├── bot.py                      # Main bot engine
├── config.py                   # Configuration settings
├── dashboard.py                # Web dashboard server
├── requirements.txt            # Python dependencies
├── exchanges/
│   ├── exchange_interface.py   # Abstract exchange interface
│   └── binance_client.py       # Full Binance implementation
├── strategies/
│   ├── strategy_interface.py   # Abstract strategy interface
│   ├── trend_following.py      # MA Crossover + RSI strategy
│   └── mean_reversion.py       # Bollinger Bands strategy
└── utils/
    ├── logger.py               # Logging setup
    ├── risk_manager.py         # Risk management
    ├── performance_tracker.py  # Performance metrics
    ├── backtester.py           # Strategy backtesting
    └── notifier.py             # Discord notifications
```

## 🔧 Configuration

### Exchange Settings (`config.py`)
```python
EXCHANGE_CONFIG = ExchangeConfig(
    name="binance",           # or "coinbase", "kraken"
    api_key="your_key_here",  # Leave blank for paper trading
    api_secret="your_secret",
    testnet=True             # Use testnet for paper trading
)
```

### Trading Settings
```python
TRADING_CONFIG = TradingConfig(
    symbol="BTCUSDT",         # Trading pair
    timeframe="1h",          # 1m, 5m, 15m, 1h, 4h, 1d
    paper_trading=True,      # True = fake money
    max_position_size=100.0, # Max $ per trade
    stop_loss_percent=2.0,   # Stop loss at -2%
    take_profit_percent=4.0  # Take profit at +4%
)
```

### Discord Notifications (`config.py`)
```python
NOTIFICATION_CONFIG = NotificationConfig(
    discord_webhook_url="https://discord.com/api/webhooks/...",  # Get from Discord
    notify_on_buy=True,
    notify_on_sell=True,
    notify_on_error=True,
    daily_summary=True
)
```

**How to get Discord webhook:**
1. Open Discord server settings
2. Go to Integrations → Webhooks
3. Click "New Webhook"
4. Copy the webhook URL

### Strategy Settings
```python
STRATEGY_CONFIG = StrategyConfig(
    strategy_name="trend_following",  # or "mean_reversion"
    short_ma_period=20,
    long_ma_period=50,
    rsi_period=14
)
```

## 🧠 Strategies

### 1. Trend Following
Uses Moving Average Crossover + RSI:
- **BUY**: Short MA crosses above Long MA + RSI < 70
- **SELL**: Short MA crosses below Long MA OR RSI > 70

### 2. Mean Reversion
Uses Bollinger Bands:
- **BUY**: Price touches lower band (oversold)
- **SELL**: Price touches upper band (overbought)

## 📊 Web Dashboard

The dashboard provides real-time visualization:
- Current balance and PnL
- Win rate statistics
- Open positions
- Trade history table
- Balance chart over time

**Access:** http://localhost:5000

## 🔔 Discord Notifications

Get instant alerts for:
- ✅ Buy signals (with confidence and reason)
- ✅ Position closes (with PnL)
- ⚠️ Bot errors
- 📊 Daily summaries

## 🧪 Backtesting

Test strategies on historical data:

```python
from utils.backtester import Backtester
from strategies.trend_following import TrendFollowingStrategy
from config import STRATEGY_CONFIG

# Load historical data
import pandas as pd
data = pd.read_csv('historical_data.csv')

# Run backtest
strategy = TrendFollowingStrategy(STRATEGY_CONFIG)
backtester = Backtester(strategy, initial_balance=10000.0)
results = backtester.run(data)

# Results include:
# - Total return %
# - Win rate
# - Number of trades
# - Max drawdown
```

## 🛡️ Risk Management

The bot includes built-in risk management:
- Max position size limits
- Stop loss / take profit automation
- Max open positions limit
- Daily loss limits

**Always start with `paper_trading=True`!**

## 📊 Performance Tracking

Trades are logged to `trades.json`. Summary includes:
- Total trades
- Win rate
- Total PnL
- Average win/loss

## 📝 API Key Setup

### Binance Testnet (Free, Recommended for Testing)
1. Go to https://testnet.binance.vision/
2. Create an account
3. Generate API keys
4. Set `testnet=True` in config
5. ```python
EXCHANGE_CONFIG = ExchangeConfig(
    name="binance",
    api_key="your_kraken_api_key",
    api_secret="your_kraken_api_secret",
    testnet=False  # Use testnet for paper trading
)
```

### Binance Live (Real Money)
1. Go to https://www.binance.com/en/my/settings/api-management
2. Create API key with "Enable Spot & Margin Trading"
3. Set `testnet=False` in config

### Kraken
1. Go to https://www.kraken.com/u/security/api
2. Create a new API key with appropriate permissions
3. Add to config:
```python
EXCHANGE_CONFIG = ExchangeConfig(
    name="kraken",
    api_key="your_kraken_api_key",
    api_secret="your_kraken_api_secret",
    testnet=False  # Kraken doesn't have a testnet
)
```

**Note:** Kraken uses different symbol formats:
- BTC/USD → `BTCUSD` or `BTCUSDT` (auto-converted internally)
- ETH/USD → `ETHUSD` or `ETHUSDT` (auto-converted internally)

## ⚠️ Disclaimer

This is for educational purposes. Trading cryptocurrencies carries significant risk. Never trade with money you can't afford to lose. Past performance doesn't guarantee future results.

## 🐛 Troubleshooting

**Bot won't start:**
- Check Python version (3.8+)
- Install requirements: `pip install -r requirements.txt`

**No trades happening:**
- Check that indicators are calculating (add debug logging)
- Verify signal confidence thresholds

**API errors:**
- Ensure testnet=True for paper trading
- Check API key permissions

**Dashboard not loading:**
- Check if port 5000 is available
- Try: `python dashboard.py` and visit http://localhost:5000

**Discord notifications not working:**
- Verify webhook URL is correct
- Check that webhook channel exists

## 📚 Learning Resources

- [Binance API Docs](https://binance-docs.github.io/apidocs/spot/en/)
- [Technical Analysis Library (TA-Lib)](https://mrjbq7.github.io/ta-lib/)
- [Backtrader](https://www.backtrader.com/) (for backtesting)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software for personal or commercial purposes. See LICENSE for full terms.