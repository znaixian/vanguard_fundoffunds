"""
Validation Tools

Tools for validating fund calculations against UCITS and other rules.
"""

import os
from typing import Any, Dict
from pathlib import Path
import pandas as pd

# Project paths
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', os.getcwd()))
OUTPUT_DIR = PROJECT_ROOT / os.getenv('OUTPUT_DIR', 'output')


def validate_weights(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run validation checks on calculated weights.

    Args:
        args: Dictionary containing:
            - fund: Fund name
            - date: Date in YYYYMMDD format

    Returns:
        Validation report with errors, warnings, and metrics
    """
    try:
        from shared.validation.weight_validator import WeightValidator
        from shared.utils.config_loader import ConfigLoader

        fund = args["fund"]
        date = args["date"]

        # Read weights
        output_file = OUTPUT_DIR / fund / date / f"{fund}_{date}_latest.csv"
        if not output_file.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"No data found for {fund} on {date}"
                }],
                "is_error": True
            }

        df = pd.read_csv(output_file)

        # Load validation config
        config_loader = ConfigLoader()
        config = config_loader.load('config/validation_rules.yaml')
        fund_config = config.get('fund_overrides', {}).get(fund, {})
        merged_config = {**config.get('global', {}), **fund_config}

        # Run validation
        validator = WeightValidator(merged_config)

        result_text = f"Validation Report for {fund} on {date}\n"
        result_text += "=" * 70 + "\n\n"

        # Check if this is a multi-portfolio fund (check for Benchmark ID format like LSE80_)
        portfolios = []
        if 'Benchmark ID' in df.columns:
            # Extract portfolio identifiers from Benchmark ID (e.g., LSE80_, LSE60_)
            portfolio_ids = df['Benchmark ID'].str.extract(r'^(LSE\d+)_')[0].unique()
            portfolio_ids = [p for p in portfolio_ids if pd.notna(p)]
            if portfolio_ids:
                portfolios = sorted(portfolio_ids)

        # Validate each portfolio separately
        if portfolios:
            overall_status = "PASSED"
            for portfolio in portfolios:
                # Filter to this portfolio
                portfolio_df = df[df['Benchmark ID'].str.contains(f'{portfolio}_', na=False)]

                if portfolio_df.empty:
                    continue

                validation_result = validator.validate(portfolio_df, portfolio)

                # Update overall status
                if not validation_result.is_valid:
                    overall_status = "FAILED"

                # Format portfolio result
                result_text += f"Portfolio: {portfolio}\n"
                result_text += f"  Status: {'✓ PASSED' if validation_result.is_valid else '✗ FAILED'}\n"
                result_text += f"  Total Weight: {validation_result.metrics.get('total_weight', 0):.9f}%\n"
                result_text += f"  Max Weight: {validation_result.metrics.get('max_weight', 0):.9f}%\n"
                result_text += f"  Positions: {validation_result.metrics.get('num_positions', 0)}\n"

                if validation_result.errors:
                    result_text += "\n  Errors:\n"
                    for error in validation_result.errors:
                        result_text += f"    ✗ {error}\n"

                if validation_result.warnings:
                    result_text += "\n  Warnings:\n"
                    for warning in validation_result.warnings:
                        # Don't show warnings for positions at exactly 19.25% (UCITS cap)
                        # These are intended to be at the cap, not a warning
                        if "within 0.5% of UCITS cap" in warning:
                            # Extract the positions from warning
                            import re
                            match = re.search(r'\[(.*?)\]', warning)
                            if match:
                                positions_str = match.group(1)
                                # Check if any positions are not exactly at cap
                                positions = [p.strip().strip("'\"") for p in positions_str.split(',')]
                                non_cap_positions = []
                                for pos in positions:
                                    pos_df = portfolio_df[portfolio_df['Benchmark ID'] == pos]
                                    if not pos_df.empty:
                                        weight = pos_df['Weight'].iloc[0]
                                        # Only warn if not exactly at 19.25%
                                        if abs(weight - 19.25) > 0.0001:
                                            non_cap_positions.append(pos)

                                if non_cap_positions:
                                    result_text += f"    ⚠ Positions close to UCITS cap (19.25%): {non_cap_positions}\n"
                        else:
                            result_text += f"    ⚠ {warning}\n"

                result_text += "\n"

            result_text += f"\nOverall Status: {'✓ ALL PORTFOLIOS PASSED' if overall_status == 'PASSED' else '✗ SOME PORTFOLIOS FAILED'}\n"
            result_text += f"Total Portfolios Checked: {len(portfolios)}\n"

        else:
            # Single portfolio validation
            validation_result = validator.validate(df, fund)
            result_text += f"Status: {'✓ PASSED' if validation_result.is_valid else '✗ FAILED'}\n\n"

            if validation_result.errors:
                result_text += "Errors:\n"
                for error in validation_result.errors:
                    result_text += f"  ✗ {error}\n"

            if validation_result.warnings:
                result_text += "\nWarnings:\n"
                for warning in validation_result.warnings:
                    result_text += f"  ⚠ {warning}\n"

            result_text += f"\nMetrics:\n"
            for key, value in validation_result.metrics.items():
                result_text += f"  - {key}: {value}\n"

        return {
            "content": [{"type": "text", "text": result_text}]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error validating weights: {str(e)}"}],
            "is_error": True
        }
