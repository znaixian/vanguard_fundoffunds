"""
S3 Uploader Utility
Upload fund calculation files to AWS S3 for cloud backup and distribution

What is S3?
-----------
AWS S3 (Simple Storage Service) is cloud storage from Amazon Web Services.
Think of it like Dropbox for your application - files uploaded to S3 are:
- Stored safely in the cloud (backed up across multiple data centers)
- Accessible from anywhere via URL or AWS tools
- Can be shared with other systems/users
- Automatically versioned if you enable S3 versioning

How this works:
---------------
1. After your calculations generate local CSV files
2. This uploader automatically copies them to your S3 bucket
3. Files are organized in S3 with the same structure: {bucket}/{fund}/{date}/
4. You can access files via AWS Console, AWS CLI, or programmatically
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime


class S3Uploader:
    """
    Handles uploading fund calculation files to AWS S3.

    What you need to use this:
    - An AWS account (free tier available)
    - An S3 bucket created (like a folder in cloud storage)
    - AWS credentials (access key ID and secret access key)
    """

    def __init__(self, config_path: str = 'config/aws_config.yaml'):
        """
        Initialize S3 uploader.

        Args:
            config_path: Path to AWS configuration file containing:
                - bucket_name: Your S3 bucket name
                - region: AWS region (e.g., 'us-east-1')
                - enabled: Whether S3 upload is enabled
        """
        self.logger = logging.getLogger(__name__)

        # Load configuration
        import yaml
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning(f"AWS config not found: {config_path}. S3 upload disabled.")
            self.config = {'enabled': False}

        # Check if S3 upload is enabled
        self.enabled = self.config.get('enabled', False)

        if not self.enabled:
            self.logger.info("S3 upload is disabled in configuration")
            return

        # Get bucket and region from config
        self.bucket_name = self.config.get('bucket_name')
        self.region = self.config.get('region', 'us-east-1')

        if not self.bucket_name:
            self.logger.error("S3 bucket_name not configured. S3 upload disabled.")
            self.enabled = False
            return

        # Initialize AWS S3 client
        # boto3 automatically looks for credentials in these places (in order):
        # 1. Environment variables: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
        # 2. ~/.aws/credentials file (AWS CLI configuration)
        # 3. IAM role if running on AWS EC2
        try:
            self.s3_client = boto3.client('s3', region_name=self.region)
            self.logger.info(f"S3 client initialized. Bucket: {self.bucket_name}, Region: {self.region}")

            # Test connection by checking if bucket exists
            self._verify_bucket_access()

        except NoCredentialsError:
            self.logger.error("AWS credentials not found. S3 upload disabled.")
            self.logger.error("To fix: Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
            self.enabled = False
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            self.enabled = False

    def _verify_bucket_access(self):
        """
        Verify that we can access the S3 bucket.
        This checks if the bucket exists and we have permission to use it.
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"Successfully verified access to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.error(f"S3 bucket does not exist: {self.bucket_name}")
                self.logger.error("To fix: Create the bucket in AWS S3 Console or use AWS CLI")
            elif error_code == '403':
                self.logger.error(f"Access denied to S3 bucket: {self.bucket_name}")
                self.logger.error("To fix: Check your AWS credentials have permission to access this bucket")
            else:
                self.logger.error(f"Cannot access S3 bucket: {e}")
            self.enabled = False

    def upload_file(
        self,
        local_path: Path,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a single file to S3.

        Args:
            local_path: Path to local file (e.g., Path('output/fund/20251120/fund_20251120_123456.csv'))
            s3_key: Path in S3 bucket (e.g., 'vanguard_lifestrat/20251120/fund_20251120_123456.csv')
            metadata: Optional metadata to attach to file in S3

        Returns:
            True if upload successful, False otherwise

        Example:
            uploader.upload_file(
                local_path=Path('output/vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv'),
                s3_key='vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv'
            )

            After this, your file is available in S3 at:
            s3://your-bucket-name/vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv
        """
        if not self.enabled:
            return False

        if not local_path.exists():
            self.logger.error(f"Local file does not exist: {local_path}")
            return False

        try:
            # Prepare upload arguments
            extra_args = {}

            # Add metadata if provided
            if metadata:
                extra_args['Metadata'] = metadata

            # Set content type based on file extension
            suffix = local_path.suffix.lower()
            if suffix == '.csv':
                extra_args['ContentType'] = 'text/csv'
            elif suffix == '.json':
                extra_args['ContentType'] = 'application/json'
            elif suffix == '.log':
                extra_args['ContentType'] = 'text/plain'

            # Upload to S3
            self.logger.info(f"Uploading {local_path.name} to s3://{self.bucket_name}/{s3_key}")

            self.s3_client.upload_file(
                Filename=str(local_path),
                Bucket=self.bucket_name,
                Key=s3_key,
                ExtraArgs=extra_args if extra_args else None
            )

            self.logger.info(f"Successfully uploaded to S3: {s3_key}")
            return True

        except ClientError as e:
            self.logger.error(f"Failed to upload {local_path.name} to S3: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error uploading to S3: {e}")
            return False

    def upload_fund_calculation(
        self,
        fund_name: str,
        date: str,
        output_dir: Path,
        include_logs: bool = False
    ) -> Dict[str, bool]:
        """
        Upload all files from a fund calculation to S3.

        This uploads:
        - Versioned CSV file (the timestamped calculation)
        - Latest CSV file (copy of the most recent calculation)
        - Metadata JSON file (calculation info)
        - Log file (optional)

        Args:
            fund_name: Fund name (e.g., 'vanguard_lifestrat')
            date: Calculation date (YYYYMMDD format)
            output_dir: Local output directory containing files
            include_logs: Whether to upload log files

        Returns:
            Dictionary with upload results: {'file.csv': True/False, ...}

        Example:
            results = uploader.upload_fund_calculation(
                fund_name='vanguard_lifestrat',
                date='20251120',
                output_dir=Path('output/vanguard_lifestrat/20251120')
            )
            # results = {'vanguard_lifestrat_20251120_123456.csv': True, ...}
        """
        if not self.enabled:
            return {}

        results = {}

        # Find all files in the output directory
        if not output_dir.exists():
            self.logger.error(f"Output directory does not exist: {output_dir}")
            return results

        # Upload CSV files (versioned and latest)
        csv_files = list(output_dir.glob(f"{fund_name}_{date}_*.csv"))
        for csv_file in csv_files:
            # Create S3 key: fund_name/date/filename
            s3_key = f"{fund_name}/{date}/{csv_file.name}"

            # Add metadata
            metadata = {
                'fund': fund_name,
                'date': date,
                'upload_timestamp': datetime.now().isoformat()
            }

            success = self.upload_file(csv_file, s3_key, metadata)
            results[csv_file.name] = success

        # Upload JSON metadata files
        json_files = list(output_dir.glob(f"{fund_name}_{date}_*.json"))
        for json_file in json_files:
            s3_key = f"{fund_name}/{date}/{json_file.name}"
            success = self.upload_file(json_file, s3_key)
            results[json_file.name] = success

        # Upload log files if requested
        if include_logs:
            log_dir = Path('logs')
            log_files = [
                log_dir / f"{fund_name}_{date}.log",
                log_dir / f"main_pipeline_{date}.log"
            ]

            for log_file in log_files:
                if log_file.exists():
                    s3_key = f"{fund_name}/{date}/logs/{log_file.name}"
                    success = self.upload_file(log_file, s3_key)
                    results[log_file.name] = success

        # Log summary
        successful = sum(1 for v in results.values() if v)
        total = len(results)
        self.logger.info(f"S3 upload complete: {successful}/{total} files uploaded successfully")

        return results

    def get_s3_url(self, s3_key: str) -> str:
        """
        Get the S3 URL for a file.

        Args:
            s3_key: S3 key (path in bucket)

        Returns:
            S3 URL string

        Example:
            url = uploader.get_s3_url('vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv')
            # Returns: 's3://your-bucket/vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv'
        """
        return f"s3://{self.bucket_name}/{s3_key}"

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a temporary download URL for a file in S3.

        This creates a URL that anyone can use to download the file for a limited time.
        Useful for sharing files with people who don't have AWS access.

        Args:
            s3_key: S3 key (path in bucket)
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            HTTPS URL that can be used to download the file, or None if failed

        Example:
            url = uploader.generate_presigned_url(
                'vanguard_lifestrat/20251120/vanguard_lifestrat_20251120_123456.csv',
                expiration=86400  # 24 hours
            )
            # Returns: 'https://your-bucket.s3.amazonaws.com/vanguard_lifestrat/...?X-Amz-...'
            # You can email this URL to someone and they can download the file
        """
        if not self.enabled:
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            self.logger.error(f"Failed to generate presigned URL: {e}")
            return None
