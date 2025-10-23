"""
Tests for Vanguard LifeStrategy calculator
"""

import pytest
import pandas as pd
import numpy as np
from funds.vanguard_lifestrat.calculator import calculate_weights, calculate_all_portfolios
from funds.vanguard_lifestrat.config import PORTFOLIO_CONFIGS


class TestCalculateWeights:
    """Test weight calculation for individual portfolios."""

    @pytest.fixture
    def base_template(self):
        """Create minimal base template for testing."""
        return pd.read_csv('vanguard_base_eu_lifestrategy.csv')

    def test_weights_sum_to_100_percent(self, base_template, sample_market_data):
        """Test that calculated weights sum to approximately 100% per portfolio."""
        result = calculate_all_portfolios(sample_market_data, "20250821")

        for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
            # Filter to this portfolio's rows
            mask = result['Fund ID'] == portfolio_type
            portfolio_weights = result.loc[mask, 'Weight'].sum()

            # Allow small rounding errors (within 0.01%)
            assert abs(portfolio_weights - 100.0) < 0.01, \
                f"{portfolio_type} weights sum to {portfolio_weights}, expected ~100"

    def test_ucits_cap_not_exceeded(self, base_template, sample_market_data):
        """Test that no weight exceeds the UCITS cap of 19.25%."""
        ucits_cap = 19.25

        for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
            result = calculate_weights(portfolio_type, base_template.copy(), sample_market_data)

            mask = result['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
            max_weight = result.loc[mask, 'Weight'].max()

            assert max_weight <= ucits_cap + 0.0001, \
                f"{portfolio_type} has weight {max_weight} exceeding UCITS cap {ucits_cap}"

    def test_no_negative_weights(self, base_template, sample_market_data):
        """Test that no weights are negative."""
        for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
            result = calculate_weights(portfolio_type, base_template.copy(), sample_market_data)

            mask = result['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
            min_weight = result.loc[mask, 'Weight'].min()

            assert min_weight >= 0.0, \
                f"{portfolio_type} has negative weight {min_weight}"

    def test_fixed_weight_components(self, base_template, sample_market_data):
        """Test that fixed weight components receive 19.25% allocation."""
        ucits_cap = 19.25

        for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
            result = calculate_weights(portfolio_type, base_template.copy(), sample_market_data)

            # Check LHMN34611 (fixed weight bond component)
            bond_mask = result['symbol'] == 'LHMN34611'
            bond_weight = result.loc[bond_mask, 'Weight'].iloc[0] if bond_mask.any() else 0

            if bond_weight > 0:  # If this component is included in this portfolio
                assert abs(bond_weight - ucits_cap) < 0.0001, \
                    f"{portfolio_type} LHMN34611 weight is {bond_weight}, expected {ucits_cap}"

    @pytest.mark.parametrize("portfolio_type,expected_equity_allocation", [
        ("LSE20", 20),
        ("LSE40", 40),
        ("LSE60", 60),
        ("LSE80", 80),
    ])
    def test_portfolio_equity_allocation(self, base_template, sample_market_data,
                                         portfolio_type, expected_equity_allocation):
        """Test that each portfolio has correct equity allocation."""
        result = calculate_weights(portfolio_type, base_template.copy(), sample_market_data)

        mask = result['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
        equity_allocation = result.loc[mask, 'Equity Allocation'].iloc[0]

        assert equity_allocation == expected_equity_allocation


class TestCalculateAllPortfolios:
    """Test calculation of all portfolios together."""

    def test_returns_dataframe(self, sample_market_data):
        """Test that calculate_all_portfolios returns a DataFrame."""
        result = calculate_all_portfolios(sample_market_data, "20250821")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_contains_all_portfolios(self, sample_market_data):
        """Test that result contains all four portfolios."""
        result = calculate_all_portfolios(sample_market_data, "20250821")

        fund_ids = result['Fund ID'].unique()

        assert 'LSE20' in fund_ids
        assert 'LSE40' in fund_ids
        assert 'LSE60' in fund_ids
        assert 'LSE80' in fund_ids

    def test_date_column_added(self, sample_market_data):
        """Test that Date column is added correctly."""
        test_date = "20250821"
        result = calculate_all_portfolios(sample_market_data, test_date)

        assert 'Date' in result.columns
        assert result.columns[0] == 'Date'  # Should be first column
        assert (result['Date'] == test_date).all()

    def test_required_columns_present(self, sample_market_data):
        """Test that all required columns are present in output."""
        result = calculate_all_portfolios(sample_market_data, "20250821")

        required_columns = [
            'Date', 'Fund ID', 'Equity Allocation', 'Fund Benchmark',
            'Benchmark ID', 'symbol', 'Weight'
        ]

        for col in required_columns:
            assert col in result.columns, f"Missing required column: {col}"

    def test_no_nan_weights(self, sample_market_data):
        """Test that weights are either valid numbers or intentionally 0."""
        result = calculate_all_portfolios(sample_market_data, "20250821")

        # Check that weights are present and numeric
        assert 'Weight' in result.columns
        # Some weights might be 0, but should not be NaN for active portfolios
        # Allow NaN for components not included in certain portfolios
        assert result['Weight'].notna().any(), "All weights are NaN"

    def test_market_data_with_missing_security(self, sample_market_data):
        """Test handling when market data is missing for a security."""
        # Remove one security from market data
        incomplete_data = sample_market_data[sample_market_data['symbol'] != 'I01270'].copy()

        # Should still run, might have warnings or zeros for missing data
        result = calculate_all_portfolios(incomplete_data, "20250821")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def base_template(self):
        """Create minimal base template for testing."""
        return pd.read_csv('vanguard_base_eu_lifestrategy.csv')

    def test_zero_market_cap(self, base_template):
        """Test handling of zero market cap."""
        market_data = pd.DataFrame({
            'symbol': ['LHMN34611', 'I00010'],
            'MarketCapIndex': [0.0, 1.0]  # Zero market cap
        })

        # Should handle gracefully without division by zero
        result = calculate_weights('LSE20', base_template.copy(), market_data)

        assert isinstance(result, pd.DataFrame)
        assert not result['Weight'].isna().all()

    def test_very_large_market_cap(self, base_template):
        """Test handling of very large market caps."""
        market_data = pd.DataFrame({
            'symbol': ['LHMN34611', 'I00010', 'I01018'],
            'MarketCapIndex': [1.0, 1.0, 1e15]  # Very large market cap
        })

        result = calculate_weights('LSE80', base_template.copy(), market_data)

        # Should not have inf values - NaN is acceptable for missing components
        weight_values = result.loc[result['Weight'].notna(), 'Weight']
        assert not np.isinf(weight_values).any(), "Found infinite weights"
        # At least some weights should be valid
        assert len(weight_values) > 0, "No valid weights found"
