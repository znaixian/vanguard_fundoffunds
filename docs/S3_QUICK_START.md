# S3 Setup Quick Start

This is a quick reference for setting up AWS S3 delivery. For detailed step-by-step instructions, see [S3_SETUP_GUIDE.md](S3_SETUP_GUIDE.md).

## What Was Added

Your fund calculation pipeline now supports automatic upload to AWS S3 cloud storage. When enabled:
- All calculation files (CSV, JSON, logs) are automatically uploaded to S3
- Email notifications include S3 upload status
- Files are organized in S3 the same way as your local `output/` directory

## Quick Setup (5 Steps)

### 1. Create AWS Account and S3 Bucket
- Go to [https://aws.amazon.com/](https://aws.amazon.com/) and create an account
- Create an S3 bucket (name it something like `vanguard-fundoffunds-prod`)
- Note your bucket name and region

### 2. Get AWS Credentials
- In AWS Console: Your Name > Security credentials
- Create access key for "Command Line Interface (CLI)"
- Download the CSV file with your Access Key ID and Secret Access Key

### 3. Set Environment Variables (Windows)
Open Command Prompt as Administrator and run:
```cmd
setx AWS_ACCESS_KEY_ID "your-access-key-id"
setx AWS_SECRET_ACCESS_KEY "your-secret-access-key"
```
Then restart your terminal.

### 4. Configure Application
Edit `config/aws_config.yaml`:
```yaml
enabled: true                        # Change from false
bucket_name: 'your-bucket-name'      # Your S3 bucket name
region: 'us-east-1'                  # Your bucket's region
```

### 5. Install boto3 and Test
```cmd
pip install -r requirements.txt
python -m orchestration.main_pipeline --date=today
```

Check your email for S3 upload status and verify files in AWS S3 Console.

## Files Created/Modified

**New Files:**
- `shared/utils/s3_uploader.py` - S3 upload functionality
- `config/aws_config.yaml` - AWS configuration with detailed documentation
- `docs/S3_SETUP_GUIDE.md` - Comprehensive setup guide
- `docs/S3_QUICK_START.md` - This file

**Modified Files:**
- `requirements.txt` - Added boto3 dependency
- `orchestration/main_pipeline.py` - Integrated S3 upload after successful calculations
- `shared/utils/emailer.py` - Added S3 upload status to email notifications

## How It Works

```
Daily Pipeline Workflow
┌─────────────────────────────────────────┐
│ 1. Fetch market data from FactSet      │
│ 2. Calculate fund weights               │
│ 3. Validate results                     │
│ 4. Save files locally (output/)         │
│ 5. Upload to S3 ← NEW!                  │
│    ├── Versioned CSV                    │
│    ├── Latest CSV                       │
│    ├── Metadata JSON                    │
│    └── Log files                        │
│ 6. Send email with S3 status            │
└─────────────────────────────────────────┘
```

## S3 File Organization

Your S3 bucket will mirror your local structure:

```
your-bucket-name/
├── vanguard_lifestrat/
│   ├── 20251122/
│   │   ├── vanguard_lifestrat_20251122_085806.csv
│   │   ├── vanguard_lifestrat_20251122_085806.json
│   │   ├── vanguard_lifestrat_20251122_latest.csv
│   │   └── logs/
│   │       ├── main_pipeline_20251122.log
│   │       └── vanguard_lifestrat_20251122.log
│   ├── 20251123/
│   └── ...
```

## Cost

**Essentially FREE** under AWS free tier:
- Free tier: 5 GB storage, 2,000 PUT requests/month
- Your usage: ~0.002 GB, ~176 PUT requests/month
- After free tier: < $0.01/month

## Email Notification Example

Your daily email will now include:

```
Fund Calculation Summary - 20251122

Fund                    Status   Runtime  Output File
vanguard_lifestrat      SUCCESS  0.5s     output/vanguard_lifestrat/...

AWS S3 Upload Status
Fund                    Status   Files Uploaded
vanguard_lifestrat      SUCCESS  5/5 files

Files uploaded to S3 are available in the cloud for backup and distribution.
```

## Accessing Files in S3

**AWS Console** (easiest):
- Go to [https://s3.console.aws.amazon.com/](https://s3.console.aws.amazon.com/)
- Click your bucket > Navigate folders > Download files

**AWS CLI**:
```cmd
# List files
aws s3 ls s3://your-bucket-name/vanguard_lifestrat/20251122/

# Download file
aws s3 cp s3://your-bucket-name/vanguard_lifestrat/20251122/file.csv ./local.csv
```

**Python**:
```python
import boto3
s3 = boto3.client('s3')
s3.download_file('bucket-name', 'path/to/file.csv', 'local.csv')
```

## If S3 Upload Fails

The pipeline is **fail-safe**:
- Local files are still generated
- Email is still sent
- S3 failure is logged and reported
- Pipeline doesn't fail (exit code still 0 if calculation succeeded)

**Common Issues:**
- Credentials not set → Set environment variables
- Bucket doesn't exist → Check bucket name in config
- Access denied → Add S3 permissions to IAM user

See [S3_SETUP_GUIDE.md](S3_SETUP_GUIDE.md) troubleshooting section for detailed solutions.

## Disabling S3 Upload

To temporarily disable S3 upload without removing the code:

Edit `config/aws_config.yaml`:
```yaml
enabled: false  # Change to false
```

The pipeline will skip S3 upload and show "S3 upload is currently disabled" in the email.

## Security Notes

- **NEVER** commit AWS credentials to git
- `.env` file is in `.gitignore` (if you use that method)
- Environment variables are the recommended approach for Windows
- Rotate access keys every 90 days
- Enable MFA on your AWS account

## Need Help?

See detailed guide: [S3_SETUP_GUIDE.md](S3_SETUP_GUIDE.md)

Covers:
- Complete step-by-step setup with screenshots descriptions
- Troubleshooting common issues
- Security best practices
- Advanced usage (presigned URLs, Lambda triggers, etc.)
- Cost estimation
- Accessing files programmatically
