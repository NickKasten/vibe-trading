import unittest
import pandas as pd
from bot.backtest.backtest import run_backtest

class TestBacktest(unittest.TestCase):
    def setUp(self):
        # Create sample data for testing
        self.data = pd.DataFrame({
            'Open': [100] * 100,
            'High': [105] * 100,
            'Low': [95] * 100,
            'Close': [102] * 100,
            'Volume': [1000] * 100
        }, index=pd.date_range(start='2024-01-01', periods=100, freq='D'))

    def test_backtest(self):
        # Run backtest
        stats = run_backtest(self.data)
        self.assertIsNotNone(stats)
        self.assertIn('Return [%]', stats)

if __name__ == "__main__":
    unittest.main() 