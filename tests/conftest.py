"""
Pytest configuration and shared fixtures
"""

import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


@pytest.fixture
def sample_market_data():
    """Sample market cap data for testing.

    Note: LHMN34611 and I00010 are fixed weight components added automatically by the calculator,
    so they should not be included in the market data.
    """
    return pd.DataFrame({
        'symbol': [
            'LHMN21140', 'LHMN9913', 'LHMN21153', 'LHMN2004', 'LHMN2002',
            'I01018', 'I01270', 'I00586', 'I27049', 'I26152', '180948'
        ],
        'MarketCapIndex': [
            13907429.834769,
            9008236.846347,
            1732624.678237,
            9381590.413234,
            3374599.379621,
            82031193.018944,
            9412058.672003,
            59972007.022340,
            13118308.339329,
            3531314.177989,
            5093057.828
        ]
    })


@pytest.fixture
def sample_weights_df():
    """Sample weights DataFrame for testing - LSE80 portfolio only."""
    return pd.DataFrame({
        'Date': ['20250821'] * 14,
        'Fund ID': ['LSE80'] * 14,
        'Equity Allocation': [80] * 14,
        'Fund Benchmark': ['LSETF 80% Benchmark'] * 14,
        'Benchmark ID': [
            'LSE80_LHMN34611', 'LSE80_LHMN21140', 'LSE80_LHMN9913', 'LSE80_LHMN21153',
            'LSE80_LHMN2004', 'LSE80_LHMN2002', 'LSE80_I00010', 'LSE80_I01018',
            'LSE80_I01270', 'LSE80_I00586', 'LSE80_I27049', 'LSE80_I26152',
            'LSE80_180948', 'LSE80_SP50'
        ],
        'symbol': [
            'LHMN34611', 'LHMN21140', 'LHMN9913', 'LHMN21153', 'LHMN2004', 'LHMN2002',
            'I00010', 'I01018', 'I01270', 'I00586', 'I27049', 'I26152', '180948', 'SP50'
        ],
        'MarketCapIndex': [
            '', 13383929.76, 8782719.665, 1665438.207, 9138954.135, 3342705.378,
            '', 78748805.61, 8811976.832, 57300667.07, 12900321.2, 3273425.567,
            5093057.828, 53995577.88
        ],
        'Weight': [
            19.25, 0.276422791, 0.181392455, 0.034396854, 0.188749885, 0.069038015,
            19.25, 19.25, 6.113782651, 19.25, 5.810210767, 1.474327048,
            2.293876174, 6.55780336
        ]
    })


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with test files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create test email config
    email_config = config_dir / "email_config.yaml"
    email_config.write_text("""
smtp:
  server: "smtp.test.com"
  port: 587
  use_tls: true
  username: "test@test.com"
  password_file: "config/email_password.txt"

recipients:
  success:
    - "test@test.com"
  partial:
    - "test@test.com"
  failure:
    - "test@test.com"

attachments:
  include_logs: true
  include_summary_excel: false
  max_size_mb: 10
""")

    # Create test password file
    password_file = config_dir / "email_password.txt"
    password_file.write_text("test_password")

    # Create test validation rules
    validation_config = config_dir / "validation_rules.yaml"
    validation_config.write_text("""
global:
  ucits_cap: 19.25
  ucits_warning_threshold: 0.5
  reconciliation:
    enabled: true
    change_threshold_pct: 5.0
""")

    return config_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_factset_response():
    """Mock FactSet API response."""
    return {
        'data': [
            {'fsymId': 'LHMN34611-S', 'marketValue': 1000000.0},
            {'fsymId': 'I00010-S', 'marketValue': 5000000.0}
        ]
    }


@pytest.fixture
def previous_day_weights():
    """Sample previous day weights for reconciliation testing."""
    return pd.DataFrame({
        'Date': ['20250820'] * 4,
        'Fund ID': ['LSE80'] * 4,
        'Equity Allocation': [80] * 4,
        'Fund Benchmark': ['LSETF 80% Benchmark'] * 4,
        'Benchmark ID': ['LSE80_LHMN34611', 'LSE80_I00010', 'LSE80_I01018', 'LSE80_I01270'],
        'Fund Description': ['Bond ETF', 'Equity ETF', 'Developed ETF', 'Emerging ETF'],
        'Benchmark Description': ['Bond Index', 'Equity Index', 'Developed Index', 'Emerging Index'],
        'symbol': ['LHMN34611', 'I00010', 'I01018', 'I01270'],
        'MarketCapIndex': [1.0, 1.0, 82031193.018944, 9412058.672003],
        'Weight': [19.25, 19.25, 19.25, 6.10]  # Slightly different from current
    })
