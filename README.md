# Vanguard Multi-Asset Fund Calculation System

Production-ready system for daily fund weight calculations with UCITS compliance.

## Features

- **Modular Architecture**: Shared components for API, validation, logging, email
- **Vanguard LifeStrategy**: Multi-tier waterfall calculation (LSE20/40/60/80)
- **UCITS Compliance**: 19.25% position cap validation
- **Versioned Outputs**: Timestamp-based files for same-day reruns
- **Email Notifications**: Automatic alerts on success/failure
- **Reconciliation**: Day-over-day change detection
- **Fresh Data**: No caching - always fetch live market data

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials

Create `config/api-key.txt` with your FactSet API key (gitignored):
```
your_factset_api_key_here
```

### 3. Configure Email (Optional)

Create `config/email_password.txt` with your SMTP password (gitignored):
```
your_email_password_here
```

Update `config/email_config.yaml` with your SMTP server and recipients.

### 4. Verify Base Data File

Ensure `vanguard_base.csv` exists in the project root.

## Usage

### Manual Run (Today)

```bash
python orchestration\main_pipeline.py
```

### Manual Run (Specific Date)

```bash
python orchestration\main_pipeline.py --date=20250821
```

### Automated Run (Windows Task Scheduler)

1. Open Task Scheduler
2. Create new task
3. Trigger: Daily at 6:00 AM (weekdays only)
4. Action: Run `run_daily_calculations.bat`
5. Set working directory to project root

## Output

### File Structure

```
output/
└── vanguard_lifestrat/
    └── 20250821/
        ├── vanguard_lifestrat_20250821_060515.csv     # Versioned
        ├── vanguard_lifestrat_20250821_060515.json    # Metadata
        └── vanguard_lifestrat_20250821_latest.csv     # Latest copy
```

### File Format

CSV with 9 decimal precision:
- `Date`: Calculation date (YYYYMMDD)
- `Benchmark ID`: Component identifier
- `Weight`: Component weight (%)
- Additional columns from vanguard_base.csv

## Email Notifications

### Success Email
- Subject: `[SUCCESS] Fund Calculations 20250821`
- Recipients: success list from `email_config.yaml`
- Includes: Summary table, warnings, log attachment

### Failure Email
- Subject: `[CRITICAL FAILURE] Fund Calculations 20250821`
- Recipients: failure list (escalated)
- Includes: Error details, remediation steps, log attachment

## Validation

### Automatic Checks

1. **Sum Validation**: Weights sum to 100% (±0.01%)
2. **UCITS Cap**: No position > 19.25%
3. **Missing Data**: All components have weights
4. **Reconciliation**: Flag changes > 5% vs. previous day

### Manual Review Triggers

- Reconciliation alerts (significant weight changes)
- Positions within 0.5% of UCITS cap
- Validation warnings

## Logs

### Location

```
logs/
├── main_pipeline_20250821.log
├── vanguard_lifestrat_20250821.log
└── archive/  # Rotated logs
```

### Rotation

- Max size: 10MB per file
- Backups: 5 files
- Auto-archive: >90 days

## Adding New Funds

1. Create fund directory: `funds/fund_name/`
2. Implement: `config.py`, `calculator.py`
3. Update `main_pipeline.py`: Add fund to `_get_fund_list()`
4. Create config: `config/funds/fund_name.yaml`

## Troubleshooting

### API Authentication Failed
- Check `config/api-key.txt` has valid key
- Verify expiration date

### Market Data Missing
- Check FactSet status
- Verify date is not weekend/holiday
- Retry in 30 minutes

### Validation Failed
- Review log file for specific errors
- Check calculation logic
- Verify vanguard_base.csv is up-to-date

### Email Not Sent
- Verify SMTP settings in `email_config.yaml`
- Check `email_password.txt` exists
- Test with manual Python SMTP connection

## Architecture

```
Project Structure:
├── shared/          # Reusable components
│   ├── api/        # FactSet client
│   ├── validation/ # Weight validator, reconciliation
│   └── utils/      # Logger, emailer, file handler
├── funds/          # Fund-specific logic
│   └── vanguard_lifestrat/
│       ├── config.py
│       └── calculator.py
├── orchestration/  # Pipeline logic
│   ├── main_pipeline.py
│   └── single_fund_runner.py
├── config/         # YAML configurations
├── output/         # Generated files
└── logs/           # Log files
```

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review `production_workflow_design.md` for detailed design
3. Contact: quant-team@company.com
