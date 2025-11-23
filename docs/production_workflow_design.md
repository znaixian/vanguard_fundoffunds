# Production Workflow Design - Lightweight Fund Calculation System

## Overview
A lightweight, production-ready architecture for daily fund weight calculations with minimal infrastructure overhead. No continuously running services required.

---

## Design Principles

1. **No Daemon Processes**: Scheduled via Windows Task Scheduler, runs and exits
2. **Email-Only Monitoring**: Simple notifications, no dashboards or web servers
3. **File-Based Logging**: Rotating logs, no ELK stack overhead
4. **Versioned Outputs**: Handle same-day reruns with timestamped files
5. **Shared Components**: Maximize code reuse across multiple funds
6. **Fresh Data Daily**: No caching - fetch live market data each run
7. **Fail-Safe**: Extensive validation with human-in-the-loop on errors

---

## Architecture

### 1. Project Structure

```
project_root/
├── config/
│   ├── api_credentials.yaml         # FactSet API credentials (gitignored)
│   ├── email_config.yaml            # SMTP settings, recipient list
│   ├── funds/
│   │   ├── vanguard_lifestrat.yaml  # Fund-specific config
│   │   ├── fund_2.yaml
│   │   └── fund_3.yaml
│   └── validation_rules.yaml        # Global validation parameters
│
├── shared/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── factset_client.py        # Reusable FactSet API wrapper
│   │   └── response_parser.py       # Parse and validate API responses
│   │
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── weight_validator.py      # UCITS, sum checks
│   │   ├── data_quality.py          # Missing data, outlier detection
│   │   └── reconciliation.py        # Day-over-day comparison
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Centralized logging setup
│       ├── emailer.py               # Email notification wrapper
│       ├── file_handler.py          # Versioned file I/O
│       └── config_loader.py         # YAML config reader
│
├── funds/
│   ├── __init__.py
│   ├── vanguard_lifestrat/
│   │   ├── __init__.py
│   │   ├── config.py                # Portfolio configs, component lists
│   │   ├── components.py            # Security definitions, tiers
│   │   └── calculator.py            # Waterfall calculation logic
│   │
│   ├── fund_2/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── components.py
│   │   └── calculator.py
│   │
│   └── fund_3/
│       └── ...
│
├── orchestration/
│   ├── __init__.py
│   ├── main_pipeline.py             # Entry point for all funds
│   └── single_fund_runner.py        # Run individual fund
│
├── output/
│   ├── vanguard_lifestrat/
│   │   ├── 20250821/
│   │   │   ├── vanguard_combined_weights_20250821_060015.csv
│   │   │   ├── vanguard_combined_weights_20250821_063042.csv
│   │   │   └── vanguard_combined_weights_20250821_latest.csv  # copy of latest
│   │   └── 20250822/
│   │       └── ...
│   ├── fund_2/
│   └── fund_3/
│
├── logs/
│   ├── vanguard_lifestrat_20250821.log
│   ├── fund_2_20250821.log
│   ├── main_pipeline_20250821.log
│   └── archive/                     # Rotated logs older than 90 days
│
├── tests/
│   ├── shared/
│   ├── funds/
│   └── integration/
│
├── requirements.txt
├── README.md
└── run_daily_calculations.bat       # Windows Task Scheduler entry point
```

---

## 2. Daily Execution Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Windows Task Scheduler triggers at 6:00 AM weekdays        │
│  Runs: run_daily_calculations.bat                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Initialize                                         │
│  - Load configurations (API, funds, validation)             │
│  - Setup logging (timestamped log files)                    │
│  - Determine run date (default: today)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Fetch Market Data (Fresh from API)                │
│  - Collect all security IDs from all funds                  │
│  - Make FactSet API call (batch all IDs)                    │
│  - Parse and validate response                              │
│  - Validate: check for missing/null values                  │
│  → If FAIL: Email alert + exit with error code              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Calculate Fund Weights (Sequential)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  For each fund (Vanguard, Fund2, Fund3):             │  │
│  │  1. Load fund-specific config                        │  │
│  │  2. Extract relevant market caps from API response   │  │
│  │  3. Run calculation logic (waterfall/tiers)          │  │
│  │  4. Generate DataFrame with weights                  │  │
│  │  5. Validate results (see Step 4)                    │  │
│  │  6. If valid: save output, else: log error + skip    │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Validation (Per Fund)                             │
│  - Sum validation: weights sum to 100% (±0.01% tolerance)  │
│  - UCITS compliance: no position > 19.25% (configurable)   │
│  - Missing data: all components have non-null weights      │
│  - Reconciliation: compare vs. T-1 (if exists)             │
│    • Flag if any weight change > 5% absolute               │
│    • Flag if new components added/removed                  │
│  → If FAIL: Mark fund as "failed", continue to next fund   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Output Generation (Versioned)                     │
│  For each successful fund:                                  │
│  - Generate filename: {fund}_{date}_{timestamp}.csv        │
│  - Save to: output/{fund}/{date}/                          │
│  - Copy to: output/{fund}/{date}/{fund}_{date}_latest.csv  │
│  - Precision: 9 decimal places                             │
│  - Include metadata: run_timestamp, version, user          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Email Notification                                │
│  Subject: [SUCCESS/PARTIAL/FAILURE] Fund Calculations {date}│
│                                                             │
│  Body:                                                      │
│  - Summary table (fund, status, runtime, file path)        │
│  - Validation warnings (if any)                            │
│  - Reconciliation alerts (significant changes)             │
│  - Error messages (for failed funds)                       │
│                                                             │
│  Attachments:                                               │
│  - Summary Excel with all funds' weights side-by-side      │
│  - Log file for the run                                    │
│                                                             │
│  Recipients: Configured in email_config.yaml               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Cleanup & Exit                                    │
│  - Rotate logs (keep last 90 days)                         │
│  - Archive old output files (keep last 365 days)           │
│  - Exit with code: 0 (success), 1 (partial), 2 (failure)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Shared Components Design

### A. FactSet API Client (`shared/api/factset_client.py`)

**Purpose:** Single source of truth for all FactSet API interactions

**Key Features:**
- Authentication management (from `api_credentials.yaml`)
- Batch fetching (all fund IDs in one call)
- Response parsing and validation
- Error handling with retry logic (3 attempts with exponential backoff)
- No caching - always fresh data

**Interface:**
```python
class FactSetClient:
    def __init__(self, credentials_path: str)

    def get_market_caps(
        self,
        ids: List[str],
        date: str
    ) -> pd.DataFrame:
        """
        Fetch fresh market cap data for given IDs and date.

        Args:
            ids: List of security IDs (e.g., ['LHMN34611', 'I00010', ...])
            date: Date in YYYYMMDD format

        Returns:
            DataFrame with columns: ['symbol', 'MarketCapIndex']

        Raises:
            APIConnectionError: Cannot reach FactSet API
            APIAuthError: Invalid credentials
            DataNotAvailableError: Data not available for date
            MissingDataError: Some IDs returned null values
        """
```

**Example Implementation:**
```python
import requests
import base64
import pandas as pd
from typing import List
import time

class FactSetClient:
    def __init__(self, credentials_path: str):
        self.config = self._load_credentials(credentials_path)
        self.base_url = self.config['factset']['base_url']
        self.timeout = self.config['factset']['timeout_seconds']
        self.max_retries = self.config['factset']['retry_attempts']
        self.retry_delay = self.config['factset']['retry_delay_seconds']

    def get_market_caps(self, ids: List[str], date: str) -> pd.DataFrame:
        """Fetch market caps with retry logic."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._fetch_with_validation(ids, date)
            except (APIConnectionError, requests.Timeout) as e:
                if attempt == self.max_retries:
                    raise
                wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(f"API call failed (attempt {attempt}/{self.max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def _fetch_with_validation(self, ids: List[str], date: str) -> pd.DataFrame:
        """Make API call and validate response."""
        # Build request
        ids_string = ','.join(ids)
        formula = f'FG_MCAP_IDX({date},{date},,USD)'
        url = f'{self.base_url}/time-series?ids={ids_string}&formulas={formula}&flatten=Y'

        # Make request
        response = requests.get(url, headers=self._get_auth_headers(), timeout=self.timeout)
        response.raise_for_status()

        # Parse response
        data = response.json()
        df = pd.DataFrame(data['data'])
        df = df.rename(columns={
            'requestId': 'symbol',
            formula: 'MarketCapIndex'
        })[['symbol', 'MarketCapIndex']]

        # Validate
        df['MarketCapIndex'] = pd.to_numeric(df['MarketCapIndex'], errors='coerce')

        # Check for missing data
        if df['MarketCapIndex'].isnull().any():
            missing = df[df['MarketCapIndex'].isnull()]['symbol'].tolist()
            raise MissingDataError(f"Missing market cap data for: {missing}")

        if len(df) != len(ids):
            missing = set(ids) - set(df['symbol'])
            raise MissingDataError(f"IDs not returned by API: {missing}")

        logger.info(f"Successfully fetched market caps for {len(df)} securities")
        return df
```

---

### B. Validation Framework (`shared/validation/`)

**Purpose:** Ensure data quality and regulatory compliance

**Components:**

#### 1. `weight_validator.py`
```python
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metrics: Dict

class WeightValidator:
    def __init__(self, config: dict):
        self.ucits_cap = config.get('ucits_cap', 19.25)
        self.sum_tolerance_pct = config.get('sum_tolerance_pct', 0.01)
        self.sum_tolerance_abs = config.get('sum_tolerance_abs', 0.0001)

    def validate(self, df: pd.DataFrame, portfolio_type: str) -> ValidationResult:
        """
        Run all weight validation checks.

        Checks:
        1. Sum of weights = 100% (within tolerance)
        2. No weight > UCITS cap
        3. No negative weights
        4. No missing/null weights

        Returns:
            ValidationResult with pass/fail status and details
        """
        errors = []
        warnings = []

        # Check 1: Sum validation
        total_weight = df['Weight'].sum()
        if abs(total_weight - 100.0) > self.sum_tolerance_abs:
            errors.append(f"Weight sum {total_weight:.9f}% != 100% (tolerance: ±{self.sum_tolerance_abs}%)")

        # Check 2: UCITS cap
        max_weight = df['Weight'].max()
        if max_weight > self.ucits_cap + self.sum_tolerance_abs:
            violators = df[df['Weight'] > self.ucits_cap + self.sum_tolerance_abs]
            errors.append(f"UCITS violation: {len(violators)} positions exceed {self.ucits_cap}%: {violators['Benchmark ID'].tolist()}")

        # Check 3: Negative weights
        if (df['Weight'] < 0).any():
            neg_positions = df[df['Weight'] < 0]
            errors.append(f"Negative weights found: {neg_positions['Benchmark ID'].tolist()}")

        # Check 4: Missing weights
        if df['Weight'].isnull().any():
            missing = df[df['Weight'].isnull()]
            errors.append(f"Missing weights for: {missing['Benchmark ID'].tolist()}")

        # Warnings: positions close to cap
        close_to_cap = df[(df['Weight'] > self.ucits_cap - 0.5) & (df['Weight'] <= self.ucits_cap)]
        if not close_to_cap.empty:
            warnings.append(f"Positions within 0.5% of UCITS cap: {close_to_cap['Benchmark ID'].tolist()}")

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
```

#### 2. `data_quality.py`
```python
class DataQualityChecker:
    def check_market_caps(self, df: pd.DataFrame, expected_ids: List[str]) -> QualityReport:
        """
        Validate market cap data quality.

        Checks:
        1. All expected IDs present
        2. No null/NaN values
        3. All values > 0
        4. No extreme outliers (optional: >3 std dev from historical mean)

        Returns:
            QualityReport with pass/fail status and details
        """
        errors = []
        warnings = []

        # Check 1: All IDs present
        actual_ids = set(df['symbol'])
        missing_ids = set(expected_ids) - actual_ids
        if missing_ids:
            errors.append(f"Missing IDs: {missing_ids}")

        # Check 2: No nulls
        null_count = df['MarketCapIndex'].isnull().sum()
        if null_count > 0:
            null_ids = df[df['MarketCapIndex'].isnull()]['symbol'].tolist()
            errors.append(f"Null market cap values for: {null_ids}")

        # Check 3: All positive
        if (df['MarketCapIndex'] <= 0).any():
            zero_or_neg = df[df['MarketCapIndex'] <= 0]
            errors.append(f"Zero/negative market cap for: {zero_or_neg['symbol'].tolist()}")

        return QualityReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

#### 3. `reconciliation.py`
```python
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

@dataclass
class ReconciliationReport:
    alerts: List[str]
    changes: pd.DataFrame  # DataFrame with columns: ['Component', 'Previous', 'Current', 'Change']
    new_components: List[str]
    removed_components: List[str]

class Reconciliator:
    def __init__(self, threshold_pct: float = 5.0):
        self.threshold_pct = threshold_pct

    def compare_with_previous(
        self,
        current: pd.DataFrame,
        previous: pd.DataFrame
    ) -> ReconciliationReport:
        """
        Compare current weights with previous day.

        Flags:
        - Weight changes > threshold_pct (absolute)
        - New components added
        - Components removed
        - Sign changes (long to short, etc.)

        Returns:
            ReconciliationReport with list of changes and alerts
        """
        alerts = []

        # Merge current and previous
        merged = current.merge(
            previous[['Benchmark ID', 'Weight']],
            on='Benchmark ID',
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
        new_components = merged[merged['Weight_previous'] == 0]['Benchmark ID'].tolist()
        removed_components = merged[merged['Weight_current'] == 0]['Benchmark ID'].tolist()

        # Find significant changes
        significant = merged[merged['Change_Abs'] > self.threshold_pct]

        # Generate alerts
        if not significant.empty:
            for _, row in significant.iterrows():
                alerts.append(
                    f"{row['Benchmark ID']}: {row['Weight_previous']:.2f}% → {row['Weight_current']:.2f}% "
                    f"(Δ{row['Change']:+.2f}pp)"
                )

        if new_components:
            alerts.append(f"New components added: {new_components}")

        if removed_components:
            alerts.append(f"Components removed: {removed_components}")

        changes_df = merged[['Benchmark ID', 'Weight_previous', 'Weight_current', 'Change']].copy()
        changes_df = changes_df.sort_values('Change_Abs', ascending=False)

        return ReconciliationReport(
            alerts=alerts,
            changes=changes_df,
            new_components=new_components,
            removed_components=removed_components
        )
```

---

### C. File Handler (`shared/utils/file_handler.py`)

**Purpose:** Versioned file I/O with audit trail

```python
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
from typing import Optional, Dict

class VersionedFileHandler:
    def __init__(self, base_output_dir: str):
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

        logger.info(f"Saved: {versioned_file}")
        return versioned_file

    def get_previous_run(self, fund_name: str, current_date: str) -> Optional[pd.DataFrame]:
        """
        Retrieve latest file from previous business day for reconciliation.

        Looks for the most recent date directory before current_date.
        """
        fund_dir = self.base_dir / fund_name

        if not fund_dir.exists():
            return None

        # Get all date directories
        date_dirs = [d.name for d in fund_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        date_dirs = [d for d in date_dirs if d < current_date]  # Only previous dates

        if not date_dirs:
            return None

        # Get most recent date
        previous_date = max(date_dirs)
        previous_dir = fund_dir / previous_date

        # Find latest file
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
```

**Metadata JSON Example:**
```json
{
    "fund_name": "vanguard_lifestrat",
    "calculation_date": "20250821",
    "run_timestamp": "2025-08-21T06:15:42",
    "version": 1,
    "runtime_seconds": 12.3,
    "validation_status": "PASSED",
    "num_portfolios": 4,
    "num_components": 56,
    "user": "ncarucci",
    "python_version": "3.11.5"
}
```

---

### D. Email Notification (`shared/utils/emailer.py`)

**Purpose:** Send structured email reports

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict
import yaml

class EmailNotifier:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Read password from separate file
        password_file = self.config['smtp']['password_file']
        with open(password_file) as f:
            self.password = f.read().strip()

    def send_daily_summary(
        self,
        date: str,
        results: List[Dict],
        attachments: List[Path] = None
    ):
        """
        Send daily summary email.

        Subject line logic:
        - All passed: [SUCCESS] Fund Calculations {date}
        - Some failed: [PARTIAL] Fund Calculations {date}
        - All failed: [FAILURE] Fund Calculations {date}
        """
        # Determine overall status
        statuses = [r['status'] for r in results]

        if all(s == 'SUCCESS' for s in statuses):
            status_prefix = "[SUCCESS]"
        elif all(s == 'FAILED' for s in statuses):
            status_prefix = "[FAILURE]"
        else:
            status_prefix = "[PARTIAL]"

        subject = f"{status_prefix} Fund Calculations {date}"

        # Build email body
        html_body = self._build_html_body(date, results)

        # Get recipients based on status
        if status_prefix == "[SUCCESS]":
            recipients = self.config['recipients']['success']
        elif status_prefix == "[PARTIAL]":
            recipients = self.config['recipients']['partial']
        else:
            recipients = self.config['recipients']['failure']

        # Send email
        self._send_email(
            to=recipients,
            subject=subject,
            html_body=html_body,
            attachments=attachments or []
        )

        logger.info(f"Summary email sent to: {', '.join(recipients)}")

    def _build_html_body(self, date: str, results: List[Dict]) -> str:
        """Build HTML email body with summary table."""
        # Build table rows
        rows = []
        for r in results:
            status_color = "green" if r['status'] == 'SUCCESS' else "red"
            status_icon = "✓" if r['status'] == 'SUCCESS' else "✗"

            runtime = f"{r.get('runtime', 0):.1f}s" if 'runtime' in r else "N/A"
            output = r.get('output_path', 'N/A')
            warnings = "<br>".join(r.get('warnings', [])) if r.get('warnings') else "None"
            error = r.get('error', '')

            rows.append(f"""
            <tr>
                <td>{r['fund']}</td>
                <td style="color: {status_color};">{status_icon} {r['status']}</td>
                <td>{runtime}</td>
                <td style="font-size: 10px;">{output}</td>
                <td>{warnings}</td>
                <td style="color: red;">{error}</td>
            </tr>
            """)

        html = f"""
        <html>
        <body>
            <h2>Fund Calculation Summary - {date}</h2>

            <table border="1" cellpadding="5" cellspacing="0">
                <tr style="background-color: #f0f0f0;">
                    <th>Fund</th>
                    <th>Status</th>
                    <th>Runtime</th>
                    <th>Output File</th>
                    <th>Warnings</th>
                    <th>Errors</th>
                </tr>
                {''.join(rows)}
            </table>

            <h3>Next Steps</h3>
            <ul>
                <li>Review warnings and reconciliation alerts</li>
                <li>Check log files for detailed execution trace</li>
                <li>Verify output files before distribution</li>
            </ul>

            <p style="color: gray; font-size: 11px;">
                This is an automated email from the Fund Calculation System.<br>
                Logs and output files available at: {Path.cwd()}
            </p>
        </body>
        </html>
        """

        return html

    def _send_email(self, to: List[str], subject: str, html_body: str, attachments: List[Path]):
        """Send email via SMTP with attachments."""
        msg = MIMEMultipart()
        msg['From'] = self.config['smtp']['username']
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject

        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))

        # Attach files
        for file_path in attachments:
            if file_path.stat().st_size > self.config['attachments']['max_size_mb'] * 1024 * 1024:
                logger.warning(f"Skipping attachment {file_path.name}: exceeds max size")
                continue

            with open(file_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={file_path.name}')
            msg.attach(part)

        # Send
        with smtplib.SMTP(self.config['smtp']['server'], self.config['smtp']['port']) as server:
            if self.config['smtp']['use_tls']:
                server.starttls()
            server.login(self.config['smtp']['username'], self.password)
            server.send_message(msg)
```

---

### E. Logging (`shared/utils/logger.py`)

**Purpose:** Simple, rotating file-based logging

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

class FundLogger:
    @staticmethod
    def setup_logger(fund_name: str, date: str, log_dir: str = 'logs') -> logging.Logger:
        """
        Create a logger with:
        - File handler: logs/{fund_name}_{date}.log
        - Rotating: max 10MB, keep 5 backups
        - Format: [%(asctime)s] %(levelname)s - %(name)s - %(message)s
        - Level: INFO (configurable)

        Returns:
            Configured logger instance
        """
        # Create logs directory
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create logger
        logger = logging.getLogger(fund_name)
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        logger.handlers = []

        # File handler with rotation
        log_file = log_path / f"{fund_name}_{date}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )

        # Console handler (optional, for debugging)
        console_handler = logging.StreamHandler()

        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

# Global logger instance
logger = None

def get_logger():
    """Get the global logger instance."""
    global logger
    if logger is None:
        logger = FundLogger.setup_logger('main', datetime.now().strftime('%Y%m%d'))
    return logger
```

---

## 4. Configuration Files

### A. `config/api_credentials.yaml`
```yaml
factset:
  username: "FDS_DEMO_US-420289"
  api_key_file: "../config/api-key.txt"  # Separate file, gitignored
  base_url: "https://api.factset.com/formula-api/v1"
  timeout_seconds: 30
  retry_attempts: 3
  retry_delay_seconds: 5
```

### B. `config/email_config.yaml`
```yaml
smtp:
  server: "smtp.office365.com"
  port: 587
  use_tls: true
  username: "quant_system@firm.com"
  password_file: "../config/email_password.txt"  # Gitignored

recipients:
  success:
    - "quant-team@firm.com"
  partial:
    - "quant-team@firm.com"
    - "quant-manager@firm.com"
  failure:
    - "quant-team@firm.com"
    - "quant-manager@firm.com"
    - "it-support@firm.com"

attachments:
  include_logs: true
  include_summary_excel: true
  max_size_mb: 10
```

### C. `config/validation_rules.yaml`
```yaml
global:
  ucits_cap: 19.25
  sum_tolerance_pct: 0.01  # ±0.01%
  sum_tolerance_abs: 0.0001

  reconciliation:
    enabled: true
    change_threshold_pct: 5.0  # Alert if weight change > 5%
    lookback_days: 1  # Compare with T-1

  data_quality:
    allow_missing_data: false
    allow_negative_weights: false

# Fund-specific overrides (optional)
fund_overrides:
  vanguard_lifestrat:
    ucits_cap: 19.25
    sum_tolerance_pct: 0.005  # Stricter tolerance

  fund_2:
    ucits_cap: 20.0  # Different regulatory limit
```

### D. `config/funds/vanguard_lifestrat.yaml`
```yaml
fund_name: "Vanguard LifeStrategy"
fund_code: "VLSTRAT"
description: "Multi-asset portfolio with 4 risk profiles (LSE20/40/60/80)"

api_config:
  data_source: "factset"
  formula: "FG_MCAP_IDX"
  currency: "USD"

portfolios:
  LSE20:
    equity_allocation: 20
    fixed_income_allocation: 80
    base_weight: 19.25
    description: "20% Equity / 80% Fixed Income"

  LSE40:
    equity_allocation: 40
    fixed_income_allocation: 60
    base_weight: 19.25
    description: "40% Equity / 60% Fixed Income"

  LSE60:
    equity_allocation: 60
    fixed_income_allocation: 40
    base_weight: 19.25
    description: "60% Equity / 40% Fixed Income"

  LSE80:
    equity_allocation: 80
    fixed_income_allocation: 20
    base_weight: 19.25
    description: "80% Equity / 20% Fixed Income"

components:
  fixed_income:
    tier_1:
      - code: "LHMN34611"
        name: "Bloomberg Global Aggregate Float-Adjusted"
        weight_type: "fixed"
        fixed_weight: 19.25

    tier_3:
      - code: "LHMN21140"
        name: "Bloomberg Global Agg - US Treasury"
        weight_type: "market_cap_weighted"
        can_exceed_base: true  # Only FI component that can exceed 19.25%

      - code: "LHMN9913"
        name: "Bloomberg Global Agg Corporate - USD"
        weight_type: "market_cap_weighted"

      - code: "LHMN21153"
        name: "Bloomberg Gilts Float Adjusted"
        weight_type: "market_cap_weighted"

      - code: "LHMN2004"
        name: "Bloomberg Euro Agg Government"
        weight_type: "market_cap_weighted"

      - code: "LHMN2002"
        name: "Bloomberg Euro Agg Credit - Corporate"
        weight_type: "market_cap_weighted"

  equity:
    tier_1:
      - code: "I00010"
        name: "FTSE All-World"
        weight_type: "fixed"
        fixed_weight: 19.25

    tier_2:
      - code: "I01018"
        name: "FTSE All-World Developed"
        weight_type: "market_cap_weighted"

      - code: "I01270"
        name: "FTSE Emerging Markets"
        weight_type: "market_cap_weighted"

    tier_3:
      - code: "I00586"
        name: "FTSE All-World North America"
        weight_type: "market_cap_weighted"

      - code: "I27049"
        name: "FTSE All-World Developed Europe"
        weight_type: "market_cap_weighted"

      - code: "I26152"
        name: "FTSE All-World Developed Asia Pacific ex Japan"
        weight_type: "market_cap_weighted"

      - code: "180948"
        name: "FTSE Japan"
        weight_type: "market_cap_weighted"

    tier_4:
      - code: "SP50"
        name: "S&P 500"
        weight_type: "overflow"
        trigger_condition: "I00586 >= 19.25"  # Only gets allocation if NA caps

output:
  format: "csv"
  precision: 9
  include_metadata: true
  base_path: "output/vanguard_lifestrat"
```

---

## 5. Entry Point Scripts

### A. `run_daily_calculations.bat` (Windows Task Scheduler)
```batch
@echo off
REM Daily Fund Calculations - Entry Point
REM Scheduled via Windows Task Scheduler for 6:00 AM weekdays

SET PYTHON_PATH=C:\Python311\python.exe
SET SCRIPT_DIR=C:\Users\ncarucci\Documents\Gitfolder\Working\202501_Vanguard_Multi_Assets

cd /d %SCRIPT_DIR%

REM Activate virtual environment if using one
REM call venv\Scripts\activate.bat

REM Run main pipeline
%PYTHON_PATH% orchestration\main_pipeline.py --date=today

REM Capture exit code
SET EXIT_CODE=%ERRORLEVEL%

REM Log completion
echo [%DATE% %TIME%] Daily calculation completed with exit code: %EXIT_CODE% >> logs\scheduler.log

exit /b %EXIT_CODE%
```

### B. `orchestration/main_pipeline.py`
```python
"""
Main entry point for daily fund calculations.

Usage:
    python main_pipeline.py                    # Run for today
    python main_pipeline.py --date=20250821    # Run for specific date
    python main_pipeline.py --fund=vanguard    # Run single fund only
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd

from shared.utils.logger import FundLogger
from shared.utils.config_loader import ConfigLoader
from shared.utils.emailer import EmailNotifier
from shared.api.factset_client import FactSetClient
from orchestration.single_fund_runner import FundRunner


class DailyPipeline:
    def __init__(self, run_date: str):
        self.run_date = run_date
        self.logger = FundLogger.setup_logger('main_pipeline', run_date)
        self.config_loader = ConfigLoader()
        self.results = []
        self.market_data = None

    def run(self, fund_filter: str = None):
        """Execute daily calculation pipeline."""
        self.logger.info(f"Starting daily fund calculations for {self.run_date}")

        try:
            # Step 1: Fetch fresh market data (shared across all funds)
            self.market_data = self._fetch_market_data()

            # Step 2: Get list of funds to process
            funds = self._get_fund_list(fund_filter)

            # Step 3: Process each fund
            for fund_name in funds:
                try:
                    result = self._process_fund(fund_name)
                    self.results.append(result)
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

        except Exception as e:
            self.logger.critical(f"Pipeline failed: {e}", exc_info=True)
            self._send_failure_email(str(e))
            return 2

    def _fetch_market_data(self) -> pd.DataFrame:
        """Fetch fresh market cap data for all funds."""
        self.logger.info("Fetching fresh market data from FactSet")

        # Collect all security IDs from all fund configs
        all_ids = self._collect_all_security_ids()
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

    def _collect_all_security_ids(self) -> List[str]:
        """Collect all unique security IDs from all fund configurations."""
        all_ids = set()

        fund_configs = ['vanguard_lifestrat', 'fund_2', 'fund_3']  # Load from config

        for fund_name in fund_configs:
            config_path = f'config/funds/{fund_name}.yaml'
            config = self.config_loader.load(config_path)

            # Extract IDs from FI components
            for tier in config['components']['fixed_income'].values():
                for component in tier:
                    all_ids.add(component['code'])

            # Extract IDs from equity components
            for tier in config['components']['equity'].values():
                for component in tier:
                    all_ids.add(component['code'])

        return list(all_ids)

    def _get_fund_list(self, fund_filter: str = None) -> List[str]:
        """Get list of funds to process."""
        all_funds = ['vanguard_lifestrat', 'fund_2', 'fund_3']

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
            market_data=self.market_data
        )

        result = runner.run()
        return result

    def _send_summary(self):
        """Send email summary of all fund results."""
        emailer = EmailNotifier('config/email_config.yaml')

        # Collect attachments
        attachments = []
        if self.config_loader.get('email_config', {}).get('attachments', {}).get('include_logs', False):
            log_file = Path('logs') / f"main_pipeline_{self.run_date}.log"
            if log_file.exists():
                attachments.append(log_file)

        emailer.send_daily_summary(
            date=self.run_date,
            results=self.results,
            attachments=attachments
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

        # Rotate logs older than 90 days
        log_dir = Path('logs')
        # ... implementation ...

        # Archive output files older than 365 days
        output_dir = Path('output')
        # ... implementation ...

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
```

### C. `orchestration/single_fund_runner.py`
```python
"""
Runner for individual fund calculations.
Orchestrates: calculation → validation → output → reconciliation
"""

import importlib
from pathlib import Path
from typing import Dict
from datetime import datetime
import pandas as pd

from shared.utils.logger import FundLogger
from shared.utils.file_handler import VersionedFileHandler
from shared.validation.weight_validator import WeightValidator
from shared.validation.reconciliation import Reconciliator
from shared.utils.config_loader import ConfigLoader


class FundRunner:
    def __init__(self, fund_name: str, run_date: str, market_data: pd.DataFrame):
        self.fund_name = fund_name
        self.run_date = run_date
        self.market_data = market_data
        self.logger = FundLogger.setup_logger(f'{fund_name}', run_date)
        self.config_loader = ConfigLoader()

        # Dynamically import fund-specific calculator
        module_name = f"funds.{fund_name}.calculator"
        self.calculator_module = importlib.import_module(module_name)

    def run(self) -> Dict:
        """Execute full fund calculation workflow."""
        try:
            # Step 1: Calculate weights
            self.logger.info("Starting weight calculation")
            start_time = datetime.now()

            weights_df = self.calculator_module.calculate_all_portfolios(
                market_data=self.market_data,
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
        for portfolio_name in df['Portfolio'].unique():
            portfolio_df = df[df['Portfolio'] == portfolio_name]
            result = validator.validate(portfolio_df, portfolio_name)
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
            return ReconciliationReport(alerts=[], changes=pd.DataFrame(), new_components=[], removed_components=[])

        threshold = config.get('global', {}).get('reconciliation', {}).get('change_threshold_pct', 5.0)
        reconciliator = Reconciliator(threshold_pct=threshold)

        # Get previous file
        handler = VersionedFileHandler('output')
        previous_df = handler.get_previous_run(self.fund_name, self.run_date)

        if previous_df is None:
            self.logger.warning("No previous run found for reconciliation")
            return ReconciliationReport(alerts=[], changes=pd.DataFrame(), new_components=[], removed_components=[])

        return reconciliator.compare_with_previous(df, previous_df)

    def _save_output(self, df: pd.DataFrame, runtime: float, validation_result) -> Path:
        """Save results with versioning."""
        handler = VersionedFileHandler('output')

        metadata = {
            'fund_name': self.fund_name,
            'calculation_date': self.run_date,
            'run_timestamp': datetime.now().isoformat(),
            'runtime_seconds': runtime,
            'validation_status': 'PASSED' if validation_result.is_valid else 'FAILED',
            'num_portfolios': len(df['Portfolio'].unique()) if 'Portfolio' in df.columns else 1,
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
```

---

## 6. Example Fund Implementation

### `funds/vanguard_lifestrat/calculator.py`
```python
"""
Vanguard LifeStrategy weight calculation logic.
Implements multi-tier waterfall with UCITS caps.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from .config import PORTFOLIO_CONFIGS, FIXED_INCOME_COMPONENTS, EQUITY_COMPONENTS


def calculate_all_portfolios(market_data: pd.DataFrame, date: str) -> pd.DataFrame:
    """
    Calculate weights for all portfolios (LSE20, LSE40, LSE60, LSE80).

    Args:
        market_data: DataFrame with columns ['symbol', 'MarketCapIndex']
        date: Calculation date (YYYYMMDD)

    Returns:
        Combined DataFrame with columns:
        ['Date', 'Portfolio', 'Component', 'Symbol', 'Weight']
    """
    results = []

    for portfolio_name, config in PORTFOLIO_CONFIGS.items():
        portfolio_df = calculate_portfolio_weights(
            portfolio_name=portfolio_name,
            config=config,
            market_data=market_data,
            date=date
        )
        results.append(portfolio_df)

    combined = pd.concat(results, ignore_index=True)
    return combined


def calculate_portfolio_weights(
    portfolio_name: str,
    config: dict,
    market_data: pd.DataFrame,
    date: str
) -> pd.DataFrame:
    """Calculate weights for a single portfolio (e.g., LSE80)."""

    # Calculate FI weights
    fi_weights = calculate_fi_weights(config, market_data)

    # Calculate equity weights
    eq_weights = calculate_equity_weights(config, market_data)

    # Combine and format
    all_weights = {**fi_weights, **eq_weights}

    df = pd.DataFrame([
        {
            'Date': date,
            'Portfolio': portfolio_name,
            'Component': component_name,
            'Symbol': symbol,
            'Weight': weight
        }
        for (component_name, symbol), weight in all_weights.items()
    ])

    return df


def calculate_fi_weights(config: dict, market_data: pd.DataFrame) -> Dict:
    """
    Calculate fixed income weights using tier-based waterfall.

    Logic:
    - Tier 1 (LHMN34611): Fixed at 19.25%
    - Tier 3: Market cap weighted from remaining allocation
    - Overflow redistribution if any component capped at 19.25%
    """
    weights = {}
    base_weight = config['base_weight']
    fi_allocation = config['fixed_income_allocation']

    # Tier 1: Fixed weight
    weights[('Bloomberg Global Agg', 'LHMN34611')] = base_weight

    # Tier 3: Calculate market cap weighted allocation
    tier3_components = FIXED_INCOME_COMPONENTS['tier_3']
    tier3_mcaps = market_data[market_data['symbol'].isin(tier3_components)]
    total_tier3_mcap = tier3_mcaps['MarketCapIndex'].sum()

    remaining_allocation = fi_allocation - base_weight

    # First pass: proportional allocation
    tier3_weights = {}
    for _, row in tier3_mcaps.iterrows():
        symbol = row['symbol']
        mcap = row['MarketCapIndex']
        weight = remaining_allocation * (mcap / total_tier3_mcap)
        tier3_weights[symbol] = min(weight, base_weight)  # Cap at 19.25%

    # Check if redistribution needed
    total_allocated = sum(tier3_weights.values())
    if total_allocated < remaining_allocation:
        # Redistribute excess to non-capped components
        excess = remaining_allocation - total_allocated
        non_capped = {k: v for k, v in tier3_weights.items() if v < base_weight}

        if non_capped:
            total_non_capped = sum(non_capped.values())
            for symbol in non_capped:
                additional = excess * (non_capped[symbol] / total_non_capped)
                tier3_weights[symbol] = min(tier3_weights[symbol] + additional, base_weight)

    # Map to component names and add to weights dict
    component_names = {
        'LHMN21140': 'US Treasury',
        'LHMN9913': 'US Corporate',
        'LHMN21153': 'UK Gilts',
        'LHMN2004': 'EUR Government',
        'LHMN2002': 'EUR Corporate'
    }

    for symbol, weight in tier3_weights.items():
        weights[(component_names[symbol], symbol)] = weight

    return weights


def calculate_equity_weights(config: dict, market_data: pd.DataFrame) -> Dict:
    """
    Calculate equity weights using tier-based cascade.

    Logic:
    - Tier 1 (I00010): Fixed at 19.25%
    - Tier 2 (I01018, I01270): Market cap weighted from remaining
    - Tier 3: Market cap weighted from remaining after Tier 2
    - Tier 4 (SP50): Overflow only if Tier 3 North America capped
    """
    # Implementation similar to FI but with 4 tiers
    # ... (detailed logic from original vanguard_funds.py)

    return equity_weights  # Dict of {(component_name, symbol): weight}
```

---

## 7. Testing Strategy

### Unit Tests
```python
# tests/funds/test_vanguard_calculator.py

def test_lse80_total_weight():
    """Test that LSE80 weights sum to 100%"""
    market_data = load_test_market_data()
    result = calculate_portfolio_weights('LSE80', PORTFOLIO_CONFIGS['LSE80'], market_data, '20250821')
    assert abs(result['Weight'].sum() - 100.0) < 0.01


def test_ucits_compliance():
    """Test no component exceeds 19.25%"""
    market_data = load_test_market_data()
    result = calculate_all_portfolios(market_data, '20250821')
    assert result['Weight'].max() <= 19.25 + 0.0001


def test_fixed_tier1_weight():
    """Test Tier 1 FI component always 19.25%"""
    market_data = load_test_market_data()
    for portfolio in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
        result = calculate_portfolio_weights(portfolio, PORTFOLIO_CONFIGS[portfolio], market_data, '20250821')
        tier1_weight = result[result['Symbol'] == 'LHMN34611']['Weight'].iloc[0]
        assert tier1_weight == 19.25
```

### Integration Tests
```python
# tests/integration/test_full_pipeline.py

def test_full_pipeline_execution():
    """Test end-to-end pipeline with test data"""
    pipeline = DailyPipeline('20250821')
    exit_code = pipeline.run()

    assert exit_code == 0  # Success
    assert len(pipeline.results) == 3  # All funds processed
    assert all(r['status'] == 'SUCCESS' for r in pipeline.results)
```

---

## 8. Deployment Checklist

### Infrastructure
- [ ] Python 3.11+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Windows Task Scheduler configured (6:00 AM weekdays)
- [ ] Output directory created with write permissions
- [ ] Logs directory created

### Configuration
- [ ] `api_credentials.yaml` populated with valid FactSet credentials
- [ ] `email_config.yaml` configured with SMTP settings
- [ ] All fund config files created (`config/funds/*.yaml`)
- [ ] Validation rules reviewed and approved
- [ ] Email recipient lists updated

### Security
- [ ] API key file (`.txt`) added to `.gitignore`
- [ ] Email password file added to `.gitignore`
- [ ] File permissions restricted (only authorized users can read credentials)
- [ ] Sensitive config files encrypted at rest (optional)

### Testing
- [ ] Unit tests passing for all funds
- [ ] Integration test executed successfully
- [ ] Manual test run for 1 historical date
- [ ] Email notification received and reviewed
- [ ] Output file format validated

### Monitoring
- [ ] Test email sent to verify SMTP settings
- [ ] Log rotation tested (create >10MB log file)
- [ ] Failure scenario tested (invalid API key → email alert received)
- [ ] Reconciliation alert tested (modify historical file → trigger alert)

### Documentation
- [ ] Runbook created for common errors
- [ ] Contact escalation matrix defined
- [ ] Fund methodology documentation updated
- [ ] Code repository README updated

---

## 9. Common Error Scenarios & Remediation

| Error | Cause | Remediation | Prevention |
|-------|-------|-------------|------------|
| **API Authentication Failed** | Invalid/expired API key | Update `api-key.txt` with valid key | Set calendar reminder for key expiration |
| **Market Data Missing** | FactSet data unavailable for date | Check FactSet status, run for T-1 | Email alert sent automatically with details |
| **Validation: Sum ≠ 100%** | Rounding errors in calculation | Review calculation logic, adjust precision | Add assertion in calculator |
| **SMTP Connection Failed** | Firewall/network issue | Check SMTP server status, test port 587 | Monitor SMTP server health |
| **File Permission Denied** | Insufficient write permissions | Grant write access to output directory | Check permissions in deployment checklist |
| **Missing Previous File** | First run or file deleted | Skip reconciliation, log warning | Archive historical files properly |
| **Component Market Cap = 0** | Data error or delisted security | Investigate with FactSet, exclude component | Add data quality check for zero values |

---

## 10. Maintenance & Operations

### Daily Operations
- **6:00 AM**: Pipeline runs automatically via Task Scheduler
- **6:15 AM**: Review email summary (check for warnings/errors)
- **6:30 AM**: If failures, investigate logs and re-run manually
- **9:00 AM**: Distribute final output files to stakeholders

### Weekly Tasks
- **Monday**: Review previous week's reconciliation alerts
- **Friday**: Verify log rotation working (check `logs/archive/`)

### Monthly Tasks
- **1st business day**: Review output directory size, archive old files if >10GB
- **15th**: Review API usage (FactSet billing), optimize if needed

### Quarterly Tasks
- **Review validation rules**: Adjust thresholds based on false positive rate
- **Update fund components**: Add/remove securities per methodology changes
- **Performance review**: Analyze runtime trends, optimize slow calculations

### Annual Tasks
- **Renew API credentials**: Update FactSet API key before expiration
- **Security audit**: Review access logs, update permissions
- **Disaster recovery test**: Restore from backup, verify pipeline runs

---

## 11. File Versioning Example

### Scenario: Same-Day Rerun

**First Run (6:00 AM):**
```
API call fails → Email alert sent → No output file created
```

**Second Run (6:30 AM - Manual):**
```
API call succeeds → Calculation runs → Output saved
```

**Directory Structure:**
```
output/vanguard_lifestrat/20250821/
├── vanguard_lifestrat_20250821_063042.csv     ← Successful run
├── vanguard_lifestrat_20250821_063042.json    ← Metadata
└── vanguard_lifestrat_20250821_latest.csv     ← Copy of latest
```

**Third Run (7:00 AM - Correction):**
```
Market data corrected → Re-run → New version saved
```

**Updated Directory:**
```
output/vanguard_lifestrat/20250821/
├── vanguard_lifestrat_20250821_063042.csv     ← First successful run
├── vanguard_lifestrat_20250821_063042.json
├── vanguard_lifestrat_20250821_070015.csv     ← Corrected run
├── vanguard_lifestrat_20250821_070015.json
└── vanguard_lifestrat_20250821_latest.csv     ← Updated to 070015 version
```

**Metadata JSON (070015 version):**
```json
{
    "fund_name": "vanguard_lifestrat",
    "calculation_date": "20250821",
    "run_timestamp": "2025-08-21T07:00:15",
    "version": 2,
    "runtime_seconds": 11.8,
    "validation_status": "PASSED",
    "num_portfolios": 4,
    "num_components": 56,
    "user": "ncarucci"
}
```

---

## 12. Summary

This lightweight design provides:

✓ **No Daemon Overhead**: Runs once per day via Task Scheduler, exits cleanly
✓ **Simple Monitoring**: Email notifications with HTML summaries and attachments
✓ **Minimal Logging**: File-based logs with rotation, no external services
✓ **Robust Versioning**: Timestamp-based files with audit trail
✓ **Shared Components**: API client, validation, file I/O reused across funds
✓ **Configurable**: YAML-based config for funds, validation, credentials
✓ **Fail-Safe**: Extensive validation, reconciliation, error handling
✓ **Fresh Data**: No caching - always fetch live market data
✓ **Maintainable**: Clear structure, documented methodology, runbooks

**Total Infrastructure Required:**
- Windows Server with Task Scheduler (or Linux with Cron)
- SMTP server access (for email)
- File storage (local or network share)

**No Additional Services Needed:**
- ❌ No Airflow/Prefect daemons
- ❌ No Prometheus/Grafana servers
- ❌ No Elasticsearch/Kibana clusters
- ❌ No Redis/database servers
- ❌ No caching layer

This design balances production-readiness with operational simplicity, suitable for a team managing 3-5 fund calculation workflows with daily runs using fresh market data.
