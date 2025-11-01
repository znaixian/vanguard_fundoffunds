# Vanguard Fund Calculation AI Agent

An interactive AI assistant powered by Claude Sonnet 4.5 for managing and analyzing the Vanguard fund calculation workflow.

## Features

- **Run Calculations**: Execute fund weight calculations for specific dates
- **Validate Results**: Check UCITS compliance and validation rules
- **Query Data**: Retrieve historical weight data and calculation outputs
- **Analyze Trends**: Perform statistical analysis on weight changes over time
- **Natural Language Interface**: Ask questions in plain English

## Setup

### 1. Install Dependencies

Already done if you ran `pip install -r requirements.txt` from the project root.

### 2. Configure API Key

1. Get your API key from https://console.anthropic.com
2. Open `.env` in the project root
3. Replace `your_api_key_here` with your actual API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-your_actual_key_here
   ```

### 3. Run the Agent

From the project root:
```bash
python vanguard_agent.py
```

## Usage Examples

### Running Calculations
```
You: Run today's calculation for vanguard_lifestrat
You: Run calculations for all funds on 20250821
```

### Querying Data
```
You: Show me the latest calculations for vanguard_lifestrat
You: What was the weight of LHMN21140 on 20250820?
You: List the last 5 calculation dates
```

### Validation
```
You: Validate yesterday's results
You: Check UCITS compliance for today's calculation
You: Are there any positions close to the 19.25% cap?
```

### Analysis
```
You: Analyze the US Treasury weight trend over the last month
You: Show me how LHMN21140 has changed over the last week
You: Which component has the highest volatility?
```

### General Questions
```
You: Explain the waterfall calculation methodology
You: What is the UCITS cap and why does it matter?
You: How do I troubleshoot a validation failure?
```

## Architecture

```
agent/
├── __init__.py           # Package initialization
├── main.py              # Interactive session loop
├── config.py            # Agent configuration and setup
└── tools/               # Custom tools (MCP servers)
    ├── __init__.py
    ├── calculator_tools.py    # Run calculations
    ├── query_tools.py         # Query historical data
    ├── validation_tools.py    # Validate results
    └── analysis_tools.py      # Trend analysis
```

## Available Tools

### Calculator Tools
- `run_calculator`: Execute fund weight calculations

### Query Tools
- `query_weights`: Retrieve weight data from outputs
- `list_calculations`: List available calculation dates

### Validation Tools
- `validate_weights`: Check UCITS compliance and validation rules

### Analysis Tools
- `analyze_weight_trends`: Analyze weight changes over time

## Adding New Tools

To add a new tool:

1. Create a function decorated with `@tool` in the appropriate module under `agent/tools/`
2. Import it in `agent/tools/__init__.py`
3. Add it to the `tools` list in `agent/config.py`
4. Add the tool name to `allowed_tools` in `agent/config.py`

Example:
```python
# In agent/tools/analysis_tools.py
from claude_agent_sdk import tool

@tool("my_new_tool", "Description", {"param": str})
async def my_new_tool(args):
    # Implementation
    return {"content": [{"type": "text", "text": "Result"}]}
```

## Troubleshooting

### API Key Error
```
ValueError: ANTHROPIC_API_KEY not set in .env file
```
**Solution**: Edit `.env` and add your API key from https://console.anthropic.com

### Import Errors
```
ModuleNotFoundError: No module named 'claude_agent_sdk'
```
**Solution**: Run `pip install -r requirements.txt`

### Tool Execution Errors
- Check that the working directory is the project root
- Verify that output files exist in `output/` directory
- Check logs in `logs/` directory for detailed error messages

## Advanced Usage

### Programmatic Usage

You can also use the agent programmatically:

```python
import asyncio
from agent.config import create_vanguard_agent
from claude_agent_sdk import ClaudeSDKClient

async def run_query(prompt: str):
    options = create_vanguard_agent()

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            # Process message
            pass

asyncio.run(run_query("Run today's calculation"))
```

## License

Part of the Vanguard Fund Calculation System.
