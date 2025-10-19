"""
Tests for weight validator
"""

import pytest
import pandas as pd
from shared.validation.weight_validator import WeightValidator, ValidationResult


class TestWeightValidator:
    """Test weight validation functionality."""

    @pytest.fixture
    def validator_config(self):
        """Create validator configuration dictionary."""
        return {
            'ucits_cap': 19.25,
            'sum_tolerance_pct': 0.01,
            'sum_tolerance_abs': 0.0001
        }

    def test_init(self, validator_config):
        """Test validator initialization."""
        validator = WeightValidator(validator_config)
        assert validator.ucits_cap == 19.25
        assert validator.sum_tolerance_abs == 0.0001

    def test_validate_all_pass(self, sample_weights_df, validator_config):
        """Test validation when all checks pass."""
        validator = WeightValidator(validator_config)
        result = validator.validate(sample_weights_df, 'LSE80')

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_ucits_cap_violation(self, sample_weights_df, validator_config):
        """Test detection of UCITS cap violation."""
        df = sample_weights_df.copy()
        # Violate UCITS cap
        df.loc[0, 'Weight'] = 20.0

        validator = WeightValidator(validator_config)
        result = validator.validate(df, 'LSE80')

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any('UCITS' in error for error in result.errors)

    def test_ucits_warning_threshold(self, sample_weights_df, validator_config):
        """Test UCITS warning threshold detection."""
        df = sample_weights_df.copy()
        # Set weight close to cap (within 0.5%) and adjust another to maintain sum=100
        original_weight = df.loc[0, 'Weight']
        df.loc[0, 'Weight'] = 18.9
        # Adjust another weight to keep sum at 100
        df.loc[1, 'Weight'] = df.loc[1, 'Weight'] + (original_weight - 18.9)

        validator = WeightValidator(validator_config)
        result = validator.validate(df, 'LSE80')

        # Should be valid (just a warning)
        assert len(result.warnings) > 0

    def test_weights_sum_to_100(self, sample_weights_df, validator_config):
        """Test that weights sum to approximately 100% per fund."""
        validator = WeightValidator(validator_config)
        result = validator.validate(sample_weights_df, 'LSE80')

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True  # Sample data sums to 100

    def test_negative_weights_invalid(self, sample_weights_df, validator_config):
        """Test that negative weights are detected as invalid."""
        df = sample_weights_df.copy()
        df.loc[0, 'Weight'] = -1.0

        validator = WeightValidator(validator_config)
        result = validator.validate(df, 'LSE80')

        # Negative weights should be invalid
        assert result.is_valid is False
        assert any('Negative' in error for error in result.errors)

    def test_multiple_violations(self, sample_weights_df, validator_config):
        """Test detection of multiple validation issues."""
        df = sample_weights_df.copy()
        # Create multiple violations
        df.loc[0, 'Weight'] = 20.0  # UCITS violation
        df.loc[1, 'Weight'] = 20.5  # Another UCITS violation

        validator = WeightValidator(validator_config)
        result = validator.validate(df, 'LSE80')

        assert result.is_valid is False
        assert len(result.errors) >= 1  # At least UCITS violation

    @pytest.mark.parametrize("weight,should_warn", [
        (19.25, False),   # At cap, no warning
        (19.0, True),     # Within threshold, should warn
        (18.5, False),    # Outside threshold, no warning
        (18.8, True),     # Within threshold, should warn
    ])
    def test_warning_threshold_parametrized(self, sample_weights_df, validator_config, weight, should_warn):
        """Test warning threshold with various weights."""
        df = sample_weights_df.copy()
        # Change one weight to test value
        df.loc[0, 'Weight'] = weight

        validator = WeightValidator(validator_config)
        result = validator.validate(df, 'LSE80')

        if should_warn:
            assert len(result.warnings) > 0
            assert any('UCITS cap' in warning for warning in result.warnings)
