"""
Single Fund Runner
Orchestrates: calculation → validation → output → reconciliation
"""

import importlib
import sys
import os
from pathlib import Path
from typing import Dict
from datetime import datetime
import pandas as pd

from shared.utils.logger import FundLogger
from shared.utils.file_handler import VersionedFileHandler
from shared.validation.weight_validator import WeightValidator, ValidationResult
from shared.validation.reconciliation import Reconciliator, ReconciliationReport
from shared.utils.config_loader import ConfigLoader


class FundRunner:
    """Runs calculation workflow for a single fund."""

    def __init__(self, fund_name: str, run_date: str, market_data: pd.DataFrame, returns_data: pd.DataFrame = None):
        """
        Initialize fund runner.

        Args:
            fund_name: Fund name (e.g., 'vanguard_lifestrat')
            run_date: Run date (YYYYMMDD)
            market_data: Market cap data
            returns_data: Returns data (optional)
        """
        self.fund_name = fund_name
        self.run_date = run_date
        self.market_data = market_data
        self.returns_data = returns_data if returns_data is not None else pd.DataFrame(columns=['symbol', 'Return'])
        self.logger = FundLogger.setup_logger(f'{fund_name}', run_date)
        self.config_loader = ConfigLoader()

        # Dynamically import fund-specific calculator and config
        module_name = f"funds.{fund_name}.calculator"
        self.calculator_module = importlib.import_module(module_name)

        config_module_name = f"funds.{fund_name}.config"
        self.fund_config_module = importlib.import_module(config_module_name)

    def run(self) -> Dict:
        """
        Execute full fund calculation workflow.

        Returns:
            Dictionary with run results
        """
        try:
            # Step 1: Calculate weights
            self.logger.info("Starting weight calculation")
            start_time = datetime.now()

            weights_df = self.calculator_module.calculate_all_portfolios(
                market_data=self.market_data,
                returns_data=self.returns_data,
                date=self.run_date
            )

            runtime = (datetime.now() - start_time).total_seconds()

            # Step 2: Validate
            self.logger.info("Validating results")
            validation_result = self._validate(weights_df)

            if not validation_result.is_valid:
                self.logger.error(f"Validation failed: {validation_result.errors}")
                return {
                    'fund': self.fund_name,
                    'status': 'FAILED',
                    'runtime': runtime,
                    'error': f"Validation errors: {'; '.join(validation_result.errors)}"
                }

            # Log warnings if any
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    self.logger.warning(warning)

            # Step 3: Reconciliation
            recon_result = self._reconcile(weights_df)

            if recon_result.alerts:
                for alert in recon_result.alerts:
                    self.logger.warning(f"Reconciliation: {alert}")

            # Step 4: Save output
            output_path = self._save_output(weights_df, runtime, validation_result)

            # Step 5: Return result summary
            return {
                'fund': self.fund_name,
                'status': 'SUCCESS',
                'runtime': runtime,
                'output_path': str(output_path),
                'warnings': validation_result.warnings + recon_result.alerts
            }

        except Exception as e:
            self.logger.exception(f"Fund calculation failed: {e}")
            return {
                'fund': self.fund_name,
                'status': 'FAILED',
                'error': str(e)
            }

    def _validate(self, df: pd.DataFrame) -> ValidationResult:
        """Run all validation checks."""
        config_path = 'config/validation_rules.yaml'
        config = self.config_loader.load(config_path)

        # Check for fund-specific overrides
        fund_config = config.get('fund_overrides', {}).get(self.fund_name, {})
        merged_config = {**config.get('global', {}), **fund_config}

        validator = WeightValidator(merged_config)

        # Validate each portfolio separately
        all_results = []

        # Group by portfolio if 'Benchmark ID' contains portfolio info
        if 'Benchmark ID' in df.columns:
            # Get portfolio types from fund's PORTFOLIO_CONFIGS
            portfolio_configs = getattr(self.fund_config_module, 'PORTFOLIO_CONFIGS', {})
            for portfolio_type in portfolio_configs.keys():
                portfolio_df = df[df['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)]
                if not portfolio_df.empty:
                    result = validator.validate(portfolio_df, portfolio_type)
                    all_results.append(result)
        else:
            # Single portfolio
            result = validator.validate(df, self.fund_name)
            all_results.append(result)

        # Combine results
        combined_errors = []
        combined_warnings = []
        for result in all_results:
            combined_errors.extend(result.errors)
            combined_warnings.extend(result.warnings)

        return ValidationResult(
            is_valid=len(combined_errors) == 0,
            errors=combined_errors,
            warnings=combined_warnings,
            metrics={}
        )

    def _reconcile(self, df: pd.DataFrame) -> ReconciliationReport:
        """Compare with previous day's results."""
        config = self.config_loader.load('config/validation_rules.yaml')

        if not config.get('global', {}).get('reconciliation', {}).get('enabled', True):
            return ReconciliationReport(
                alerts=[],
                changes=pd.DataFrame(),
                new_components=[],
                removed_components=[]
            )

        threshold = config.get('global', {}).get('reconciliation', {}).get('change_threshold_pct', 5.0)
        reconciliator = Reconciliator(threshold_pct=threshold)

        # Get previous file
        handler = VersionedFileHandler('output')
        previous_df = handler.get_previous_run(self.fund_name, self.run_date)

        if previous_df is None:
            self.logger.warning("No previous run found for reconciliation")
            return ReconciliationReport(
                alerts=[],
                changes=pd.DataFrame(),
                new_components=[],
                removed_components=[]
            )

        return reconciliator.compare_with_previous(df, previous_df)

    def _save_output(self, df: pd.DataFrame, runtime: float, validation_result) -> Path:
        """Save results with versioning."""
        handler = VersionedFileHandler('output')

        # Get number of portfolios from fund's PORTFOLIO_CONFIGS
        portfolio_configs = getattr(self.fund_config_module, 'PORTFOLIO_CONFIGS', {})
        num_portfolios = len(portfolio_configs) if portfolio_configs else 1

        metadata = {
            'fund_name': self.fund_name,
            'calculation_date': self.run_date,
            'run_timestamp': datetime.now().isoformat(),
            'runtime_seconds': runtime,
            'validation_status': 'PASSED' if validation_result.is_valid else 'FAILED',
            'num_portfolios': num_portfolios,
            'num_components': len(df),
            'user': os.getenv('USERNAME', 'unknown'),
            'python_version': sys.version.split()[0]
        }

        return handler.save_csv(
            df=df,
            fund_name=self.fund_name,
            date=self.run_date,
            metadata=metadata
        )
