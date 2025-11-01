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

        result_text = f"Validation Report for {fund} on {date}\n\n"

        # Check each portfolio if multiple exist
        if 'Portfolio' in df.columns:
            portfolios = df['Portfolio'].unique()
            for portfolio in portfolios:
                portfolio_df = df[df['Portfolio'] == portfolio]
                validation_result = validator.validate(portfolio_df, portfolio)

                result_text += f"Portfolio: {portfolio}\n"
                result_text += f"Status: {'PASSED' if validation_result.is_valid else 'FAILED'}\n"

                if validation_result.errors:
                    result_text += "Errors:\n"
                    for error in validation_result.errors:
                        result_text += f"  - {error}\n"

                if validation_result.warnings:
                    result_text += "Warnings:\n"
                    for warning in validation_result.warnings:
                        result_text += f"  - {warning}\n"

                result_text += f"Metrics:\n"
                for key, value in validation_result.metrics.items():
                    result_text += f"  - {key}: {value}\n"
                result_text += "\n"
        else:
            validation_result = validator.validate(df, fund)
            result_text += f"Status: {'PASSED' if validation_result.is_valid else 'FAILED'}\n\n"

            if validation_result.errors:
                result_text += "Errors:\n"
                for error in validation_result.errors:
                    result_text += f"  - {error}\n"

            if validation_result.warnings:
                result_text += "Warnings:\n"
                for warning in validation_result.warnings:
                    result_text += f"  - {warning}\n"

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
