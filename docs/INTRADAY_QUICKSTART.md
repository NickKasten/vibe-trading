# Intraday Data Enhancement - Quick Start Guide

## TL;DR

Your trading bot now uses **5-minute bars** during market hours instead of stale daily data. This is automatic and backward compatible.

---

## Setup (2 minutes)

### 1. Install Alpaca SDK

```bash
cd /Users/nick/Desktop/Summer2025Projects/vibe-trading
pip install alpaca-py>=0.8.0
```

### 2. Add Credentials to Environment

**Option A: Using .env file** (recommended)
```bash
# Add to your .env file or export in terminal
export ALPACA_API_KEY="PK..."
export ALPACA_SECRET_KEY="..."
```

**Option B: Render.com Environment Variables**
If deploying on Render:
1. Go to your service → Environment
2. Add `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
3. Restart service

### 3. Get Alpaca Keys (if you don't have them)

1. Go to https://alpaca.markets
2. Sign up for free account
3. Dashboard → API Keys → Generate New Key
4. **Use Paper Trading keys** for testing

---

## Verification (1 minute)

### Quick Test

```python
# Test that everything works
from backend.app.services.fetcher import fetch_intraday_bars, _is_market_hours
import os

# Check if market is open
print(f"Market open: {_is_market_hours()}")

# Try fetching intraday data
os.environ["ALPACA_API_KEY"] = "your_key_here"
os.environ["ALPACA_SECRET_KEY"] = "your_secret_here"

df = fetch_intraday_bars("AAPL", timeframe_minutes=5)
if df is not None:
    print(f"✅ Success! Fetched {len(df)} bars")
    print(f"Latest price: ${df['close'].iloc[-1]:.2f}")
else:
    print("⚠️ Intraday fetch failed (may be market closed or free tier limitation)")
```

### Run Tests

```bash
pytest backend/tests/services/test_intraday_fetcher.py -v
```

---

## How It Works

### Automatic Switching

```python
# During market hours (9:30 AM - 4:00 PM ET)
data = fetch_ohlcv("AAPL")
# → Returns ~3,900 bars of 5-minute data from Alpaca

# Outside market hours
data = fetch_ohlcv("AAPL")
# → Returns ~50-120 bars of daily data from Tiingo/Alpha Vantage
```

**No code changes needed!** Your existing `main.py` automatically benefits.

### Decision Tree

```
fetch_ohlcv("AAPL")
    │
    ├─ Is market open? YES
    │   ├─ Is Alpaca SDK available? YES
    │   │   ├─ Fetch 5-min bars from Alpaca
    │   │   └─ Success? → Return intraday data ✅
    │   │       Failure? → Fall back to daily data ⬇️
    │   └─ SDK not available? → Fall back to daily data ⬇️
    │
    └─ Is market closed? → Use daily data
        ├─ Try Tiingo
        ├─ Try Alpha Vantage
        └─ Try yfinance
```

---

## What You Get

### Before (Daily Data)
```
Date        Open    High    Low     Close   Volume
2025-01-02  180.00  182.50  179.00  181.25  50M
2025-01-03  181.50  183.00  180.50  182.10  48M
2025-01-06  182.00  184.00  181.50  183.50  52M  ← Yesterday's close
```

**Problem**: At 10:00 AM, you're trading on yesterday's $183.50 close, but stock is at $185.00!

### After (Intraday Data)
```
Timestamp           Open    High    Low     Close   Volume
2025-01-06 09:30    183.50  184.00  183.20  183.75  1.2M
2025-01-06 09:35    183.75  184.25  183.50  184.00  0.9M
2025-01-06 09:40    184.00  184.50  183.80  184.20  1.1M
...
2025-01-06 09:55    184.50  185.00  184.30  184.90  1.3M  ← 5 minutes ago
2025-01-06 10:00    184.90  185.20  184.70  185.00  1.5M  ← Latest bar
```

**Solution**: At 10:00 AM, you're trading on current $185.00 price!

---

## Important Notes

### 1. Free Tier Limitations

**Alpaca Free Tier**:
- ✅ 5-minute bars available
- ⚠️ Data is 15 minutes delayed (IEX feed)
- ⚠️ Historical data limited to last 15 minutes

**Impact**: You'll get recent intraday data, but not real-time and limited history.

**Upgrade Path**: Algo Trader Plus ($99/month) gives:
- Real-time data (no delay)
- Full historical intraday data
- Higher rate limits (10,000/min vs 200/min)

### 2. Market Holidays

The bot doesn't detect market holidays (e.g., MLK Day, Presidents' Day). On holidays:
- `_is_market_hours()` may return `True` (thinks market is open)
- Intraday fetch will fail (no data available)
- **Gracefully falls back to daily data** ✅

**Future Enhancement**: Add holiday calendar (pandas_market_calendars).

### 3. Technical Indicators

Your existing strategy uses:
- **SMA50**: 50-period moving average
- **RSI**: Relative Strength Index

**With intraday data**:
- SMA50 on 5-min bars = 50 × 5 min = 4.2 hours of data
- This is much shorter-term than SMA50 on daily bars (50 days)

**Consider**:
- Using SMA200 or SMA390 (one full trading day) for intraday
- Or keep SMA50 for short-term intraday momentum

---

## Monitoring

### Check Logs

```bash
# Look for these log messages during trading cycle:
tail -f logs/app.log | grep -i "intraday\|market"
```

**Expected logs during market hours**:
```
INFO - Market is open - attempting to fetch intraday data from Alpaca
INFO - Fetching 5-minute intraday bars for AAPL from Alpaca
INFO - Successfully fetched 3900 intraday bars for AAPL (timeframe: 5min)
INFO - Successfully using intraday data: 3900 bars
```

**Expected logs outside market hours**:
```
INFO - Market is closed - using daily data
INFO - Attempting to fetch from Tiingo API (primary source)
INFO - Successfully fetched from Tiingo - data shape: (120, 5)
```

---

## Troubleshooting

### Problem: "alpaca-py SDK not available"

**Solution**: Install the SDK
```bash
pip install alpaca-py>=0.8.0
```

### Problem: "Alpaca credentials not found"

**Solution**: Set environment variables
```bash
export ALPACA_API_KEY="your_key"
export ALPACA_SECRET_KEY="your_secret"
```

Verify they're set:
```bash
echo $ALPACA_API_KEY
```

### Problem: "Alpaca returned empty data"

**Possible causes**:
1. **Free tier limitation**: Free tier only has last 15 minutes of data
2. **Market closed**: No new bars when market is closed
3. **Invalid symbol**: Check that symbol exists

**Solution**: Check Alpaca dashboard, verify account status, try during market hours.

### Problem: Always falling back to daily data

**Check**:
1. Is market currently open? (9:30 AM - 4:00 PM ET, Mon-Fri)
2. Are Alpaca credentials correct?
3. Is alpaca-py installed?

**Debug**:
```python
from backend.app.services.fetcher import _is_market_hours, ALPACA_SDK_AVAILABLE
import os

print(f"Market open: {_is_market_hours()}")
print(f"SDK available: {ALPACA_SDK_AVAILABLE}")
print(f"API key set: {bool(os.getenv('ALPACA_API_KEY'))}")
```

---

## Performance Comparison

### Before Intraday Enhancement

```
Trading Cycle: 2025-01-06 10:00 AM ET
├─ Fetch OHLCV: Daily data (Tiingo)
├─ Latest data: 2025-01-05 (yesterday)
├─ Price used: $183.50 (yesterday's close)
├─ Actual price: $185.00 (current)
└─ Price lag: $1.50 (0.8%)  ⚠️
```

### After Intraday Enhancement

```
Trading Cycle: 2025-01-06 10:00 AM ET
├─ Fetch OHLCV: Intraday 5-min bars (Alpaca)
├─ Latest data: 2025-01-06 10:00 AM (current)
├─ Price used: $185.00 (latest bar)
├─ Actual price: $185.00 (current)
└─ Price lag: $0.00 (0.0%)  ✅
```

**Note**: With free tier (15-min delay), you'd see $184.90 instead of $185.00, which is still much better than yesterday's $183.50!

---

## Next Steps

1. ✅ **Install SDK**: `pip install alpaca-py>=0.8.0`
2. ✅ **Set credentials**: Add `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` to environment
3. ✅ **Run tests**: `pytest backend/tests/services/test_intraday_fetcher.py -v`
4. ✅ **Test during market hours**: Run trading cycle and check logs
5. 📊 **Monitor performance**: Compare trades before/after intraday enhancement
6. 💰 **Consider paid tier**: If you need real-time data and full history

---

## Resources

- **Full Documentation**: `/docs/INTRADAY_DATA_ENHANCEMENT.md`
- **Alpaca Docs**: https://docs.alpaca.markets
- **Alpaca Dashboard**: https://app.alpaca.markets
- **Test Suite**: `/backend/tests/services/test_intraday_fetcher.py`

---

**Questions?** Check the full documentation or review the implementation in `/backend/app/services/fetcher.py`.

**Happy Trading!** 📈
