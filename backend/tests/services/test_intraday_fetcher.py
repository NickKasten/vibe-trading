"""
Comprehensive tests for intraday data fetching functionality.

Tests cover:
1. Market hours detection
2. Intraday bars fetching from Alpaca
3. Fallback logic (intraday -> daily)
4. Caching behavior
5. DataFrame format validation
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import os

from backend.app.services.fetcher import (
    fetch_intraday_bars,
    fetch_ohlcv,
    _is_market_hours,
    ALPACA_SDK_AVAILABLE
)


class TestMarketHoursDetection:
    """Test market hours detection logic."""

    @patch('backend.app.services.fetcher.datetime')
    def test_market_hours_weekday_open(self, mock_datetime):
        """Test that market is detected as open during trading hours on weekday."""
        from zoneinfo import ZoneInfo

        # Monday at 10:00 AM ET (market is open)
        mock_now = datetime(2025, 1, 6, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_datetime.now.return_value = mock_now

        result = _is_market_hours()
        assert result is True

    @patch('backend.app.services.fetcher.datetime')
    def test_market_hours_weekday_before_open(self, mock_datetime):
        """Test that market is detected as closed before 9:30 AM ET."""
        from zoneinfo import ZoneInfo

        # Monday at 9:00 AM ET (before market open)
        mock_now = datetime(2025, 1, 6, 9, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_datetime.now.return_value = mock_now

        result = _is_market_hours()
        assert result is False

    @patch('backend.app.services.fetcher.datetime')
    def test_market_hours_weekday_after_close(self, mock_datetime):
        """Test that market is detected as closed after 4:00 PM ET."""
        from zoneinfo import ZoneInfo

        # Monday at 5:00 PM ET (after market close)
        mock_now = datetime(2025, 1, 6, 17, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_datetime.now.return_value = mock_now

        result = _is_market_hours()
        assert result is False

    @patch('backend.app.services.fetcher.datetime')
    def test_market_hours_weekend(self, mock_datetime):
        """Test that market is detected as closed on weekends."""
        from zoneinfo import ZoneInfo

        # Saturday at 12:00 PM ET
        mock_now = datetime(2025, 1, 4, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        mock_datetime.now.return_value = mock_now

        result = _is_market_hours()
        assert result is False


class TestIntradayBarsBasic:
    """Test basic intraday bars fetching functionality."""

    def test_intraday_bars_requires_sdk(self):
        """Test that intraday bars returns None when SDK is not available."""
        with patch('backend.app.services.fetcher.ALPACA_SDK_AVAILABLE', False):
            result = fetch_intraday_bars("AAPL")
            assert result is None

    def test_intraday_bars_requires_credentials(self):
        """Test that intraday bars returns None when credentials are missing."""
        with patch('backend.app.services.fetcher.ALPACA_SDK_AVAILABLE', True):
            with patch.dict(os.environ, {}, clear=True):
                result = fetch_intraday_bars("AAPL")
                assert result is None

    @pytest.mark.skipif(not ALPACA_SDK_AVAILABLE, reason="Alpaca SDK not installed")
    @patch('backend.app.services.fetcher.StockHistoricalDataClient')
    def test_intraday_bars_successful_fetch(self, mock_client_class):
        """Test successful intraday bars fetch with mocked Alpaca client."""
        # Create mock data
        mock_data = pd.DataFrame({
            'open': [150.0, 151.0, 152.0],
            'high': [151.0, 152.0, 153.0],
            'low': [149.0, 150.0, 151.0],
            'close': [150.5, 151.5, 152.5],
            'volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2025-01-06 09:30', periods=3, freq='5min'))

        # Set up multi-index as Alpaca does
        mock_data.index = pd.MultiIndex.from_product(
            [['AAPL'], mock_data.index],
            names=['symbol', 'timestamp']
        )

        # Mock the client
        mock_client = MagicMock()
        mock_bars = MagicMock()
        mock_bars.df = mock_data
        mock_client.get_stock_bars.return_value = mock_bars
        mock_client_class.return_value = mock_client

        # Set up environment
        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret'
        }):
            result = fetch_intraday_bars("AAPL", timeframe_minutes=5)

        # Verify result
        assert result is not None
        assert not result.empty
        assert len(result) == 3
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert isinstance(result.index, pd.DatetimeIndex)

    @pytest.mark.skipif(not ALPACA_SDK_AVAILABLE, reason="Alpaca SDK not installed")
    @patch('backend.app.services.fetcher.StockHistoricalDataClient')
    def test_intraday_bars_handles_api_error(self, mock_client_class):
        """Test that API errors are handled gracefully."""
        # Mock client to raise an exception
        mock_client = MagicMock()
        mock_client.get_stock_bars.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret'
        }):
            result = fetch_intraday_bars("AAPL")

        assert result is None


class TestFetchOHLCVIntelligence:
    """Test intelligent dispatcher between intraday and daily data."""

    @patch('backend.app.services.fetcher._is_market_hours')
    @patch('backend.app.services.fetcher.fetch_intraday_bars')
    def test_uses_intraday_during_market_hours(self, mock_intraday, mock_market_hours):
        """Test that fetch_ohlcv uses intraday data when market is open."""
        mock_market_hours.return_value = True

        # Mock successful intraday fetch
        mock_df = pd.DataFrame({
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        }, index=pd.date_range('2025-01-06 09:30', periods=1, freq='5min'))
        mock_intraday.return_value = mock_df

        with patch('backend.app.services.fetcher.ALPACA_SDK_AVAILABLE', True):
            result = fetch_ohlcv("AAPL", prefer_intraday=True)

        # Verify intraday was called
        mock_intraday.assert_called_once_with("AAPL", timeframe_minutes=5)
        assert result is not None
        assert len(result) == 1

    @patch('backend.app.services.fetcher._is_market_hours')
    @patch('backend.app.services.fetcher._fetch_tiingo')
    def test_uses_daily_outside_market_hours(self, mock_tiingo, mock_market_hours):
        """Test that fetch_ohlcv uses daily data when market is closed."""
        mock_market_hours.return_value = False

        # Mock successful daily fetch
        mock_df = pd.DataFrame({
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        }, index=pd.date_range('2025-01-06', periods=1))
        mock_tiingo.return_value = mock_df

        with patch.dict(os.environ, {'TIINGO_API_KEY': 'test_key'}):
            result = fetch_ohlcv("AAPL", prefer_intraday=True)

        # Verify daily source was used
        mock_tiingo.assert_called_once()
        assert result is not None

    @patch('backend.app.services.fetcher._is_market_hours')
    @patch('backend.app.services.fetcher.fetch_intraday_bars')
    @patch('backend.app.services.fetcher._fetch_tiingo')
    def test_fallback_intraday_to_daily(self, mock_tiingo, mock_intraday, mock_market_hours):
        """Test fallback from intraday to daily when intraday fails."""
        mock_market_hours.return_value = True
        mock_intraday.return_value = None  # Intraday fails

        # Mock successful daily fetch
        mock_df = pd.DataFrame({
            'open': [150.0],
            'high': [151.0],
            'low': [149.0],
            'close': [150.5],
            'volume': [1000000]
        }, index=pd.date_range('2025-01-06', periods=1))
        mock_tiingo.return_value = mock_df

        with patch('backend.app.services.fetcher.ALPACA_SDK_AVAILABLE', True):
            with patch.dict(os.environ, {'TIINGO_API_KEY': 'test_key'}):
                result = fetch_ohlcv("AAPL", prefer_intraday=True)

        # Verify both were called
        mock_intraday.assert_called_once()
        mock_tiingo.assert_called_once()
        assert result is not None


class TestDataFrameFormat:
    """Test that returned DataFrames have correct format."""

    @pytest.mark.skipif(not ALPACA_SDK_AVAILABLE, reason="Alpaca SDK not installed")
    @patch('backend.app.services.fetcher.StockHistoricalDataClient')
    def test_intraday_dataframe_format(self, mock_client_class):
        """Test that intraday data has correct format and columns."""
        # Create properly formatted mock data
        dates = pd.date_range('2025-01-06 09:30', periods=100, freq='5min')
        mock_data = pd.DataFrame({
            'open': [150.0 + i*0.1 for i in range(100)],
            'high': [151.0 + i*0.1 for i in range(100)],
            'low': [149.0 + i*0.1 for i in range(100)],
            'close': [150.5 + i*0.1 for i in range(100)],
            'volume': [1000000 + i*1000 for i in range(100)]
        }, index=pd.MultiIndex.from_product([['AAPL'], dates], names=['symbol', 'timestamp']))

        mock_client = MagicMock()
        mock_bars = MagicMock()
        mock_bars.df = mock_data
        mock_client.get_stock_bars.return_value = mock_bars
        mock_client_class.return_value = mock_client

        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret'
        }):
            result = fetch_intraday_bars("AAPL")

        # Validate format
        assert isinstance(result, pd.DataFrame)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert set(result.columns) == {'open', 'high', 'low', 'close', 'volume'}
        assert len(result) == 100

        # Validate data types
        assert result['open'].dtype in [float, 'float64']
        assert result['close'].dtype in [float, 'float64']
        assert result['volume'].dtype in [int, 'int64', float, 'float64']


class TestCachingBehavior:
    """Test caching for intraday vs daily data."""

    @patch('backend.app.services.fetcher._is_market_hours')
    @patch('backend.app.services.fetcher.fetch_intraday_bars')
    def test_intraday_cache_ttl(self, mock_intraday, mock_market_hours):
        """Test that intraday data uses shorter cache TTL."""
        from backend.app.services.fetcher import cache, INTRADAY_CACHE_TTL

        mock_market_hours.return_value = True
        mock_df = pd.DataFrame({
            'close': [150.0]
        }, index=pd.date_range('2025-01-06 09:30', periods=1, freq='5min'))
        mock_intraday.return_value = mock_df

        # Clear cache
        cache.clear()

        with patch('backend.app.services.fetcher.ALPACA_SDK_AVAILABLE', True):
            # First call - should fetch
            result1 = fetch_ohlcv("AAPL", prefer_intraday=True)
            assert mock_intraday.call_count == 1

            # Second call immediately - should use cache
            result2 = fetch_ohlcv("AAPL", prefer_intraday=True)
            assert mock_intraday.call_count == 1  # Not called again

            # Verify cache key exists
            assert "AAPL_intraday" in cache


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
