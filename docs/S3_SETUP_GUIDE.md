# AWS S3 Setup Guide for Fund Calculations

This guide will walk you through setting up AWS S3 cloud storage for your fund calculation files. **No prior AWS experience required!**

## What is AWS S3?

Think of **AWS S3** (Simple Storage Service) as **cloud storage** for your files - similar to Dropbox or Google Drive, but designed for applications.

**Benefits:**
- **Automatic Backup**: Files are safely stored in Amazon's data centers
- **Accessibility**: Access your files from anywhere, not just your local machine
- **Sharing**: Easy to share files with other systems or people
- **Durability**: AWS guarantees 99.999999999% durability (your files won't get lost)
- **Versioning**: Optionally keeps old versions of files automatically

## Cost

**Good news**: Your usage will likely be **FREE** or cost less than $0.01/month!

AWS offers a **free tier** for the first 12 months:
- 5 GB of storage (you'll use ~0.002 GB/month)
- 20,000 GET requests, 2,000 PUT requests per month (you'll use ~176/month)

After the free tier, S3 is very inexpensive for small files like yours.

---

## Step-by-Step Setup

### Step 1: Create an AWS Account

1. Go to [https://aws.amazon.com/](https://aws.amazon.com/)
2. Click **"Create an AWS Account"**
3. Fill in your information:
   - Email address
   - Password
   - AWS account name (can be anything, like "MyCompany-Funds")
4. Enter your credit card information
   - Required even for free tier
   - You won't be charged unless you exceed free tier limits
5. Verify your phone number
6. Choose **Basic Support - Free**
7. Complete sign-up

### Step 2: Create an S3 Bucket

**What's a bucket?** Think of it as a top-level folder in the cloud where your files will be stored.

1. **Log into AWS Console**
   - Go to [https://console.aws.amazon.com/](https://console.aws.amazon.com/)
   - Sign in with your AWS account credentials

2. **Navigate to S3**
   - In the top search bar, type "S3"
   - Click on "S3" in the search results

3. **Create Bucket**
   - Click the orange **"Create bucket"** button

4. **Bucket Settings**

   **Bucket name** (must be globally unique):
   - Example: `vanguard-fundoffunds-yourcompany-prod`
   - Example: `mycompany-fund-calculations`
   - Rules: 3-63 characters, lowercase letters, numbers, hyphens only
   - Try your company name + "fund-calculations"

   **AWS Region** (choose the closest to you):
   - US East (Virginia): `us-east-1` (most common, usually cheapest)
   - US West (Oregon): `us-west-2`
   - Europe (Ireland): `eu-west-1`
   - Asia Pacific (Singapore): `ap-southeast-1`

   **Block Public Access settings**:
   - ✅ **KEEP "Block all public access" CHECKED** (recommended for security)
   - This means only people with AWS credentials can access your files

   **Bucket Versioning**:
   - ✅ **Enable** (recommended)
   - This automatically keeps old versions of files if you overwrite them

   **Encryption**:
   - Leave as default (Server-side encryption with Amazon S3 managed keys)

5. Click **"Create bucket"**

6. **Write down your bucket name** - you'll need it later!

### Step 3: Create AWS Access Keys (Credentials)

**What are access keys?** Think of them as a username/password pair that allows your application to access AWS.

1. **Navigate to IAM (Identity and Access Management)**
   - In AWS Console, click your account name (top right corner)
   - Click **"Security credentials"**
   - OR search for "IAM" in the top search bar

2. **Create Access Key**
   - Scroll down to **"Access keys"** section
   - Click **"Create access key"**

3. **Select Use Case**
   - Choose **"Command Line Interface (CLI)"**
   - Check the acknowledgment box
   - Click **"Next"**

4. **Optional Description**
   - Description: "Vanguard Fund Calculations"
   - Click **"Create access key"**

5. **IMPORTANT: Save Your Keys NOW**

   You'll see two values:
   - **Access Key ID**: `AKIAIOSFODNN7EXAMPLE` (example)
   - **Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` (example)

   ⚠️ **WARNING**: You can **NEVER** see the Secret Access Key again after you close this page!

   **Do this immediately:**
   - Click **"Download .csv file"** and save it somewhere safe
   - Copy both keys to a secure location (password manager, encrypted note, etc.)
   - **DO NOT** commit these to git or share them publicly

6. Click **"Done"**

### Step 4: Install AWS SDK (boto3)

1. Open **Windows Terminal** or **Command Prompt**

2. Navigate to your project directory:
   ```cmd
   cd C:\Users\ncarucci\Documents\Gitfolder\vanguard-fundoffunds
   ```

3. Install boto3:
   ```cmd
   pip install boto3
   ```

   Or install all requirements (recommended):
   ```cmd
   pip install -r requirements.txt
   ```

### Step 5: Configure AWS Credentials

You have **three options** for storing your AWS credentials. Choose **ONE**:

#### Option A: Environment Variables (Recommended for Windows)

1. **Open Command Prompt as Administrator**
   - Press Windows key
   - Type "cmd"
   - Right-click "Command Prompt"
   - Select "Run as administrator"

2. **Set environment variables** (replace with your actual keys):
   ```cmd
   setx AWS_ACCESS_KEY_ID "AKIAIOSFODNN7EXAMPLE"
   setx AWS_SECRET_ACCESS_KEY "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
   ```

3. **Restart your terminal/command prompt** (required for changes to take effect)

4. **Verify** (in new terminal):
   ```cmd
   echo %AWS_ACCESS_KEY_ID%
   ```
   Should display your access key ID

#### Option B: Using .env File (Alternative)

1. Create a file named `.env` in your project root:
   ```
   C:\Users\ncarucci\Documents\Gitfolder\vanguard-fundoffunds\.env
   ```

2. Add these lines (replace with your actual keys):
   ```
   AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   ```

3. **Make sure `.env` is in `.gitignore`** (it already should be)

4. Add this to the top of `run_daily_calculations.bat`:
   ```batch
   @echo off
   :: Load environment variables from .env file
   for /f "tokens=*" %%a in (.env) do (set %%a)
   ```

#### Option C: AWS CLI Configuration (Advanced)

1. Install AWS CLI: [https://aws.amazon.com/cli/](https://aws.amazon.com/cli/)

2. Run:
   ```cmd
   aws configure
   ```

3. Enter when prompted:
   - AWS Access Key ID: `AKIAIOSFODNN7EXAMPLE`
   - AWS Secret Access Key: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
   - Default region name: `us-east-1` (or your chosen region)
   - Default output format: `json`

### Step 6: Configure the Application

1. **Edit `config/aws_config.yaml`**

   ```yaml
   enabled: true  # Change from 'false' to 'true'

   bucket_name: 'your-bucket-name-here'  # Replace with your actual bucket name

   region: 'us-east-1'  # Replace with your chosen region
   ```

2. **Save the file**

### Step 7: Test the Setup

1. **Run a test calculation**:
   ```cmd
   python -m orchestration.main_pipeline --date=today
   ```

2. **Check the output**:
   - Look for log messages like:
     ```
     S3 client initialized. Bucket: your-bucket-name, Region: us-east-1
     Successfully verified access to S3 bucket: your-bucket-name
     Uploading vanguard_lifestrat files to S3
     S3 upload successful: 5/5 files uploaded
     ```

3. **Check your email**:
   - You should see an "AWS S3 Upload Status" section showing successful uploads

4. **Verify in AWS Console**:
   - Go to [https://s3.console.aws.amazon.com/](https://s3.console.aws.amazon.com/)
   - Click your bucket name
   - You should see folders like:
     ```
     vanguard_lifestrat/
       20251122/
         vanguard_lifestrat_20251122_123456.csv
         vanguard_lifestrat_20251122_123456.json
         vanguard_lifestrat_20251122_latest.csv
         logs/
           main_pipeline_20251122.log
           vanguard_lifestrat_20251122.log
     ```

---

## How Files Are Organized in S3

Your S3 bucket will mirror your local `output/` directory structure:

```
your-bucket-name/
├── vanguard_lifestrat/
│   ├── 20251120/
│   │   ├── vanguard_lifestrat_20251120_085806.csv
│   │   ├── vanguard_lifestrat_20251120_085806.json
│   │   ├── vanguard_lifestrat_20251120_latest.csv
│   │   └── logs/
│   │       ├── main_pipeline_20251120.log
│   │       └── vanguard_lifestrat_20251120.log
│   ├── 20251121/
│   │   └── ...
│   └── 20251122/
│       └── ...
└── fund_2/
    └── 20251120/
        └── ...
```

---

## How to Access Your Files in S3

### Method 1: AWS Console (Web Browser)

**Easy for viewing/downloading individual files**

1. Go to [https://s3.console.aws.amazon.com/](https://s3.console.aws.amazon.com/)
2. Click your bucket name
3. Navigate folders by clicking them
4. Download files by clicking the filename, then clicking "Download"

### Method 2: AWS CLI (Command Line)

**Good for bulk operations**

**List files:**
```cmd
aws s3 ls s3://your-bucket-name/vanguard_lifestrat/20251120/
```

**Download a file:**
```cmd
aws s3 cp s3://your-bucket-name/vanguard_lifestrat/20251120/file.csv C:\Downloads\file.csv
```

**Download entire folder:**
```cmd
aws s3 sync s3://your-bucket-name/vanguard_lifestrat/20251120/ C:\Downloads\20251120\
```

### Method 3: Python (boto3)

**Good for automation**

```python
import boto3

s3 = boto3.client('s3')

# Download a file
s3.download_file(
    'your-bucket-name',
    'vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv',
    'local_file.csv'
)

# List files in a "folder"
response = s3.list_objects_v2(
    Bucket='your-bucket-name',
    Prefix='vanguard_lifestrat/20251120/'
)

for obj in response.get('Contents', []):
    print(obj['Key'])
```

### Method 4: Generate Shareable Links

**Good for sharing files with people who don't have AWS access**

The S3Uploader class has a method to generate temporary download URLs:

```python
from shared.utils.s3_uploader import S3Uploader

uploader = S3Uploader('config/aws_config.yaml')

# Generate a URL valid for 24 hours
url = uploader.generate_presigned_url(
    'vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv',
    expiration=86400  # 24 hours in seconds
)

print(url)
# Returns: https://your-bucket.s3.amazonaws.com/vanguard_lifestrat/...?X-Amz-...

# You can email this URL to anyone and they can download the file
# No AWS account needed to download (as long as URL hasn't expired)
```

---

## Troubleshooting

### Problem: "NoCredentialsError"

**Cause**: AWS credentials not found

**Solutions**:
1. If using environment variables:
   - Check: `echo %AWS_ACCESS_KEY_ID%`
   - Make sure you restarted terminal after running `setx`
   - Verify no extra spaces in the keys

2. If using .env file:
   - Check file is named exactly `.env` (not `.env.txt`)
   - Check file is in project root directory
   - Verify no extra spaces or quotes around values

3. Verify credentials are correct (no typos)

### Problem: "Bucket does not exist"

**Cause**: Bucket name typo or wrong region

**Solutions**:
1. In AWS Console, go to S3 and verify bucket name (case-sensitive!)
2. Check `config/aws_config.yaml` - bucket name must match exactly
3. Verify bucket region in AWS Console matches `region` in config file

### Problem: "Access Denied"

**Cause**: Your AWS user doesn't have permission to access the bucket

**Solutions**:
1. In AWS Console, go to **IAM** > **Users** > Your user
2. Click **"Add permissions"** > **"Attach policies directly"**
3. Search for `AmazonS3FullAccess`
4. Check the box and click **"Add permissions"**

Alternatively, create a more restrictive policy (recommended for production):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

### Problem: "Invalid bucket name"

**Cause**: Bucket names have strict rules

**Rules**:
- 3-63 characters
- Only lowercase letters, numbers, hyphens (-)
- Must start with letter or number
- No underscores, spaces, or special characters

**Example valid names**:
- `vanguard-fundoffunds-prod`
- `mycompany-fund-calculations`
- `fund-weights-2025`

**Example invalid names**:
- `Vanguard_FundOfFunds` (uppercase, underscore)
- `my bucket` (space)
- `fund@calculations` (special character)

### Problem: Files not appearing in S3

**Check**:
1. Look at logs for S3 upload errors:
   ```
   logs/main_pipeline_20251122.log
   ```
2. Check email for S3 upload status
3. Verify `enabled: true` in `config/aws_config.yaml`
4. Check calculation was successful (S3 only uploads successful calculations)

---

## Security Best Practices

### 1. Never Commit Credentials to Git

**What NOT to do**:
- ❌ Put AWS keys directly in `aws_config.yaml`
- ❌ Commit `.env` file to git
- ❌ Share keys in Slack, email, or other insecure channels

**What TO do**:
- ✅ Use environment variables or `.env` file
- ✅ Verify `.env` is in `.gitignore`
- ✅ Store credentials in a password manager
- ✅ Never share Secret Access Key with anyone

### 2. Use Least-Privilege IAM Policies

**Instead of** `AmazonS3FullAccess` (which gives access to ALL S3 buckets):

Create a custom policy that only allows access to YOUR specific bucket (see "Access Denied" solution above).

### 3. Enable MFA (Multi-Factor Authentication)

**Protects against credential theft**

1. In AWS Console, click your name > **Security credentials**
2. Under **Multi-factor authentication (MFA)**, click **Assign MFA device**
3. Choose **Authenticator app** (like Google Authenticator or Authy)
4. Follow setup instructions

### 4. Rotate Access Keys Periodically

**Create new keys every 90 days**

1. Create new access key
2. Update environment variables with new keys
3. Test that everything still works
4. Delete old access key in AWS Console

### 5. Enable S3 Bucket Versioning

**Already recommended in Step 2**

- Protects against accidental deletion
- Keeps old versions of files automatically
- Can restore previous versions if needed

### 6. Monitor Costs

**Set up billing alerts**

1. AWS Console > **Billing Dashboard**
2. **Budgets** > **Create budget**
3. Set alert for $1 or $5 per month
4. Get email if costs exceed threshold

---

## What Happens When the Batch File Runs

When `run_daily_calculations.bat` runs (scheduled for 6:00 AM):

1. **Fetch market data** from FactSet API
2. **Calculate fund weights** for all active funds
3. **Validate results** (UCITS compliance, sum checks)
4. **Save files locally** to `output/fund/date/`
5. **Upload to S3** ← NEW!
   - Uploads versioned CSV
   - Uploads latest CSV
   - Uploads metadata JSON
   - Uploads log files
6. **Send email** with results and S3 upload status
7. **Exit** with status code

**If S3 upload is disabled** (enabled: false in config):
- Steps 1-4 and 6-7 still happen
- S3 upload is skipped
- Email shows "S3 upload is currently disabled"

**If S3 upload fails**:
- Pipeline continues (doesn't fail the entire calculation)
- Local files are still saved
- Email shows partial S3 upload status
- Error logged for troubleshooting

---

## Advanced: Accessing S3 from Other Systems

### Scenario: Another application needs to download the daily files

**Option 1: AWS SDK in that application**

If the other application can use AWS SDK:

```python
# In another Python application
import boto3

s3 = boto3.client('s3')
s3.download_file(
    'your-bucket-name',
    'vanguard_lifestrat/20251122/vanguard_lifestrat_20251122_latest.csv',
    'local_file.csv'
)
```

**Option 2: S3 Event Notifications**

Configure S3 to automatically notify when new files are uploaded:

1. S3 Console > Your bucket > **Properties**
2. **Event notifications** > **Create event notification**
3. Choose event type: **"All object create events"**
4. Destination: **SNS topic**, **SQS queue**, or **Lambda function**

Now whenever a file is uploaded to S3, it can trigger an automatic action.

**Option 3: AWS Lambda Function**

Automatically process files when uploaded:

1. Create Lambda function
2. Set trigger: S3 bucket, object create events
3. Lambda function runs automatically when file uploaded
4. Can send file somewhere else, process it, send notification, etc.

---

## Summary

You've now set up AWS S3 cloud backup for your fund calculation files!

**What you accomplished**:
- ✅ Created AWS account
- ✅ Created S3 bucket
- ✅ Generated AWS credentials
- ✅ Configured application to upload to S3
- ✅ Tested the setup

**What happens now**:
- Every time your batch file runs, calculation files are automatically uploaded to S3
- Email notifications include S3 upload status
- Files are safely backed up in the cloud
- You can access files from AWS Console or programmatically

**Next steps**:
- Monitor first few runs to ensure S3 uploads work correctly
- Set up billing alerts to monitor costs
- Consider enabling S3 bucket versioning if you haven't already
- Share S3 bucket access with team members if needed

---

## Need Help?

**AWS Documentation**:
- S3 Getting Started: [https://docs.aws.amazon.com/s3/](https://docs.aws.amazon.com/s3/)
- boto3 Documentation: [https://boto3.amazonaws.com/v1/documentation/api/latest/index.html](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

**AWS Support**:
- Free tier includes AWS Support (basic)
- [https://support.aws.amazon.com/](https://support.aws.amazon.com/)

**Check Configuration Files**:
- `config/aws_config.yaml` - Has detailed comments and troubleshooting tips
- `shared/utils/s3_uploader.py` - Well-documented code with examples

**Review Logs**:
- `logs/main_pipeline_YYYYMMDD.log` - Contains S3 upload details and errors
