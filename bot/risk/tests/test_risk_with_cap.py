"""
Comprehensive tests for risk calculator with position cap and buying power validation.
Tests the updated risk.py implementation.
"""

import unittest
import sys
sys.path.insert(0, '/Users/nick/Desktop/Summer2025Projects/vibe-trading')

from bot.risk.risk import calculate_position_size, validate_buying_power, MAX_POSITION_PCT


class TestRiskWithCap(unittest.TestCase):
    """Test position sizing with 30% cap"""

    def test_standard_account_cap_applied(self):
        """Test that cap is applied for standard account"""
        signals = {'signal': 1}
        current_equity = 100000
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        self.assertIn('position_size', result)
        self.assertTrue(result['cap_applied'], "Cap should be applied")

        # Verify position is capped at 30% of equity
        max_allowed = current_equity * MAX_POSITION_PCT
        self.assertLessEqual(result['actual_investment'], max_allowed)
        self.assertAlmostEqual(result['equity_pct'], 0.30, delta=0.01)

        # Verify 3 positions would be ~90% of equity
        total_if_3 = result['actual_investment'] * 3
        self.assertLess(total_if_3, current_equity)  # Less than 100%
        self.assertGreater(total_if_3, current_equity * 0.85)  # But > 85%

    def test_small_account_cap_applied(self):
        """Test cap with small account"""
        signals = {'signal': 1}
        current_equity = 10000
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        self.assertTrue(result['cap_applied'])

        # Verify ~30% of equity
        expected_investment = current_equity * 0.30
        self.assertAlmostEqual(result['actual_investment'], expected_investment, delta=200)

    def test_expensive_stock_cap_applied(self):
        """Test with expensive stock (TSLA @ $350)"""
        signals = {'signal': 1}
        current_equity = 100000
        open_positions = 0
        current_price = 350.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        self.assertTrue(result['cap_applied'])

        # Position should be capped at 30% of equity
        max_allowed = current_equity * MAX_POSITION_PCT
        self.assertLessEqual(result['actual_investment'], max_allowed)

        # Verify shares calculation
        expected_shares = int(max_allowed / current_price)
        self.assertEqual(result['position_size'], expected_shares)

    def test_cheap_stock_cap_applied(self):
        """Test with cheap stock"""
        signals = {'signal': 1}
        current_equity = 10000
        open_positions = 0
        current_price = 5.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        self.assertTrue(result['cap_applied'])

        # Should still be capped at 30%
        max_allowed = current_equity * MAX_POSITION_PCT
        self.assertLessEqual(result['actual_investment'], max_allowed)

    def test_three_positions_safe(self):
        """Test that 3 simultaneous positions stay within buying power"""
        signals = {'signal': 1}
        current_equity = 100000
        current_price = 180.00

        # Simulate opening 3 positions
        positions = []
        for i in range(3):
            result = calculate_position_size(signals, current_equity, i, current_price)
            self.assertIsNotNone(result, f"Position {i+1} should be allowed")
            positions.append(result)

        # Calculate total exposure
        total_investment = sum(p['actual_investment'] for p in positions)

        # Should be ~90% of equity (3 × 30%)
        self.assertLess(total_investment, current_equity)
        self.assertGreater(total_investment, current_equity * 0.85)

        print(f"\n3 Position Test:")
        print(f"  Total investment: ${total_investment:,.2f}")
        print(f"  Percentage of equity: {total_investment/current_equity*100:.1f}%")
        print(f"  Within overnight buying power: {total_investment < current_equity}")

    def test_max_positions_rejected(self):
        """Test that 4th position is rejected"""
        signals = {'signal': 1}
        current_equity = 100000
        open_positions = 3  # Already at max
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNone(result, "Should reject when at max positions")

    def test_no_signal_rejected(self):
        """Test that no signal returns None"""
        signals = {'signal': 0}
        current_equity = 100000
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNone(result)

    def test_result_metadata(self):
        """Test that result contains all expected fields"""
        signals = {'signal': 1}
        current_equity = 100000
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        # Verify all expected fields
        required_fields = [
            'position_size', 'risk_per_trade', 'stop_loss_pct',
            'max_investment', 'actual_investment', 'current_price',
            'cap_applied', 'equity_pct'
        ]
        for field in required_fields:
            self.assertIn(field, result, f"Missing field: {field}")

        # Verify types
        self.assertIsInstance(result['position_size'], int)
        self.assertIsInstance(result['cap_applied'], bool)
        self.assertIsInstance(result['equity_pct'], float)


class TestBuyingPowerValidation(unittest.TestCase):
    """Test buying power validation function"""

    def test_safe_position(self):
        """Test position that's safe"""
        equity = 100000
        proposed_investment = 30000  # 30% - should be safe
        open_positions = 0

        is_valid, error_msg = validate_buying_power(equity, proposed_investment, open_positions)

        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")

    def test_unsafe_position(self):
        """Test position that would exceed limits"""
        equity = 100000
        proposed_investment = 50000  # 50% - too high (3 × 50% = 150%)
        open_positions = 0

        is_valid, error_msg = validate_buying_power(equity, proposed_investment, open_positions)

        self.assertFalse(is_valid)
        self.assertIn("buying power", error_msg.lower())

    def test_edge_case_exactly_30_percent(self):
        """Test position at exactly 30%"""
        equity = 100000
        proposed_investment = 30000  # Exactly 30%
        open_positions = 0

        is_valid, error_msg = validate_buying_power(equity, proposed_investment, open_positions)

        self.assertTrue(is_valid)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def test_very_small_equity(self):
        """Test with very small account"""
        signals = {'signal': 1}
        current_equity = 1000  # $1K account
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        # Should still respect 30% cap
        self.assertLessEqual(result['actual_investment'], current_equity * 0.30)

    def test_very_expensive_stock(self):
        """Test with very expensive stock"""
        signals = {'signal': 1}
        current_equity = 100000
        open_positions = 0
        current_price = 5000.00  # Very expensive stock

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        # Should be able to buy at least 1 share
        self.assertGreaterEqual(result['position_size'], 1)

    def test_large_account(self):
        """Test with large account"""
        signals = {'signal': 1}
        current_equity = 1000000  # $1M account
        open_positions = 0
        current_price = 180.00

        result = calculate_position_size(signals, current_equity, open_positions, current_price)

        self.assertIsNotNone(result)
        self.assertTrue(result['cap_applied'])

        # Should still be capped at 30%
        expected_max = current_equity * 0.30
        self.assertLessEqual(result['actual_investment'], expected_max)


class TestRiskCalculations(unittest.TestCase):
    """Test risk calculation accuracy"""

    def test_risk_per_trade_2_percent(self):
        """Test that risk per trade is always 2% of equity"""
        test_cases = [
            (10000, 200),    # $10K → $200 risk
            (100000, 2000),  # $100K → $2K risk
            (500000, 10000), # $500K → $10K risk
        ]

        for equity, expected_risk in test_cases:
            signals = {'signal': 1}
            result = calculate_position_size(signals, equity, 0, 100.00)
            self.assertAlmostEqual(result['risk_per_trade'], expected_risk, delta=1)

    def test_stop_loss_5_percent(self):
        """Test that stop loss is always 5%"""
        signals = {'signal': 1}
        result = calculate_position_size(signals, 100000, 0, 100.00)

        self.assertEqual(result['stop_loss_pct'], 0.05)


def run_comprehensive_demo():
    """Run a comprehensive demo showing the improvements"""
    print("\n" + "="*80)
    print("RISK CALCULATOR - AFTER FIX DEMONSTRATION")
    print("="*80)

    test_cases = [
        ("Standard Account - AAPL", 100000, 180.00),
        ("Standard Account - TSLA", 100000, 350.00),
        ("Small Account - AAPL", 10000, 180.00),
        ("Large Account - TSLA", 500000, 350.00),
    ]

    for name, equity, price in test_cases:
        print(f"\n{name}:")
        print(f"  Equity: ${equity:,.2f}, Price: ${price:.2f}")

        signals = {'signal': 1}
        result = calculate_position_size(signals, equity, 0, price)

        if result:
            print(f"  Position: {result['position_size']:,} shares = ${result['actual_investment']:,.2f}")
            print(f"  Equity %: {result['equity_pct']*100:.1f}%")
            print(f"  Cap applied: {result['cap_applied']}")
            print(f"  3 positions total: ${result['actual_investment']*3:,.2f} ({result['equity_pct']*3*100:.1f}% of equity)")

    print("\n" + "="*80)
    print("CONCLUSION: All positions now capped at 30% for safe trading!")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Run demo first
    run_comprehensive_demo()

    # Then run unit tests
    unittest.main(verbosity=2)
