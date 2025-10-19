"""
Reconciliation Module
Compares current weights with previous day for change detection
"""

from dataclasses import dataclass
from typing import List
import pandas as pd


@dataclass
class ReconciliationReport:
    """Result of reconciliation comparison."""
    alerts: List[str]
    changes: pd.DataFrame
    new_components: List[str]
    removed_components: List[str]


class Reconciliator:
    """Reconciles current weights with previous day."""

    def __init__(self, threshold_pct: float = 5.0):
        """
        Initialize reconciliator.

        Args:
            threshold_pct: Alert threshold for weight changes (absolute %)
        """
        self.threshold_pct = threshold_pct

    def compare_with_previous(
        self,
        current: pd.DataFrame,
        previous: pd.DataFrame
    ) -> ReconciliationReport:
        """
        Compare current weights with previous day.

        Args:
            current: Current day DataFrame
            previous: Previous day DataFrame

        Returns:
            ReconciliationReport with list of changes and alerts
        """
        alerts = []

        # Determine column name to use
        id_col = 'Benchmark ID' if 'Benchmark ID' in current.columns else 'Symbol'

        # Merge current and previous
        merged = current.merge(
            previous[[id_col, 'Weight']],
            on=id_col,
            how='outer',
            suffixes=('_current', '_previous')
        )

        # Fill NaN for new/removed components
        merged['Weight_current'] = merged['Weight_current'].fillna(0)
        merged['Weight_previous'] = merged['Weight_previous'].fillna(0)

        # Calculate changes
        merged['Change'] = merged['Weight_current'] - merged['Weight_previous']
        merged['Change_Abs'] = merged['Change'].abs()

        # Identify new/removed components
        # New: had 0 weight previously, now has non-zero weight
        new_components = merged[(merged['Weight_previous'] == 0) & (merged['Weight_current'] > 0)][id_col].tolist()
        # Removed: had non-zero weight previously, now has 0 weight
        removed_components = merged[(merged['Weight_previous'] > 0) & (merged['Weight_current'] == 0)][id_col].tolist()

        # Find significant changes
        significant = merged[merged['Change_Abs'] > self.threshold_pct]

        # Generate alerts
        if not significant.empty:
            for _, row in significant.iterrows():
                alerts.append(
                    f"{row[id_col]}: {row['Weight_previous']:.2f}% → {row['Weight_current']:.2f}% "
                    f"(Δ{row['Change']:+.2f}pp)"
                )

        if new_components:
            alerts.append(f"New components added: {new_components}")

        if removed_components:
            alerts.append(f"Components removed: {removed_components}")

        changes_df = merged[[id_col, 'Weight_previous', 'Weight_current', 'Change', 'Change_Abs']].copy()
        changes_df = changes_df.sort_values('Change_Abs', ascending=False)

        return ReconciliationReport(
            alerts=alerts,
            changes=changes_df,
            new_components=new_components,
            removed_components=removed_components
        )
