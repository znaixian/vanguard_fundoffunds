"""
Test S3 Connection
Quick script to verify AWS credentials and S3 bucket access
"""

import sys
from shared.utils.s3_uploader import S3Uploader

def test_s3_connection():
    """Test S3 connection and configuration."""

    print("=" * 70)
    print("AWS S3 Connection Test")
    print("=" * 70)
    print()

    # Initialize S3 uploader
    print("Step 1: Initializing S3 Uploader...")
    uploader = S3Uploader('config/aws_config.yaml')
    print()

    # Check if enabled
    if not uploader.enabled:
        print("ERROR: S3 upload is disabled or initialization failed.")
        print("Check the logs above for details.")
        return False

    print("SUCCESS: S3 Uploader initialized successfully!")
    print(f"  - Bucket: {uploader.bucket_name}")
    print(f"  - Region: {uploader.region}")
    print()

    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print()
    print("Your S3 connection is working correctly.")
    print("You can now run the full pipeline with S3 upload enabled.")
    print()

    return True

if __name__ == '__main__':
    success = test_s3_connection()
    sys.exit(0 if success else 1)
