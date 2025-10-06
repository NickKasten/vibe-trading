"""
Rate Limit Compliance Agent Tests

This agent validates that the application properly respects external API rate limits
by using caching effectively and avoiding unnecessary API calls.

Test Coverage:
- Cache effectiveness (hit rate > 95%)
- Concurrent request deduplication
- Rate limit error handling
- Key rotation functionality
- Fallback cache activation
- Cold vs warm cache behavior
"""
import pytest
import time
from unittest.mock import patch, MagicMock, call
from backend.app.services import fetcher
from backend.app.services.fetcher import fetch_ohlcv, RateLimitError, _fetch_tiingo, _fetch_alpha_vantage_with_key
import pandas as pd
from datetime import datetime, timedelta


class TestCacheEffectiveness:
    """Validate that caching prevents redundant API calls."""

    def test_cache_hit_on_repeated_requests(self):
        """Test that repeated requests use cache instead of hitting external APIs."""
        # Clear cache
        fetcher.cache.clear()

        with patch('backend.app.services.fetcher._fetch_tiingo') as mock_tiingo:
            # Create mock DataFrame
            mock_df = pd.DataFrame({
                'close': [150.0, 151.0, 152.0],
                'open': [149.0, 150.0, 151.0],
                'high': [152.0, 153.0, 154.0],
                'low': [148.0, 149.0, 150.0],
                'volume': [1000000, 1100000, 1200000]
            }, index=pd.date_range(start='2025-01-01', periods=3))

            mock_tiingo.return_value = mock_df

            # First call - should hit API
            result1 = fetch_ohlcv("AAPL")
            assert result1 is not None
            assert mock_tiingo.call_count == 1

            # Second call within cache TTL - should use cache
            result2 = fetch_ohlcv("AAPL")
            assert result2 is not None
            assert mock_tiingo.call_count == 1  # No additional API call

            # Results should be equal
            pd.testing.assert_frame_equal(result1, result2)

    def test_cache_expiration_triggers_refresh(self):
        """Test that cache expiration causes new API call."""
        fetcher.cache.clear()

        # Temporarily reduce cache TTL for testing
        original_ttl = fetcher.CACHE_TTL
        fetcher.CACHE_TTL = 1  # 1 second

        try:
            with patch('backend.app.services.fetcher._fetch_tiingo') as mock_tiingo:
                mock_df = pd.DataFrame({
                    'close': [150.0],
                    'open': [149.0],
                    'high': [151.0],
                    'low': [148.0],
                    'volume': [1000000]
                }, index=pd.date_range(start='2025-01-01', periods=1))

                mock_tiingo.return_value = mock_df

                # First call
                fetch_ohlcv("AAPL")
                assert mock_tiingo.call_count == 1

                # Wait for cache to expire
                time.sleep(1.5)

                # Second call after expiration - should hit API again
                fetch_ohlcv("AAPL")
                assert mock_tiingo.call_count == 2

        finally:
            fetcher.CACHE_TTL = original_ttl

    def test_different_symbols_cached_separately(self):
        """Test that different symbols have separate cache entries."""
        fetcher.cache.clear()

        with patch('backend.app.services.fetcher._fetch_tiingo') as mock_tiingo:
            mock_df = pd.DataFrame({
                'close': [150.0],
                'open': [149.0],
                'high': [151.0],
                'low': [148.0],
                'volume': [1000000]
            }, index=pd.date_range(start='2025-01-01', periods=1))

            mock_tiingo.return_value = mock_df

            # Fetch two different symbols
            fetch_ohlcv("AAPL")
            fetch_ohlcv("MSFT")

            # Should have made 2 API calls (one per symbol)
            assert mock_tiingo.call_count == 2


class TestRateLimitErrorHandling:
    """Validate proper handling of rate limit errors."""

    def test_rate_limit_error_caught_from_tiingo(self):
        """Test that rate limit errors from Tiingo are properly caught."""
        fetcher.cache.clear()

        with patch('backend.app.services.fetcher._fetch_tiingo') as mock_tiingo:
            mock_tiingo.side_effect = RateLimitError("Tiingo rate limit exceeded")

            with patch('backend.app.services.fetcher._fetch_alpha_vantage') as mock_alpha:
                mock_df = pd.DataFrame({
                    'close': [150.0],
                    'open': [149.0],
                    'high': [151.0],
                    'low': [148.0],
                    'volume': [1000000]
                }, index=pd.date_range(start='2025-01-01', periods=1))
                mock_alpha.return_value = mock_df

                # Should fall back to Alpha Vantage
                result = fetch_ohlcv("AAPL")
                assert result is not None
                assert mock_alpha.called

    def test_fallback_cache_used_when_all_apis_fail(self):
        """Test that fallback cache is used when all APIs fail."""
        fetcher.cache.clear()
        fetcher.fallback_cache.clear()

        # Populate fallback cache
        mock_df = pd.DataFrame({
            'close': [150.0],
            'open': [149.0],
            'high': [151.0],
            'low': [148.0],
            'volume': [1000000]
        }, index=pd.date_range(start='2025-01-01', periods=1))

        cache_key = "AAPL"
        fetcher.fallback_cache[cache_key] = {
            'data': mock_df,
            'timestamp': time.time()
        }

        with patch('backend.app.services.fetcher._fetch_tiingo') as mock_tiingo, \
             patch('backend.app.services.fetcher._fetch_alpha_vantage') as mock_alpha:

            mock_tiingo.side_effect = RateLimitError("Rate limit")
            mock_alpha.side_effect = RateLimitError("Rate limit")

            # Should use fallback cache
            result = fetch_ohlcv("AAPL")
            assert result is not None
            pd.testing.assert_frame_equal(result, mock_df)


class TestConcurrentRequestDeduplication:
    """Validate that concurrent requests for the same symbol are deduplicated."""

    def test_concurrent_requests_use_same_cache(self):
        """Test that multiple concurrent requests use cached data."""
        import threading

        fetcher.cache.clear()
        call_count = {'value': 0}
        lock = threading.Lock()

        def mock_tiingo_with_delay(*args, **kwargs):
            with lock:
                call_count['value'] += 1
            time.sleep(0.1)  # Simulate API latency
            return pd.DataFrame({
                'close': [150.0],
                'open': [149.0],
                'high': [151.0],
                'low': [148.0],
                'volume': [1000000]
            }, index=pd.date_range(start='2025-01-01', periods=1))

        with patch('backend.app.services.fetcher._fetch_tiingo', side_effect=mock_tiingo_with_delay):
            results = []

            def fetch_and_store():
                result = fetch_ohlcv("AAPL")
                results.append(result)

            # Start multiple threads simultaneously
            threads = [threading.Thread(target=fetch_and_store) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All threads should have received data
            assert len(results) == 5
            assert all(r is not None for r in results)

            # Due to caching, we should have significantly fewer than 5 API calls
            # (ideally 1, but race conditions might cause 2-3)
            assert call_count['value'] <= 3


class TestKeyRotation:
    """Validate API key rotation for Alpha Vantage."""

    def test_multiple_alpha_vantage_keys_available(self):
        """Test that multiple Alpha Vantage keys are detected."""
        with patch.dict('os.environ', {
            'ALPHA_VANTAGE_API_KEY': 'key1',
            'ALPHA_VANTAGE_API_KEY_2': 'key2',
            'ALPHA_VANTAGE_API_KEY_3': 'key3'
        }):
            keys = fetcher._get_api_keys()
            assert len(keys['alpha_vantage_keys']) == 3
            assert 'key1' in keys['alpha_vantage_keys']
            assert 'key2' in keys['alpha_vantage_keys']
            assert 'key3' in keys['alpha_vantage_keys']


class TestCacheMetrics:
    """Validate cache performance metrics."""

    def test_cache_hit_rate_under_load(self):
        """Test cache hit rate under simulated load (target > 95%)."""
        fetcher.cache.clear()
        api_calls = {'count': 0}

        def mock_fetch(*args, **kwargs):
            api_calls['count'] += 1
            return pd.DataFrame({
                'close': [150.0],
                'open': [149.0],
                'high': [151.0],
                'low': [148.0],
                'volume': [1000000]
            }, index=pd.date_range(start='2025-01-01', periods=1))

        with patch('backend.app.services.fetcher._fetch_tiingo', side_effect=mock_fetch):
            # Simulate 100 requests for the same symbol
            total_requests = 100
            for _ in range(total_requests):
                fetch_ohlcv("AAPL")

            # Calculate cache hit rate
            cache_hits = total_requests - api_calls['count']
            hit_rate = (cache_hits / total_requests) * 100

            # Should be > 95% (ideally 99% with first miss)
            assert hit_rate >= 95, f"Cache hit rate {hit_rate:.1f}% is below 95% threshold"


class TestSignalsEndpointRateLimitProtection:
    """Validate that /api/signals endpoint doesn't abuse rate limits."""

    @pytest.mark.asyncio
    async def test_signals_endpoint_reads_from_database_only(self):
        """Test that /api/signals reads from DB and doesn't call external APIs."""
        from backend.app.api.endpoints.signals import get_signals
        from unittest.mock import AsyncMock

        # Mock request and authentication
        mock_request = MagicMock()

        # Mock Supabase client
        with patch('backend.app.db.supabase.get_supabase_client') as mock_supabase, \
             patch('backend.app.services.fetcher.fetch_ohlcv') as mock_fetch:

            # Setup mock response from database
            mock_client = MagicMock()
            mock_table = MagicMock()
            mock_select = MagicMock()
            mock_gte = MagicMock()
            mock_order = MagicMock()

            # Chain the mock calls
            mock_client.table.return_value = mock_table
            mock_table.select.return_value = mock_select
            mock_select.gte.return_value = mock_gte
            mock_gte.order.return_value = mock_order
            mock_order.execute.return_value = MagicMock(data=[
                {
                    'symbol': 'AAPL',
                    'signal_type': 'buy',
                    'strength': 0.75,
                    'price': 150.0,
                    'sma_20': 148.0,
                    'sma_50': 145.0,
                    'rsi': 65.0,
                    'created_at': datetime.now().isoformat(),
                    'timestamp': datetime.now().isoformat()
                }
            ])

            mock_supabase.return_value = mock_client

            # Call the endpoint
            result = await get_signals(mock_request, authenticated=True)

            # Verify no external API calls were made
            assert mock_fetch.call_count == 0, "Signals endpoint should not call external APIs"

            # Verify response structure
            assert 'signals' in result
            assert 'AAPL' in result['signals']
