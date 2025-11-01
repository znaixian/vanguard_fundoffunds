"""
Agent Configuration

Sets up the Anthropic Claude client with tool definitions.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify API key is set
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your_api_key_here':
    raise ValueError(
        "ANTHROPIC_API_KEY not set in .env file. "
        "Please add your API key from https://console.anthropic.com"
    )

# Project configuration
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', os.getcwd()))
MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
MAX_TOKENS = int(os.getenv('CLAUDE_MAX_TOKENS', '8000'))


# Tool definitions in Anthropic format
TOOLS = [
    {
        "name": "run_calculator",
        "description": "Run fund weight calculation for a specific date and fund. This executes the full calculation pipeline including data fetching, weight calculation, and validation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYYMMDD format or 'today' for current date"
                },
                "fund": {
                    "type": "string",
                    "description": "Fund name (e.g., 'vanguard_lifestrat') or omit for all funds"
                }
            },
            "required": ["date"]
        }
    },
    {
        "name": "query_weights",
        "description": "Query historical fund weights from calculation outputs. Retrieves weight data for specific funds, dates, and components.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund": {
                    "type": "string",
                    "description": "Fund name (e.g., 'vanguard_lifestrat')"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYYMMDD format"
                },
                "component": {
                    "type": "string",
                    "description": "Optional component/benchmark ID to filter (e.g., 'LHMN21140' for US Treasury)"
                }
            },
            "required": ["fund", "date"]
        }
    },
    {
        "name": "list_calculations",
        "description": "List available calculation dates for a fund. Shows recent calculation outputs with metadata like file size and modification time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund": {
                    "type": "string",
                    "description": "Fund name (e.g., 'vanguard_lifestrat')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of dates to return (default: 10)"
                }
            },
            "required": ["fund"]
        }
    },
    {
        "name": "validate_weights",
        "description": "Validate fund weights for UCITS compliance and other rules. Checks that weights sum to 100%, no position exceeds 19.25% cap, and other validation rules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund": {
                    "type": "string",
                    "description": "Fund name"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYYMMDD format"
                }
            },
            "required": ["fund", "date"]
        }
    },
    {
        "name": "analyze_weight_trends",
        "description": "Analyze how a component's weight has changed over time. Provides statistics including mean, volatility, trend direction, and UCITS compliance status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund": {
                    "type": "string",
                    "description": "Fund name"
                },
                "component": {
                    "type": "string",
                    "description": "Component/benchmark ID (e.g., 'LHMN21140')"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYYMMDD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYYMMDD format"
                }
            },
            "required": ["fund", "component", "start_date", "end_date"]
        }
    }
]


SYSTEM_PROMPT = """You are an AI assistant for the Vanguard fund calculation workflow.

Your expertise includes:
- Running and monitoring daily fund calculations
- Validating UCITS compliance (19.25% position caps)
- Analyzing historical weight data and trends
- Interpreting calculation results and troubleshooting errors
- Understanding waterfall calculation methodology for multi-tier portfolios
- Performing quantitative analysis on fund weights and allocations

When users ask questions:
1. Use the appropriate tools to fetch data
2. Provide clear, concise analysis with specific numbers and percentages
3. Highlight any compliance issues, warnings, or red flags
4. Suggest remediation steps for errors or validation failures
5. Explain calculations and methodology when asked
6. Be proactive in identifying potential issues

Available Tools:
- run_calculator: Execute fund calculations for a specific date/fund
- query_weights: Retrieve historical weight data
- list_calculations: Show available calculation dates
- validate_weights: Check UCITS compliance and validation rules
- analyze_weight_trends: Analyze weight changes over time periods

You understand:
- UCITS regulations and the 19.25% position cap
- Waterfall calculation methodology (fixed tier 1, market-cap weighted tiers)
- Multi-asset portfolio construction (LSE20/40/60/80 profiles)
- Risk metrics and portfolio analysis

Always provide actionable insights and be concise in your responses."""
