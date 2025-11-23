# Streamlit Community Cloud Deployment Guide

This guide walks you through deploying the Vanguard Agent UI to Streamlit Community Cloud.

## Prerequisites

- Code pushed to GitHub repository: `znaixian/vanguard_fundoffunds`
- Anthropic API key from https://console.anthropic.com
- FactSet API credentials (username and API key)
- (Optional) AWS credentials if using S3 uploads

## Step-by-Step Deployment

### 1. Access Streamlit Community Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account (znaixian)
3. Click **"New app"** button

### 2. Configure App Settings

Fill in the deployment form:

- **Repository**: `znaixian/vanguard_fundoffunds`
- **Branch**: `main`
- **Main file path**: `vanguard_agent_ui.py`

### 3. Configure Secrets (CRITICAL)

Click **"Advanced settings"** and add your secrets:

#### Minimum Required Secrets:

```toml
# Anthropic API
ANTHROPIC_API_KEY = "sk-ant-api03-your_actual_key_here"

# Project paths (use Streamlit mount path)
PROJECT_ROOT = "/mount/src/vanguard_fundoffunds"
OUTPUT_DIR = "output"
LOGS_DIR = "logs"

# FactSet API
FACTSET_USERNAME = "your_factset_username"
FACTSET_API_KEY = "your_factset_api_key"
```

#### Optional Secrets (if using S3):

```toml
# AWS Credentials
AWS_ACCESS_KEY_ID = "your_aws_access_key_id"
AWS_SECRET_ACCESS_KEY = "your_aws_secret_access_key"
AWS_DEFAULT_REGION = "us-east-1"
S3_BUCKET_NAME = "vanguard-fundoffunds-prod"
S3_ENABLED = "true"
```

**See `.streamlit/secrets.toml.example` for complete list of available secrets.**

### 4. Update Code to Read Streamlit Secrets

The app needs to be updated to read from `st.secrets` when deployed. Here's the pattern:

```python
import streamlit as st
import os

# Check if running on Streamlit Cloud
if "ANTHROPIC_API_KEY" in st.secrets:
    # Running on Streamlit Cloud - use st.secrets
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
    PROJECT_ROOT = Path(st.secrets.get("PROJECT_ROOT", "/mount/src/vanguard_fundoffunds"))
else:
    # Running locally - use environment variables
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", os.getcwd()))
```

### 5. Deploy

1. Click **"Deploy"**
2. Wait for deployment (usually 2-5 minutes)
3. Your app will be available at: `https://[your-app-name].streamlit.app`

## Important Notes

### File Paths on Streamlit Cloud

- Streamlit mounts your repo at: `/mount/src/vanguard_fundoffunds`
- Set `PROJECT_ROOT` to this path in secrets
- All relative paths will be relative to this directory

### File System Limitations

- Streamlit Cloud filesystem is **ephemeral** - files are lost on restart
- Output files generated during runtime won't persist
- For persistent storage, you **must** use S3 or external storage
- The UI is best for testing queries, not for production calculations that need file output

### Performance Considerations

- Streamlit Cloud has resource limits (free tier)
- Large calculations may timeout or run slowly
- Consider using for demo/query purposes, not production calculations

### Security

- Never commit secrets to GitHub
- All secrets should be in Streamlit's Secrets Management
- `.env` file is gitignored - secrets won't be pushed

## Troubleshooting

### "Module not found" errors

- Check that `requirements.txt` includes all dependencies
- Streamlit Cloud installs from `requirements.txt` automatically

### "Permission denied" errors

- Check `PROJECT_ROOT` is set to `/mount/src/vanguard_fundoffunds`
- Ensure output directories are writable (may need to check paths)

### API key errors

- Verify secrets are configured correctly in Streamlit settings
- Check that code is reading from `st.secrets` when deployed
- Confirm API keys are valid

### Calculation timeout

- Streamlit Cloud has execution time limits
- Consider disabling long-running operations for cloud deployment
- Use for queries/validation, not full production calculations

## Local Testing with Streamlit

To test locally before deploying:

1. Create `.streamlit/secrets.toml` (gitignored):
```toml
ANTHROPIC_API_KEY = "your_key_here"
PROJECT_ROOT = "C:\\Users\\ncarucci\\Documents\\Gitfolder\\vanguard-fundoffunds"
```

2. Run locally:
```bash
streamlit run vanguard_agent_ui.py
```

3. Access at: http://localhost:8501

## Updating Your Deployment

After pushing changes to GitHub:

1. Streamlit Cloud auto-detects changes
2. Click **"Reboot app"** in Streamlit Cloud dashboard
3. Or wait for automatic reboot (usually within minutes)

## Alternatives to Streamlit Cloud

If Streamlit Cloud doesn't meet your needs:

- **Heroku**: More control, paid plans available
- **AWS EC2**: Full control, requires more setup
- **Docker + Cloud Run**: Containerized deployment
- **On-premises**: Host on company servers

See `docs/DEPLOYMENT_OPTIONS.md` for more details (if available).

## Support

- Streamlit Docs: https://docs.streamlit.io/
- Streamlit Community: https://discuss.streamlit.io/
- This project's issues: https://github.com/znaixian/vanguard_fundoffunds/issues
