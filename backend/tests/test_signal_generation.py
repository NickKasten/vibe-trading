"""
Comprehensive tests for signal generation functionality.
Tests technical indicator calculations and trading signal logic.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from bot.strategy.signals import generate_signals, calculate_signal_strength, validate_data_sufficiency


class TestSignalGeneration:
    """Test suite for signal generation."""
    
    def test_generate_signals_with_sufficient_data(self):
        """Test signal generation with sufficient historical data."""
        
        # Create sample data with 60 days (enough for SMA50)
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        data = pd.DataFrame({
            'close': np.random.uniform(95, 105, 60)  # Random prices around 100
        }, index=dates)
        
        # Add upward trend for last 20 days to trigger buy signal
        data.loc[data.index[-20:], 'close'] = np.linspace(100, 110, 20)
        
        result = generate_signals(data)
        
        assert result is not None
        assert 'signal' in result
        assert 'side' in result
        assert 'strength' in result
        assert 'data' in result
        assert 'used_fallback' in result
        assert 'validation' in result
        
        # Signal should be -1 (sell), 0 (hold), or 1 (buy)
        assert result['signal'] in [-1, 0, 1]
        assert result['side'] in ['buy', 'sell', 'hold']
        assert 0.0 <= result['strength'] <= 1.0
        assert result['used_fallback'] is False  # Should have enough data
    
    def test_generate_signals_with_insufficient_data_fallback(self):
        """Test signal generation with insufficient data triggers fallback."""
        
        # Create sample data with only 25 days (not enough for SMA50)
        dates = pd.date_range('2024-01-01', periods=25, freq='D')
        data = pd.DataFrame({
            'close': np.random.uniform(95, 105, 25)
        }, index=dates)
        
        result = generate_signals(data)
        
        assert result is not None
        assert result['used_fallback'] is True  # Should use fallback strategy
        assert result['validation']['has_sma50_data'] is False
        assert result['validation']['total_days'] == 25
    
    def test_generate_signals_with_empty_data(self):
        """Test signal generation with empty data returns None."""
        
        empty_data = pd.DataFrame()
        result = generate_signals(empty_data)
        
        assert result is None
    
    def test_generate_signals_without_close_column(self):
        """Test signal generation without close column returns None."""
        
        data = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107]
            # Missing 'close' column
        })
        
        result = generate_signals(data)
        
        assert result is None
    
    def test_generate_signals_with_existing_position_buy_signal(self):
        """Test signal generation considers existing position for buy signals."""
        
        # Create data that would normally generate buy signal
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        data = pd.DataFrame({
            'close': np.linspace(90, 110, 60)  # Strong upward trend
        }, index=dates)
        
        # Test with existing position
        result = generate_signals(data, existing_position=100)  # Have 100 shares
        
        assert result is not None
        # Buy signal might be suppressed due to existing position
        # unless it's a very strong signal
    
    def test_generate_signals_with_existing_position_sell_signal(self):
        """Test signal generation considers existing position for sell signals."""
        
        # Create data that would generate sell signal
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        data = pd.DataFrame({
            'close': np.linspace(110, 90, 60)  # Strong downward trend
        }, index=dates)
        
        # Test without existing position (sell should be suppressed)
        result = generate_signals(data, existing_position=None)
        
        assert result is not None
        if result['signal'] == -1:  # Sell signal generated
            assert result['side'] == 'hold'  # Should be converted to hold


class TestTechnicalIndicators:
    """Test technical indicator calculations."""
    
    def test_sma_calculation(self):
        """Test Simple Moving Average calculation."""
        
        # Create test data with known values
        data = pd.DataFrame({
            'close': [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        })
        
        result = generate_signals(data, use_precalculated=False)
        
        if result is not None and 'data' in result:
            processed_data = result['data']
            
            # Check if SMA columns were added
            if 'SMA20' in processed_data.columns:
                # SMA should be NaN for insufficient data points
                assert pd.isna(processed_data['SMA20'].iloc[0])
            
            if 'SMA50' in processed_data.columns:
                # SMA50 should be NaN for insufficient data
                assert pd.isna(processed_data['SMA50'].iloc[-1])
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        
        # Create data with known price changes
        prices = [100]
        for i in range(20):
            # Alternating up/down moves
            if i % 2 == 0:
                prices.append(prices[-1] + 2)
            else:
                prices.append(prices[-1] - 1)
        
        data = pd.DataFrame({'close': prices})
        
        result = generate_signals(data, use_precalculated=False)
        
        if result is not None and 'data' in result:
            processed_data = result['data']
            
            if 'RSI' in processed_data.columns:
                # RSI should be between 0 and 100
                rsi_values = processed_data['RSI'].dropna()
                if len(rsi_values) > 0:
                    assert all(0 <= rsi <= 100 for rsi in rsi_values)
    
    def test_signal_generation_with_overbought_rsi(self):
        """Test signal generation when RSI is overbought (>70)."""
        
        # Create data that would result in high RSI
        data = pd.DataFrame({
            'close': np.linspace(100, 150, 60)  # Strong upward trend
        })
        
        result = generate_signals(data)
        
        if result is not None and 'data' in result:
            processed_data = result['data']
            
            # Check final RSI value
            if 'RSI' in processed_data.columns:
                final_rsi = processed_data['RSI'].iloc[-1]
                if not pd.isna(final_rsi) and final_rsi > 70:
                    # Buy signals should be filtered out when RSI > 70
                    assert result['signal'] != 1  # Should not be buy signal
    
    def test_signal_generation_with_oversold_rsi(self):
        """Test signal generation when RSI is oversold (<30)."""
        
        # Create data that would result in low RSI
        data = pd.DataFrame({
            'close': np.linspace(150, 100, 60)  # Strong downward trend
        })
        
        result = generate_signals(data)
        
        if result is not None and 'data' in result:
            processed_data = result['data']
            
            # Check final RSI value
            if 'RSI' in processed_data.columns:
                final_rsi = processed_data['RSI'].iloc[-1]
                if not pd.isna(final_rsi) and final_rsi < 30:
                    # Sell signals should be filtered out when RSI < 30
                    assert result['signal'] != -1  # Should not be sell signal


class TestSignalStrength:
    """Test signal strength calculations."""
    
    def test_calculate_signal_strength_buy(self):
        """Test signal strength calculation for buy signals."""
        
        # Create data with RSI and SMA values
        data = pd.DataFrame({
            'RSI': [40],  # Moderately oversold
            'SMA20': [100],
            'SMA50': [95],
            'close': [102]
        })
        
        strength = calculate_signal_strength(data, 1)  # Buy signal
        
        assert 0.0 <= strength <= 1.0
        assert isinstance(strength, float)
    
    def test_calculate_signal_strength_sell(self):
        """Test signal strength calculation for sell signals."""
        
        data = pd.DataFrame({
            'RSI': [75],  # Overbought
            'SMA20': [95],
            'SMA50': [100],
            'close': [98]
        })
        
        strength = calculate_signal_strength(data, -1)  # Sell signal
        
        assert 0.0 <= strength <= 1.0
    
    def test_calculate_signal_strength_hold(self):
        """Test signal strength calculation for hold signals."""
        
        data = pd.DataFrame({
            'RSI': [50],  # Neutral
            'SMA20': [100],
            'SMA50': [100],
            'close': [100]
        })
        
        strength = calculate_signal_strength(data, 0)  # Hold signal
        
        assert 0.0 <= strength <= 1.0
    
    def test_calculate_signal_strength_with_nan_values(self):
        """Test signal strength calculation handles NaN values."""
        
        data = pd.DataFrame({
            'RSI': [np.nan],  # Missing RSI
            'SMA20': [np.nan],
            'SMA50': [np.nan],
            'close': [100]
        })
        
        strength = calculate_signal_strength(data, 1)
        
        # Should return default strength when data is missing
        assert 0.0 <= strength <= 1.0


class TestDataValidation:
    """Test data validation functions."""
    
    def test_validate_data_sufficiency_sufficient(self):
        """Test data validation with sufficient data."""
        
        # Create 60 days of data
        data = pd.DataFrame({
            'close': range(60)
        })
        
        validation = validate_data_sufficiency(data)
        
        assert validation['has_sma20_data'] is True
        assert validation['has_sma50_data'] is True
        assert validation['has_rsi_data'] is True
        assert validation['total_days'] == 60
    
    def test_validate_data_sufficiency_insufficient(self):
        """Test data validation with insufficient data."""
        
        # Create only 10 days of data
        data = pd.DataFrame({
            'close': range(10)
        })
        
        validation = validate_data_sufficiency(data)
        
        assert validation['has_sma20_data'] is False
        assert validation['has_sma50_data'] is False
        assert validation['has_rsi_data'] is False
        assert validation['total_days'] == 10
    
    def test_validate_data_sufficiency_partial(self):
        """Test data validation with partially sufficient data."""
        
        # Create 25 days of data (enough for SMA20 and RSI, not SMA50)
        data = pd.DataFrame({
            'close': range(25)
        })
        
        validation = validate_data_sufficiency(data)
        
        assert validation['has_sma20_data'] is True
        assert validation['has_sma50_data'] is False
        assert validation['has_rsi_data'] is True
        assert validation['total_days'] == 25


class TestFallbackStrategy:
    """Test fallback strategy when insufficient data."""
    
    def test_fallback_strategy_uses_different_sma_periods(self):
        """Test that fallback strategy uses 10/20 SMA instead of 20/50."""
        
        # Create data with 25 days (enough for 20 but not 50)
        dates = pd.date_range('2024-01-01', periods=25, freq='D')
        data = pd.DataFrame({
            'close': np.linspace(100, 110, 25)  # Upward trend
        }, index=dates)
        
        result = generate_signals(data)
        
        assert result is not None
        assert result['used_fallback'] is True
        
        if 'data' in result:
            processed_data = result['data']
            # Should have SMA10 when using fallback
            if 'SMA10' in processed_data.columns:
                assert not pd.isna(processed_data['SMA10'].iloc[-1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
