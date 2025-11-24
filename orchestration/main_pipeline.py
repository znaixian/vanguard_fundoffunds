"""
Main Pipeline
Entry point for daily fund calculations

Usage:
    python orchestration/main_pipeline.py                    # Run for today
    python orchestration/main_pipeline.py --date=20250821    # Run for specific date
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd

from shared.utils.logger import FundLogger
from shared.utils.config_loader import ConfigLoader
from shared.utils.emailer import EmailNotifier
from shared.utils.s3_uploader import S3Uploader
from shared.api.factset_client import FactSetClient, MissingDataError, APIConnectionError
from orchestration.single_fund_runner import FundRunner
import importlib


class DailyPipeline:
    """Main pipeline for daily fund calculations."""

    def __init__(self, run_date: str):
        """
        Initialize pipeline.

        Args:
            run_date: Run date (YYYYMMDD)
        """
        self.run_date = run_date
        self.logger = FundLogger.setup_logger('main_pipeline', run_date)
        self.config_loader = ConfigLoader()
        self.results = []
        self.market_data = None
        self.returns_data = None  # Store returns data
        self.s3_uploader = S3Uploader('config/aws_config.yaml')
        self.s3_results = {}  # Track S3 upload results

    def run(self, fund_filter: str = None):
        """
        Execute daily calculation pipeline.

        Args:
            fund_filter: Optional fund name to run only that fund

        Returns:
            Exit code (0=success, 1=partial, 2=failure)
        """
        self.logger.info(f"Starting daily fund calculations for {self.run_date}")

        try:
            # Step 1: Fetch fresh market data (shared across all funds)
            self.market_data = self._fetch_market_data()

            # Step 1a: Fetch returns data (shared across all funds)
            self.returns_data = self._fetch_returns_data()

            # Step 2: Get list of funds to process
            funds = self._get_fund_list(fund_filter)

            # Step 3: Process each fund
            for fund_name in funds:
                try:
                    result = self._process_fund(fund_name)
                    self.results.append(result)

                    # Step 3a: Upload to S3 if calculation was successful
                    if result.get('status') == 'SUCCESS' and 'output_path' in result:
                        self._upload_to_s3(fund_name, result)

                except Exception as e:
                    self.logger.error(f"Fund {fund_name} failed: {e}", exc_info=True)
                    self.results.append({
                        'fund': fund_name,
                        'status': 'FAILED',
                        'error': str(e)
                    })

            # Step 4: Send email summary
            self._send_summary()

            # Step 5: Cleanup
            self._cleanup()

            # Determine exit code
            exit_code = self._determine_exit_code()
            self.logger.info(f"Pipeline completed with exit code {exit_code}")

            return exit_code

        except (MissingDataError, APIConnectionError) as e:
            self.logger.critical(f"Pipeline failed - Market data issue: {e}", exc_info=True)
            self._send_failure_email(str(e))
            return 2
        except Exception as e:
            self.logger.critical(f"Pipeline failed: {e}", exc_info=True)
            self._send_failure_email(str(e))
            return 2

    def _fetch_market_data(self) -> pd.DataFrame:
        """Fetch fresh market cap data for all funds."""
        self.logger.info("Fetching fresh market data from FactSet")

        # Collect ALL_COMPONENT_IDS from all active funds
        all_funds = self._get_fund_list()
        all_ids = []

        for fund_name in all_funds:
            try:
                config_module = importlib.import_module(f"funds.{fund_name}.config")
                fund_ids = getattr(config_module, 'ALL_COMPONENT_IDS', [])
                all_ids.extend(fund_ids)
                self.logger.info(f"Loaded {len(fund_ids)} securities from {fund_name}")
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Could not load securities for {fund_name}: {e}")

        # Remove duplicates (in case funds share securities)
        all_ids = list(set(all_ids))
        self.logger.info(f"Total unique securities across all funds: {len(all_ids)}")

        # Initialize FactSet client
        client = FactSetClient('config/api_credentials.yaml')

        # Fetch fresh data (no caching)
        market_data = client.get_market_caps(
            ids=all_ids,
            date=self.run_date
        )

        self.logger.info(f"Successfully retrieved market data for {len(market_data)} securities")
        return market_data

    def _fetch_returns_data(self) -> pd.DataFrame:
        """Fetch return data for all funds."""
        self.logger.info("Fetching returns data from FactSet")

        # Collect ALL_COMPONENT_IDs and their FactSet identifiers from all active funds
        all_funds = self._get_fund_list()
        id_to_factset_map = {}

        for fund_name in all_funds:
            try:
                # Import the factset_identifiers module for this fund
                identifiers_module = importlib.import_module(f"funds.{fund_name}.factset_identifiers")
                fund_map = getattr(identifiers_module, 'FACTSET_IDENTIFIER_MAP', {})

                # Merge with main map
                id_to_factset_map.update(fund_map)

                self.logger.info(f"Loaded {len(fund_map)} FactSet identifiers from {fund_name}")
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Could not load FactSet identifiers for {fund_name}: {e}")

        if not id_to_factset_map:
            self.logger.warning("No FactSet identifier mappings found - returns will not be fetched")
            # Return empty DataFrame with expected structure
            return pd.DataFrame(columns=['symbol', 'Return'])

        self.logger.info(f"Total unique securities for returns fetch: {len(id_to_factset_map)}")

        # Initialize FactSet client
        client = FactSetClient('config/api_credentials.yaml')

        # Fetch returns data
        returns_data = client.get_returns(
            id_to_factset_map=id_to_factset_map,
            date=self.run_date
        )

        self.logger.info(f"Successfully retrieved returns for {len(returns_data)} securities")
        return returns_data

    def _get_fund_list(self, fund_filter: str = None) -> List[str]:
        """Get list of funds to process from config file."""
        # Load active funds from config
        funds_config = self.config_loader.load('config/funds.yaml')
        all_funds = funds_config.get('active_funds', [])

        if not all_funds:
            raise ValueError("No active funds configured in config/funds.yaml")

        if fund_filter:
            if fund_filter in all_funds:
                return [fund_filter]
            else:
                raise ValueError(f"Unknown fund: {fund_filter}. Available: {all_funds}")

        return all_funds

    def _process_fund(self, fund_name: str) -> Dict:
        """Process a single fund calculation."""
        self.logger.info(f"Processing fund: {fund_name}")

        runner = FundRunner(
            fund_name=fund_name,
            run_date=self.run_date,
            market_data=self.market_data,
            returns_data=self.returns_data
        )

        result = runner.run()
        return result

    def _upload_to_s3(self, fund_name: str, result: Dict):
        """
        Upload calculation files to S3.

        Args:
            fund_name: Fund name
            result: Calculation result dictionary
        """
        if not self.s3_uploader.enabled:
            self.logger.info("S3 upload disabled - skipping")
            return

        self.logger.info(f"Uploading {fund_name} files to S3")

        # Get output directory from result
        output_path = Path(result['output_path'])
        output_dir = output_path.parent

        # Upload fund calculation files
        upload_results = self.s3_uploader.upload_fund_calculation(
            fund_name=fund_name,
            date=self.run_date,
            output_dir=output_dir,
            include_logs=True
        )

        # Store results for email summary
        self.s3_results[fund_name] = upload_results

        # Log summary
        successful = sum(1 for v in upload_results.values() if v)
        total = len(upload_results)

        if successful == total:
            self.logger.info(f"S3 upload successful: {successful}/{total} files uploaded")
        else:
            self.logger.warning(f"S3 upload partial: {successful}/{total} files uploaded")

            # Log which files failed
            failed_files = [f for f, success in upload_results.items() if not success]
            self.logger.warning(f"Failed uploads: {failed_files}")

    def _send_summary(self):
        """Send email summary of all fund results."""
        emailer = EmailNotifier('config/email_config.yaml')

        # Collect attachments
        attachments = []

        # Add log file
        log_file = Path('logs') / f"main_pipeline_{self.run_date}.log"
        if log_file.exists():
            attachments.append(log_file)

        # Add output files from successful calculations
        for result in self.results:
            if result.get('status') == 'SUCCESS' and 'output_path' in result:
                output_path = Path(result['output_path'])
                if output_path.exists():
                    attachments.append(output_path)
                    self.logger.info(f"Adding output file to email: {output_path}")

        emailer.send_daily_summary(
            date=self.run_date,
            results=self.results,
            attachments=attachments,
            s3_results=self.s3_results
        )

    def _send_failure_email(self, error: str):
        """Send critical failure email."""
        emailer = EmailNotifier('config/email_config.yaml')

        subject = f"[CRITICAL FAILURE] Fund Calculations {self.run_date}"

        html_body = f"""
        <html>
        <body>
            <h2 style="color: red;">Critical Pipeline Failure - {self.run_date}</h2>

            <p><strong>Error:</strong></p>
            <pre style="background-color: #f5f5f5; padding: 10px;">{error}</pre>

            <p><strong>Impact:</strong> No calculations were performed. No output files generated.</p>

            <h3>Common Causes:</h3>
            <ul>
                <li><strong>Market Data Missing:</strong> FactSet API returned null/missing values for one or more securities</li>
                <li><strong>API Connection Failed:</strong> Cannot reach FactSet API (network/firewall issue)</li>
                <li><strong>Authentication Failed:</strong> Invalid or expired API credentials</li>
                <li><strong>Invalid Date:</strong> Weekend/holiday or future date requested</li>
            </ul>

            <h3>Next Steps:</h3>
            <ol>
                <li>Check log file: logs/main_pipeline_{self.run_date}.log</li>
                <li>If market data issue: Check FactSet status or retry in 30 minutes</li>
                <li>If authentication issue: Update config/api-key.txt</li>
                <li>If date issue: Run with previous business day</li>
                <li>Contact IT support if issue persists</li>
            </ol>

            <p style="color: gray; font-size: 11px;">
                Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                Run date: {self.run_date}
            </p>
        </body>
        </html>
        """

        # Send to failure recipients
        recipients = emailer.config['recipients']['failure']

        # Attach log file if exists
        log_file = Path('logs') / f"main_pipeline_{self.run_date}.log"
        attachments = [log_file] if log_file.exists() else []

        emailer._send_email(
            to=recipients,
            subject=subject,
            html_body=html_body,
            attachments=attachments
        )

    def _cleanup(self):
        """Cleanup old logs and output files."""
        self.logger.info("Running cleanup tasks")
        # Implementation for log rotation and archiving
        # Can be added later

    def _determine_exit_code(self) -> int:
        """Determine exit code based on results."""
        statuses = [r['status'] for r in self.results]

        if all(s == 'SUCCESS' for s in statuses):
            return 0  # All success
        elif all(s == 'FAILED' for s in statuses):
            return 2  # All failed
        else:
            return 1  # Partial success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Daily fund weight calculations')
    parser.add_argument('--date', default='today', help='Calculation date (YYYYMMDD or "today")')
    parser.add_argument('--fund', default=None, help='Specific fund to run (optional)')

    args = parser.parse_args()

    # Parse date
    if args.date == 'today':
        run_date = datetime.now().strftime('%Y%m%d')
    else:
        run_date = args.date

    # Execute pipeline
    pipeline = DailyPipeline(run_date)
    exit_code = pipeline.run(fund_filter=args.fund)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
