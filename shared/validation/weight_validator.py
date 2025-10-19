"""
Weight Validator
Validates fund weights for UCITS compliance and sum checks
"""

from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import yaml


@dataclass
class ValidationResult:
    """Result of weight validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metrics: Dict


class WeightValidator:
    """Validator for fund weight calculations."""

    def __init__(self, config: dict):
        """
        Initialize validator with configuration.

        Args:
            config: Dictionary with validation rules
        """
        # UCITS cap is required - no default (each fund must specify)
        if 'ucits_cap' not in config:
            raise ValueError(
                "ucits_cap must be specified in fund configuration. "
                "Add it to fund_overrides in config/validation_rules.yaml"
            )
        self.ucits_cap = config['ucits_cap']
        self.sum_tolerance_pct = config.get('sum_tolerance_pct', 0.01)
        self.sum_tolerance_abs = config.get('sum_tolerance_abs', 0.0001)

    def validate(self, df: pd.DataFrame, portfolio_type: str) -> ValidationResult:
        """
        Run all weight validation checks.

        Args:
            df: DataFrame with weight data
            portfolio_type: Portfolio name (e.g., 'LSE80')

        Returns:
            ValidationResult with pass/fail status and details
        """
        errors = []
        warnings = []

        # Check 1: Sum validation
        total_weight = df['Weight'].sum()
        if abs(total_weight - 100.0) > self.sum_tolerance_abs:
            errors.append(
                f"{portfolio_type}: Weight sum {total_weight:.9f}% != 100% "
                f"(tolerance: ±{self.sum_tolerance_abs}%)"
            )

        # Check 2: UCITS cap
        max_weight = df['Weight'].max()
        if max_weight > self.ucits_cap + self.sum_tolerance_abs:
            violators = df[df['Weight'] > self.ucits_cap + self.sum_tolerance_abs]
            errors.append(
                f"{portfolio_type}: UCITS violation - {len(violators)} positions exceed "
                f"{self.ucits_cap}%: {violators['Benchmark ID'].tolist() if 'Benchmark ID' in df.columns else violators['Symbol'].tolist()}"
            )

        # Check 3: Negative weights
        if (df['Weight'] < 0).any():
            neg_positions = df[df['Weight'] < 0]
            col_name = 'Benchmark ID' if 'Benchmark ID' in df.columns else 'Symbol'
            errors.append(
                f"{portfolio_type}: Negative weights found: {neg_positions[col_name].tolist()}"
            )

        # Check 4: Missing weights
        if df['Weight'].isnull().any():
            missing = df[df['Weight'].isnull()]
            col_name = 'Benchmark ID' if 'Benchmark ID' in df.columns else 'Symbol'
            errors.append(
                f"{portfolio_type}: Missing weights for: {missing[col_name].tolist()}"
            )

        # Warnings: positions close to cap
        close_to_cap = df[(df['Weight'] > self.ucits_cap - 0.5) & (df['Weight'] <= self.ucits_cap)]
        if not close_to_cap.empty:
            col_name = 'Benchmark ID' if 'Benchmark ID' in df.columns else 'Symbol'
            warnings.append(
                f"{portfolio_type}: Positions within 0.5% of UCITS cap: {close_to_cap[col_name].tolist()}"
            )

        metrics = {
            'total_weight': total_weight,
            'max_weight': max_weight,
            'num_positions': len(df),
            'num_negative': (df['Weight'] < 0).sum(),
            'num_missing': df['Weight'].isnull().sum()
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics
        )
