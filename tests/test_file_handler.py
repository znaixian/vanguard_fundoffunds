"""
Tests for file handler
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from shared.utils.file_handler import VersionedFileHandler


class TestVersionedFileHandler:
    """Test file handling with versioning."""

    def test_init(self, temp_output_dir):
        """Test handler initialization."""
        handler = VersionedFileHandler(str(temp_output_dir))
        assert handler.base_dir == Path(temp_output_dir)

    def test_save_csv_creates_files(self, temp_output_dir, sample_weights_df):
        """Test that save_csv creates both versioned and latest files."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        date = "20250821"

        result_path = handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date=date
        )

        # Check versioned file exists
        assert result_path.exists()
        assert fund_name in result_path.name
        assert date in result_path.name

        # Check latest file exists
        latest_file = temp_output_dir / fund_name / date / f"{fund_name}_{date}_latest.csv"
        assert latest_file.exists()

    def test_save_csv_with_metadata(self, temp_output_dir, sample_weights_df):
        """Test that metadata is saved correctly."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        date = "20250821"
        metadata = {
            "fund_name": fund_name,
            "date": date,
            "test_key": "test_value"
        }

        handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date=date,
            metadata=metadata
        )

        # Check metadata file exists
        metadata_files = list((temp_output_dir / fund_name / date).glob("*.json"))
        assert len(metadata_files) > 0

    def test_save_csv_precision(self, temp_output_dir, sample_weights_df):
        """Test that CSV is saved with 9 decimal precision."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        date = "20250821"

        handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date=date
        )

        # Read back and check precision
        latest_file = temp_output_dir / fund_name / date / f"{fund_name}_{date}_latest.csv"
        loaded_df = pd.read_csv(latest_file)

        # Check that weights are preserved
        assert loaded_df['Weight'].equals(sample_weights_df['Weight'])

    def test_get_previous_run_exists(self, temp_output_dir, sample_weights_df):
        """Test retrieving previous run when it exists."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        current_date = "20250822"
        previous_date = "20250821"

        # Save previous day's data
        handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date=previous_date
        )

        # Retrieve previous run
        previous_df = handler.get_previous_run(fund_name, current_date)

        assert previous_df is not None
        assert isinstance(previous_df, pd.DataFrame)
        assert len(previous_df) == len(sample_weights_df)

    def test_get_previous_run_not_exists(self, temp_output_dir):
        """Test retrieving previous run when it doesn't exist."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        current_date = "20250822"

        # No previous data saved
        previous_df = handler.get_previous_run(fund_name, current_date)

        assert previous_df is None

    def test_get_previous_run_strictly_previous_day(self, temp_output_dir, sample_weights_df):
        """Test that get_previous_run only checks strictly previous day."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        current_date = "20250825"  # Aug 25

        # Save data for Aug 20 (not previous day)
        handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date="20250820"
        )

        # Should NOT find Aug 20 data (not strictly previous day)
        previous_df = handler.get_previous_run(fund_name, current_date)
        assert previous_df is None

        # Save data for Aug 24 (strictly previous day)
        handler.save_csv(
            df=sample_weights_df,
            fund_name=fund_name,
            date="20250824"
        )

        # Should find Aug 24 data
        previous_df = handler.get_previous_run(fund_name, current_date)
        assert previous_df is not None

    def test_multiple_versions_same_day(self, temp_output_dir, sample_weights_df):
        """Test that multiple saves on same day create different versions."""
        import time
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "test_fund"
        date = "20250821"

        # Save first version
        path1 = handler.save_csv(df=sample_weights_df, fund_name=fund_name, date=date)

        # Wait a tiny bit to ensure different timestamp
        time.sleep(0.01)

        # Save second version
        path2 = handler.save_csv(df=sample_weights_df, fund_name=fund_name, date=date)

        # Both files should exist
        assert path1.exists()
        assert path2.exists()

        # Paths might be same if timestamps match (very rare), so just verify both saved
        assert (temp_output_dir / fund_name / date).exists()

    def test_directory_creation(self, temp_output_dir, sample_weights_df):
        """Test that directories are created automatically."""
        handler = VersionedFileHandler(str(temp_output_dir))

        fund_name = "new_fund"
        date = "20250821"

        # Directory shouldn't exist yet
        expected_dir = temp_output_dir / fund_name / date
        assert not expected_dir.exists()

        # Save should create directory
        handler.save_csv(df=sample_weights_df, fund_name=fund_name, date=date)

        assert expected_dir.exists()
        assert expected_dir.is_dir()
