# Intraday Data Enhancement Documentation

## Executive Summary

The trading bot has been enhanced to use **real-time intraday price data** instead of stale daily closes. This is a critical improvement for an intraday trading strategy that runs every 5 minutes.

**Before**: Bot fetched daily OHLCV data, meaning it traded on yesterday's closing price.
**After**: Bot fetches 5-minute bars during market hours, providing near real-time price data.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution Architecture](#solution-architecture)
3. [Implementation Details](#implementation-details)
4. [API Details: Alpaca Bars API](#api-details-alpaca-bars-api)
5. [Usage Guide](#usage-guide)
6. [Testing](#testing)
7. [Limitations & Considerations](#limitations--considerations)
8. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### The Issue

The trading bot runs every 5 minutes to make intraday trading decisions. However, it was fetching **daily OHLCV data** from sources like Tiingo, Alpha Vantage, and yfinance. This meant:

- **Stale prices**: During market hours (9:30 AM - 4:00 PM ET), the bot was using yesterday's closing price.
- **Missed opportunities**: Intraday price movements were not captured.
- **Poor signal quality**: Technical indicators (SMA, RSI) calculated on daily data don't reflect intraday momentum.

### Example Scenario

**Without intraday data**:
- 10:00 AM: AAPL closed yesterday at $150.00
- Bot fetches daily data: latest close = $150.00
- Bot makes decision based on $150.00
- **Problem**: AAPL is actually trading at $152.50 right now!

**With intraday data**:
- 10:00 AM: AAPL is trading at $152.50
- Bot fetches 5-minute bars: latest bar shows $152.50
- Bot makes decision based on current price
- **Result**: Accurate, timely trading decisions

---

## Solution Architecture

### High-Level Strategy

```
┌─────────────────────────────────────────────────┐
│           fetch_ohlcv() - Smart Dispatcher      │
│                                                  │
│  1. Check: Is market open?                      │
│  2. Check: Is Alpaca SDK available?             │
│  3. Decide: Intraday or Daily?                  │
└─────────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    Market OPEN              Market CLOSED
    (9:30-4:00 ET)          (After hours/weekends)
         │                         │
         ▼                         ▼
  ┌──────────────┐          ┌──────────────┐
  │  Intraday    │          │  Daily Data  │
  │  Bars from   │          │  from        │
  │  Alpaca      │          │  Tiingo/AV   │
  │  (5-min)     │          │  (fallback)  │
  └──────────────┘          └──────────────┘
         │                         │
         └────────────┬────────────┘
                      ▼
           ┌─────────────────────┐
           │  Fallback Chain     │
           │                     │
           │  1. Alpaca (5-min)  │
           │  2. Tiingo (daily)  │
           │  3. Alpha V (daily) │
           │  4. yfinance (daily)│
           └─────────────────────┘
```

### Key Design Decisions

1. **Intelligent Routing**: Use intraday during market hours, fall back to daily when market is closed.
2. **Graceful Degradation**: If intraday fails (API issue, missing SDK), seamlessly fall back to daily data.
3. **Backward Compatibility**: Existing code continues to work; intraday is an enhancement, not a breaking change.
4. **Caching Strategy**: Shorter cache TTL for intraday data (60 seconds) vs daily data (5 minutes).

---

## Implementation Details

### New Components

#### 1. Market Hours Detection: `_is_market_hours()`

```python
def _is_market_hours() -> bool:
    """
    Check if current time is within US market hours (9:30 AM - 4:00 PM ET).

    Returns:
        bool: True if market is currently open, False otherwise
    """
```

**Logic**:
- Get current time in Eastern timezone (America/New_York)
- Check if weekday (Monday-Friday)
- Check if time is between 9:30 AM and 4:00 PM ET
- Return True only if both conditions are met

**Note**: This is a basic implementation that doesn't account for market holidays. For production, consider integrating with `pandas_market_calendars` or Alpaca's clock API.

#### 2. Intraday Bars Fetcher: `fetch_intraday_bars()`

```python
def fetch_intraday_bars(
    symbol: str = "AAPL",
    timeframe_minutes: int = 5
) -> Optional[pd.DataFrame]:
    """
    Fetch intraday bars using Alpaca API.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        timeframe_minutes: Timeframe in minutes (1, 5, or 15 recommended)

    Returns:
        DataFrame with columns: open, high, low, close, volume
        Index is datetime (timestamp of each bar)
        Returns None if intraday data is unavailable
    """
```

**Features**:
- Uses Alpaca's `StockHistoricalDataClient` from `alpaca-py` SDK
- Fetches 60 calendar days of historical bars (ensures enough data for SMA50)
- Supports multiple timeframes: 1-min, 5-min, 15-min
- Returns properly formatted DataFrame matching existing data format
- Handles multi-index responses from Alpaca API

**Data Volume Calculations**:
- **5-minute bars**: 78 bars/day × 50 trading days = 3,900 bars
- **1-minute bars**: 390 bars/day × 50 trading days = 19,500 bars
- **15-minute bars**: 26 bars/day × 50 trading days = 1,300 bars

Fetching 60 calendar days (~40-45 trading days) ensures sufficient data for technical indicators.

#### 3. Enhanced OHLCV Fetcher: `fetch_ohlcv()`

**New signature**:
```python
def fetch_ohlcv(
    symbol: str = "AAPL",
    prefer_intraday: bool = True
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data with intelligent selection between intraday and daily data.

    Strategy:
    1. During market hours: Fetch 5-minute intraday bars from Alpaca (if available)
    2. Outside market hours or if intraday fails: Fall back to daily data
    """
```

**Decision Logic**:
```python
use_intraday = prefer_intraday and _is_market_hours() and ALPACA_SDK_AVAILABLE

if use_intraday:
    df = fetch_intraday_bars(symbol, timeframe_minutes=5)
    if df is not None:
        return df  # Success!
    else:
        # Fall back to daily data

# Daily data fallback chain: Tiingo → Alpha Vantage → yfinance
```

### Caching Strategy

| Data Type | Cache Key Format | TTL | Rationale |
|-----------|-----------------|-----|-----------|
| Intraday | `{symbol}_intraday` | 60 seconds | Prices change frequently during market hours |
| Daily | `{symbol}_ohlcv` | 5 minutes | Daily data doesn't change as rapidly |
| Fallback Cache | Same as above | 24 hours | Emergency backup if all sources fail |

---

## API Details: Alpaca Bars API

### Overview

**Alpaca Markets** provides both trading and market data APIs. We use their **Market Data API** specifically for historical bars.

**Official Documentation**: https://docs.alpaca.markets/reference/stockbars

### Authentication

Alpaca uses API key/secret authentication via HTTP headers:

```python
headers = {
    "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY"),
    "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY")
}
```

**Required Environment Variables**:
- `ALPACA_API_KEY`: Your Alpaca API key
- `ALPACA_SECRET_KEY`: Your Alpaca secret key

### Endpoint

**Base URL**: `https://data.alpaca.markets/v2/stocks/bars`

**HTTP Method**: GET

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` or `symbols` | string | Yes | Single symbol or comma-separated list |
| `timeframe` | string | Yes | Bar timeframe: `1Min`, `5Min`, `15Min`, `1Hour`, `1Day` |
| `start` | datetime | Yes | Start date/time (ISO 8601 format) |
| `end` | datetime | No | End date/time (defaults to now) |
| `limit` | int | No | Max number of bars to return (default: 1000, max: 10000) |
| `page_token` | string | No | Token for pagination |

### Example Request (using alpaca-py SDK)

```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Initialize client
client = StockHistoricalDataClient(
    api_key="YOUR_API_KEY",
    secret_key="YOUR_SECRET_KEY"
)

# Create request
request = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame(5, "Min"),  # 5-minute bars
    start=datetime(2025, 1, 1),
    end=datetime(2025, 1, 6)
)

# Fetch bars
bars = client.get_stock_bars(request)

# Convert to DataFrame
df = bars.df
```

### Example Response Structure

**Raw API Response** (JSON):
```json
{
  "bars": {
    "AAPL": [
      {
        "t": "2025-01-06T09:30:00Z",
        "o": 150.00,
        "h": 150.50,
        "l": 149.80,
        "c": 150.25,
        "v": 1234567
      },
      {
        "t": "2025-01-06T09:35:00Z",
        "o": 150.25,
        "h": 150.75,
        "l": 150.10,
        "c": 150.60,
        "v": 987654
      }
    ]
  },
  "next_page_token": null
}
```

**SDK DataFrame Response**:
```
                                    open    high     low   close    volume
symbol timestamp
AAPL   2025-01-06 09:30:00-05:00  150.00  150.50  149.80  150.25  1234567
       2025-01-06 09:35:00-05:00  150.25  150.75  150.10  150.60   987654
       2025-01-06 09:40:00-05:00  150.60  151.00  150.40  150.85  1100000
       ...
```

Our implementation flattens this multi-index to single-index with datetime:

```
                         open    high     low   close    volume
2025-01-06 09:30:00    150.00  150.50  149.80  150.25  1234567
2025-01-06 09:35:00    150.25  150.75  150.10  150.60   987654
2025-01-06 09:40:00    150.60  151.00  150.40  150.85  1100000
```

### Rate Limits & Pricing

#### Free Tier (Basic)
- **Real-time data**: Limited to IEX exchange only
- **Historical data**: Limited to last 15 minutes
- **Rate limit**: 200 requests/minute
- **WebSocket subscriptions**: Max 30 symbols
- **Cost**: Free

#### Paid Tier (Algo Trader Plus)
- **Real-time data**: All US exchanges (CTA/UTP consolidated feed)
- **Historical data**: Full historical access (years of data)
- **Rate limit**: 10,000 requests/minute
- **WebSocket subscriptions**: Unlimited
- **Cost**: $99/month

**Recommendation**: Start with free tier for testing. Upgrade to paid tier for production if you need:
1. Real-time data (not 15-minute delayed)
2. Full historical data for backtesting
3. Higher rate limits

### How Bars Are Calculated

From Alpaca's documentation:

> **Minute and daily bars** are aggregated from trades. The (SIP) timestamp of the trade is truncated to the minute for minute bars and to the day (in New York) for daily bars.
>
> **All other non-minute and non-daily bars** are aggregated from the minute and daily bars. For example, an hour (1Hour) bar is aggregated from all the minute bars in the given hour and a weekly bar (1Week) is aggregated from all the daily bars in the given week.

This means:
- **1-min bars**: Direct aggregation from trade data (most granular)
- **5-min bars**: Aggregated from five 1-min bars
- **15-min bars**: Aggregated from fifteen 1-min bars

For maximum accuracy, use 1-min or 5-min bars rather than larger timeframes.

---

## Usage Guide

### Prerequisites

1. **Install alpaca-py SDK**:
   ```bash
   pip install alpaca-py>=0.8.0
   ```

2. **Set environment variables**:
   ```bash
   export ALPACA_API_KEY="your_api_key_here"
   export ALPACA_SECRET_KEY="your_secret_key_here"
   ```

3. **Sign up for Alpaca** (if you haven't):
   - Go to https://alpaca.markets
   - Create an account
   - Get your API keys from the dashboard
   - Use paper trading keys for testing

### Basic Usage

The enhancement is **automatic** - no code changes needed in `main.py`:

```python
from backend.app.services.fetcher import fetch_ohlcv

# This will automatically use intraday data during market hours
df = fetch_ohlcv("AAPL")

# During market hours (9:30 AM - 4:00 PM ET):
# → Returns 5-minute bars from Alpaca
# → ~3,900 bars covering last 50 trading days

# Outside market hours:
# → Returns daily bars from Tiingo/Alpha Vantage/yfinance
# → ~50-120 daily bars covering last 3-4 months
```

### Advanced Usage

#### Disable Intraday (Force Daily Data)

```python
df = fetch_ohlcv("AAPL", prefer_intraday=False)
# Always uses daily data, even during market hours
```

#### Fetch Intraday Directly

```python
from backend.app.services.fetcher import fetch_intraday_bars

# Fetch 1-minute bars
df_1min = fetch_intraday_bars("AAPL", timeframe_minutes=1)

# Fetch 5-minute bars
df_5min = fetch_intraday_bars("AAPL", timeframe_minutes=5)

# Fetch 15-minute bars
df_15min = fetch_intraday_bars("AAPL", timeframe_minutes=15)
```

#### Check Market Hours

```python
from backend.app.services.fetcher import _is_market_hours

if _is_market_hours():
    print("Market is open - using intraday data")
else:
    print("Market is closed - using daily data")
```

### Integration with Existing Code

**No changes needed!** The enhancement is backward compatible:

**Before**:
```python
# main.py - trading cycle
data = fetch_ohlcv(symbol)  # Returns daily data
signals = generate_signals(data)
```

**After**:
```python
# main.py - trading cycle
data = fetch_ohlcv(symbol)  # Returns intraday during market hours, daily otherwise
signals = generate_signals(data)  # Works with both!
```

The `generate_signals()` function doesn't need to know whether it's using intraday or daily data - it just calculates indicators on whatever bars are provided.

---

## Testing

### Running the Tests

```bash
# Run all intraday tests
pytest backend/tests/services/test_intraday_fetcher.py -v

# Run specific test class
pytest backend/tests/services/test_intraday_fetcher.py::TestMarketHoursDetection -v

# Run with coverage
pytest backend/tests/services/test_intraday_fetcher.py --cov=backend.app.services.fetcher
```

### Test Coverage

The test suite includes:

1. **Market Hours Detection** (5 tests)
   - Market open during trading hours (weekday 9:30-4:00 ET)
   - Market closed before open (weekday before 9:30 ET)
   - Market closed after close (weekday after 4:00 PM ET)
   - Market closed on weekends
   - Error handling for timezone issues

2. **Intraday Bars Basic** (4 tests)
   - Requires SDK check
   - Requires credentials check
   - Successful fetch with mocked API
   - API error handling

3. **Intelligent Dispatcher** (3 tests)
   - Uses intraday during market hours
   - Uses daily outside market hours
   - Fallback from intraday to daily on error

4. **DataFrame Format** (1 test)
   - Validates column names (open, high, low, close, volume)
   - Validates index type (DatetimeIndex)
   - Validates data types (float for prices, int/float for volume)

5. **Caching Behavior** (1 test)
   - Verifies intraday cache TTL
   - Verifies cache keys
   - Verifies cache hit/miss behavior

**Total**: 14 comprehensive tests

### Manual Testing

#### Test Intraday Fetch (During Market Hours)

```python
from backend.app.services.fetcher import fetch_intraday_bars
import os

# Set credentials
os.environ["ALPACA_API_KEY"] = "your_key"
os.environ["ALPACA_SECRET_KEY"] = "your_secret"

# Fetch intraday bars
df = fetch_intraday_bars("AAPL", timeframe_minutes=5)

print(f"Fetched {len(df)} bars")
print(f"Date range: {df.index[0]} to {df.index[-1]}")
print(f"Latest close: ${df['close'].iloc[-1]:.2f}")
print(df.tail(10))
```

#### Test Intelligent Dispatcher

```python
from backend.app.services.fetcher import fetch_ohlcv

# Will automatically choose intraday or daily
df = fetch_ohlcv("AAPL")

# Check what type of data was returned
if len(df) > 1000:
    print("Got intraday data (many bars)")
else:
    print("Got daily data (fewer bars)")
```

---

## Limitations & Considerations

### 1. Alpaca Free Tier Limitations

**15-Minute Delay**:
- Free tier provides **IEX exchange data** with a 15-minute delay
- This means prices are 15 minutes behind real-time
- For a bot running every 5 minutes, this is still much better than yesterday's close!

**Workaround**: Upgrade to paid tier ($99/month) for real-time data.

### 2. Market Holidays Not Handled

The `_is_market_hours()` function checks day of week and time, but doesn't account for:
- Market holidays (e.g., New Year's Day, MLK Day, Presidents' Day, etc.)
- Early closes (e.g., day before Thanksgiving, Christmas Eve)

**Impact**: On market holidays, the bot will attempt to fetch intraday data and fail, then fall back to daily data. This is graceful but not ideal.

**Future Enhancement**: Integrate with `pandas_market_calendars` or use Alpaca's Clock API:
```python
from alpaca.trading.client import TradingClient

client = TradingClient(api_key, secret_key)
clock = client.get_clock()
if clock.is_open:
    # Market is open
```

### 3. Historical Data Limits (Free Tier)

Free tier limits historical intraday data to **last 15 minutes**. This is not enough for SMA50 calculation!

**Solution**: Our implementation requests 60 days of data, which works on paid tier but fails on free tier. The code gracefully falls back to daily data.

**Recommendation**:
- For **testing**: Use free tier, accept daily data fallback
- For **production**: Use paid tier for full historical intraday data

### 4. Data Volume & API Costs

**5-minute bars over 60 days**:
- 78 bars/day × 50 trading days = **3,900 bars per request**
- With 200 requests/minute limit (free tier), you can fetch ~780,000 bars/minute
- For 5 symbols: 19,500 bars = well within limits

**Bandwidth**: Each bar is ~50 bytes (JSON), so 3,900 bars ≈ 195 KB per request.

**Conclusion**: API costs and bandwidth are not a concern for typical usage.

### 5. Signal Generation Assumptions

The `generate_signals()` function was designed for daily data. It calculates:
- SMA50: 50-period simple moving average
- RSI: Relative Strength Index

**With intraday data**:
- SMA50 on 5-min bars = 50 bars = ~4.2 hours of trading history
- This is very short-term momentum!

**Consideration**: You may want to adjust indicator periods for intraday data:
- Use SMA200 or SMA390 (full trading day) instead of SMA50
- Use different RSI periods

**Future Enhancement**: Add parameter to `generate_signals()` to auto-adjust periods based on bar timeframe.

### 6. DataFrame Index Timezone

Alpaca returns timestamps in **UTC** with timezone info:
```
2025-01-06 14:30:00+00:00  (UTC)
```

Our implementation preserves this. If you need **Eastern Time** (ET):
```python
df.index = df.index.tz_convert('America/New_York')
```

---

## Future Enhancements

### 1. WebSocket Real-Time Streaming

Instead of fetching historical bars every 5 minutes, **stream bars in real-time** via WebSocket:

```python
from alpaca.data.live import StockDataStream

stream = StockDataStream(api_key, secret_key)

@stream.on_bar('AAPL')
async def on_bar(bar):
    print(f"New bar: {bar}")
    # Trigger signal generation immediately

stream.run()
```

**Benefits**:
- No polling delay (5-minute wait)
- Instant signal generation when new bar closes
- Lower API usage

**Complexity**: Requires async/await architecture change.

### 2. Market Calendar Integration

Use `pandas_market_calendars` for accurate holiday detection:

```python
import pandas_market_calendars as mcal

nyse = mcal.get_calendar('NYSE')
schedule = nyse.schedule(start_date='2025-01-01', end_date='2025-12-31')

def is_market_open():
    now = pd.Timestamp.now(tz='America/New_York')
    if now in schedule.index:
        # Check if current time is within market hours
        ...
```

### 3. Multi-Timeframe Analysis

Support multiple timeframes simultaneously:

```python
df_1min = fetch_intraday_bars("AAPL", timeframe_minutes=1)
df_5min = fetch_intraday_bars("AAPL", timeframe_minutes=5)
df_15min = fetch_intraday_bars("AAPL", timeframe_minutes=15)

# Generate signals using multiple timeframes
signals = generate_signals_multi_timeframe(df_1min, df_5min, df_15min)
```

**Benefit**: Capture both short-term and medium-term momentum.

### 4. Adaptive Indicator Periods

Automatically adjust indicator periods based on bar timeframe:

```python
def generate_signals(df, timeframe_minutes=1440):  # 1440 = daily
    if timeframe_minutes == 1:
        sma_period = 390  # 1 full trading day
        rsi_period = 14 * 390  # 14 trading days
    elif timeframe_minutes == 5:
        sma_period = 78  # 1 full trading day
        rsi_period = 14 * 78  # 14 trading days
    else:  # daily
        sma_period = 50
        rsi_period = 14

    df['sma'] = df['close'].rolling(sma_period).mean()
    df['rsi'] = calculate_rsi(df['close'], rsi_period)
    ...
```

### 5. Pre-Market & After-Hours Data

Extend market hours to include extended trading:

```python
def _is_extended_hours() -> bool:
    """Check if within extended hours (4:00 AM - 8:00 PM ET)"""
    ...

# Fetch pre-market and after-hours bars
df = fetch_intraday_bars("AAPL", include_extended_hours=True)
```

**Benefit**: Capture overnight gaps and early momentum.

### 6. Cost Monitoring & Budgeting

Track API usage and costs:

```python
from backend.app.services.fetcher import get_api_usage_stats

stats = get_api_usage_stats()
print(f"Alpaca requests today: {stats['alpaca_requests']}")
print(f"Estimated cost: ${stats['estimated_cost']:.2f}")
```

---

## Conclusion

The intraday data enhancement transforms the trading bot from a **daily close trader** to a **real-time intraday trader**. This is a significant improvement for a strategy that runs every 5 minutes.

**Key Benefits**:
1. ✅ Trades on current prices (not yesterday's close)
2. ✅ Captures intraday momentum and reversals
3. ✅ More accurate technical indicators
4. ✅ Backward compatible with existing code
5. ✅ Graceful fallback to daily data when needed

**Next Steps**:
1. Install `alpaca-py`: `pip install alpaca-py>=0.8.0`
2. Set Alpaca credentials in environment variables
3. Run tests to verify functionality
4. Monitor logs during first few trading cycles
5. Consider upgrading to Alpaca paid tier for real-time data

**Questions or Issues?**
- Check logs for detailed error messages
- Review Alpaca API documentation: https://docs.alpaca.markets
- File an issue in the project repository

---

**Document Version**: 1.0
**Last Updated**: 2025-01-06
**Author**: Intraday Data Enhancement Specialist
