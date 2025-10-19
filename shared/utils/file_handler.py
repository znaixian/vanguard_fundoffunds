"""
File Handler Utility
Versioned file I/O with audit trail
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import json
from typing import Optional, Dict


class VersionedFileHandler:
    """Handles versioned file saving with metadata."""

    def __init__(self, base_output_dir: str):
        """
        Initialize file handler.

        Args:
            base_output_dir: Base directory for output files
        """
        self.base_dir = Path(base_output_dir)

    def save_csv(
        self,
        df: pd.DataFrame,
        fund_name: str,
        date: str,
        metadata: dict = None
    ) -> Path:
        """
        Save DataFrame with versioning.

        Process:
        1. Create directory: output/{fund_name}/{date}/
        2. Generate filename: {fund_name}_{date}_{timestamp}.csv
        3. Save with 9 decimal precision
        4. Copy to: {fund_name}_{date}_latest.csv
        5. Save metadata JSON alongside CSV

        Args:
            df: DataFrame to save
            fund_name: Fund name
            date: Date string (YYYYMMDD)
            metadata: Optional metadata dictionary

        Returns:
            Path to saved file
        """
        # Create date directory
        output_dir = self.base_dir / fund_name / date
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now().strftime('%H%M%S')

        # Create filenames
        versioned_file = output_dir / f"{fund_name}_{date}_{timestamp}.csv"
        latest_file = output_dir / f"{fund_name}_{date}_latest.csv"
        metadata_file = output_dir / f"{fund_name}_{date}_{timestamp}.json"

        # Save CSV
        df.to_csv(versioned_file, index=False, float_format='%.9f')
        df.to_csv(latest_file, index=False, float_format='%.9f')

        # Save metadata
        if metadata:
            version_num = self._get_version_number(output_dir, fund_name, date)
            metadata['version'] = version_num

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        print(f"Saved: {versioned_file}")
        return versioned_file

    def get_previous_run(self, fund_name: str, current_date: str) -> Optional[pd.DataFrame]:
        """
        Retrieve latest file from strictly previous day for reconciliation.

        Args:
            fund_name: Fund name
            current_date: Current date (YYYYMMDD)

        Returns:
            DataFrame from previous run, or None if not found
        """
        from datetime import datetime, timedelta

        fund_dir = self.base_dir / fund_name

        if not fund_dir.exists():
            return None

        # Calculate strictly previous day (current_date - 1)
        current_dt = datetime.strptime(current_date, '%Y%m%d')
        previous_dt = current_dt - timedelta(days=1)
        previous_date = previous_dt.strftime('%Y%m%d')

        # Check if directory exists for strictly previous day
        previous_dir = fund_dir / previous_date

        if not previous_dir.exists():
            return None

        # Find latest file in the previous day's folder
        latest_file = previous_dir / f"{fund_name}_{previous_date}_latest.csv"

        if latest_file.exists():
            return pd.read_csv(latest_file)

        return None

    def _get_version_number(self, output_dir: Path, fund_name: str, date: str) -> int:
        """Count existing CSV files for this date to determine version number."""
        pattern = f"{fund_name}_{date}_*.csv"
        existing_files = list(output_dir.glob(pattern))
        # Exclude 'latest' file
        existing_files = [f for f in existing_files if 'latest' not in f.name]
        return len(existing_files)
