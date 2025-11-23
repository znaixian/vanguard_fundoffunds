# Windows Claude Agent Workaround

## Issue

The `claude-agent-sdk` has difficulty executing Claude Code CLI on Windows because:
- Windows subprocess can't execute .CMD files directly
- The SDK uses `asyncio.create_subprocess_exec` which requires .exe files

## Solution

Use the **Anthropic Python SDK** directly instead of the agent SDK. This works perfectly on Windows and doesn't require the CLI.

### Install

```bash
pip install anthropic
```

### Example Implementation

```python
import os
from anthropic import Anthropic

# Load API key
from dotenv import load_dotenv
load_dotenv()

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Simple query
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=8000,
    messages=[
        {"role": "user", "content": "What is 2+2?"}
    ]
)

print(response.content[0].text)
```

### For Tool Calling

```python
import json

def run_calculator(date, fund=None):
    """Your calculator function"""
    from orchestration.main_pipeline import DailyPipeline
    pipeline = DailyPipeline(date)
    exit_code = pipeline.run(fund_filter=fund)
    return {"status": exit_code, "results": pipeline.results}

# Define tools
tools = [
    {
        "name": "run_calculator",
        "description": "Run fund weight calculation",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYYMMDD format"},
                "fund": {"type": "string", "description": "Fund name"}
            },
            "required": ["date"]
        }
    }
]

# Use with Claude
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=8000,
    tools=tools,
    messages=[
        {"role": "user", "content": "Run today's calculation"}
    ]
)

# Handle tool calls
if response.stop_reason == "tool_use":
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "run_calculator":
                result = run_calculator(**block.input)
                # Send result back to Claude
                print(json.dumps(result, indent=2))
```

## Next Steps

Would you like me to:
1. Rewrite the agent using the Anthropic SDK directly (recommended for Windows)
2. Or keep troubleshooting the claude-agent-sdk CLI issue?

The direct SDK approach is more reliable, gives you more control, and works perfectly on Windows.
