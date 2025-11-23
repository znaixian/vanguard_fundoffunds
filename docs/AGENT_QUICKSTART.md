# Claude Agent Quick Start Guide

## Step 1: Add Your API Key

1. Open `.env` file in the project root
2. Replace `your_api_key_here` with your actual Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
   ```

## Step 2: Test the Installation

```bash
python vanguard_agent.py
```

You should see the welcome screen!

## Step 3: Try Some Queries

Once the agent starts, try these commands:

### Basic Queries
```
list the last 5 calculations
what can you help me with?
explain the UCITS cap
```

### Data Queries (if you have output data)
```
show me calculations for vanguard_lifestrat
what was the weight of LHMN21140 on 20251022?
```

### Run Calculations (requires FactSet API access)
```
run today's calculation
validate yesterday's results
```

## What You Built

```
vanguard-fundoffunds/
├── agent/
│   ├── __init__.py
│   ├── main.py                    # Interactive session
│   ├── config.py                  # Agent setup
│   ├── README.md                  # Documentation
│   └── tools/
│       ├── __init__.py
│       ├── calculator_tools.py    # Run calculations
│       ├── query_tools.py         # Query data
│       ├── validation_tools.py    # Validate results
│       └── analysis_tools.py      # Analyze trends
├── vanguard_agent.py              # Entry point (run this!)
├── .env                           # Your API key (add it here!)
└── .env.example                   # Template
```

## Next Steps

1. **Get your API key** from https://console.anthropic.com
2. **Add it to `.env`** (replace `your_api_key_here`)
3. **Run the agent**: `python vanguard_agent.py`
4. **Ask questions** about your fund calculations!

## Branch Information

You're on branch: `feature/claude-agent-integration`

When ready to commit:
```bash
git add .
git commit -m "Add Claude Agent integration with custom tools"
git push origin feature/claude-agent-integration
```

## Need Help?

- Check `agent/README.md` for detailed documentation
- Review tool implementations in `agent/tools/`
- Check Claude Agent SDK docs: https://docs.anthropic.com/en/docs/claude-code/sdk
