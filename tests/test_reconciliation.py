"""
Tests for reconciliation module
"""

import pytest
import pandas as pd
from shared.validation.reconciliation import Reconciliator, ReconciliationReport


class TestReconciliator:
    """Test reconciliation functionality."""

    def test_init_default_threshold(self):
        """Test default threshold initialization."""
        reconciliator = Reconciliator()
        assert reconciliator.threshold_pct == 5.0

    def test_init_custom_threshold(self):
        """Test custom threshold initialization."""
        reconciliator = Reconciliator(threshold_pct=10.0)
        assert reconciliator.threshold_pct == 10.0

    def test_no_changes(self, sample_weights_df):
        """Test reconciliation when there are no changes."""
        reconciliator = Reconciliator()
        result = reconciliator.compare_with_previous(sample_weights_df, sample_weights_df)

        assert isinstance(result, ReconciliationReport)
        assert len(result.alerts) == 0
        assert len(result.new_components) == 0
        assert len(result.removed_components) == 0
        assert not result.changes.empty
        assert 'Change_Abs' in result.changes.columns

    def test_significant_weight_change(self, sample_weights_df):
        """Test detection of significant weight changes."""
        current = sample_weights_df.copy()
        previous = sample_weights_df.copy()

        # Change one weight significantly (more than 5%)
        previous.loc[previous['Benchmark ID'] == 'LSE80_I01270', 'Weight'] = 1.0

        reconciliator = Reconciliator(threshold_pct=5.0)
        result = reconciliator.compare_with_previous(current, previous)

        # Should have 1 alert for significant change
        assert len(result.alerts) >= 1
        assert any('LSE80_I01270' in alert for alert in result.alerts)

    def test_new_component_detection(self, sample_weights_df):
        """Test detection of new components."""
        current = sample_weights_df.copy()
        previous = sample_weights_df[sample_weights_df['Benchmark ID'] != 'LSE80_I01270'].copy()

        reconciliator = Reconciliator()
        result = reconciliator.compare_with_previous(current, previous)

        # LSE80_I01270 should be detected as new (went from 0 to non-zero weight)
        assert 'LSE80_I01270' in result.new_components
        assert len(result.new_components) == 1

    def test_removed_component_detection(self, sample_weights_df):
        """Test detection of removed components."""
        current = sample_weights_df[sample_weights_df['Benchmark ID'] != 'LSE80_I01270'].copy()
        previous = sample_weights_df.copy()

        reconciliator = Reconciliator()
        result = reconciliator.compare_with_previous(current, previous)

        # LSE80_I01270 should be detected as removed (went from non-zero to 0 weight)
        assert 'LSE80_I01270' in result.removed_components
        assert len(result.removed_components) == 1

    def test_zero_weight_components_ignored(self, sample_weights_df):
        """Test that components with 0 weight in both periods are not flagged."""
        current = sample_weights_df.copy()
        previous = sample_weights_df.copy()

        # Add a component with 0 weight in both
        new_row = current.iloc[0].copy()
        new_row['Benchmark ID'] = 'LSE80_ZERO'
        new_row['Weight'] = 0.0

        current = pd.concat([current, pd.DataFrame([new_row])], ignore_index=True)
        previous = pd.concat([previous, pd.DataFrame([new_row])], ignore_index=True)

        reconciliator = Reconciliator()
        result = reconciliator.compare_with_previous(current, previous)

        # LSE80_ZERO should NOT be in new or removed components
        assert 'LSE80_ZERO' not in result.new_components
        assert 'LSE80_ZERO' not in result.removed_components

    def test_changes_sorted_by_absolute_change(self, sample_weights_df):
        """Test that changes are sorted by absolute change."""
        current = sample_weights_df.copy()
        previous = sample_weights_df.copy()

        # Make different sized changes
        previous.loc[0, 'Weight'] = 18.0  # 1.25% change
        previous.loc[1, 'Weight'] = 15.0  # 4.25% change
        previous.loc[2, 'Weight'] = 10.0  # 9.25% change

        reconciliator = Reconciliator(threshold_pct=0.0)  # Catch all changes
        result = reconciliator.compare_with_previous(current, previous)

        # First row should have largest absolute change
        assert result.changes.iloc[0]['Change_Abs'] >= result.changes.iloc[1]['Change_Abs']
        assert result.changes.iloc[1]['Change_Abs'] >= result.changes.iloc[2]['Change_Abs']

    def test_change_abs_column_exists(self, sample_weights_df):
        """Test that Change_Abs column is included in output."""
        current = sample_weights_df.copy()
        previous = sample_weights_df.copy()
        previous.loc[0, 'Weight'] = 18.0

        reconciliator = Reconciliator()
        result = reconciliator.compare_with_previous(current, previous)

        # Verify Change_Abs column exists and can be accessed
        assert 'Change_Abs' in result.changes.columns
        assert not result.changes['Change_Abs'].isna().any()
