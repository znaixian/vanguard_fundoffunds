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
        "description": "Validate EXISTING fund weight calculations for UCITS compliance. This reads the already-calculated output file and checks: 1) Each portfolio sums to 100%, 2) No position exceeds 19.25% cap, 3) Other validation rules. IMPORTANT: This does NOT run new calculations - it validates existing output files. Use this after run_calculator or to check historical calculations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fund": {
                    "type": "string",
                    "description": "Fund name"
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYYMMDD format of the EXISTING calculation to validate"
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


SYSTEM_PROMPT = """You are an AI assistant for Vanguard fund calculations.

Expertise: Fund calculations, UCITS compliance (19.25% cap), weight analysis, waterfall methodology.

Tools available:
- run_calculator: Execute NEW calculations (fetches data, calculates weights, validates, saves output)
- query_weights: Get historical data from EXISTING calculations
- list_calculations: Show available calculation dates
- validate_weights: Check UCITS compliance of EXISTING calculation files (does NOT run new calculations)
- analyze_weight_trends: Analyze weight trends over time

IMPORTANT CONTEXT AWARENESS:
- When a user runs calculations in the conversation and then asks to validate, use the SAME date from the calculation you just ran
- Do NOT re-run calculations if you just ran them - validate_weights reads existing files
- Remember what date/fund was used in previous tool calls in the same conversation

UCITS COMPLIANCE:
- Each portfolio (LSE20, LSE40, LSE60, LSE80) is separate and must sum to 100% independently
- Maximum position weight: 19.25%
- Positions AT exactly 19.25% are COMPLIANT and by design - this is the cap being used correctly, not a warning
- Only warn if positions are CLOSE to (but not at) 19.25%, as they might exceed on next calculation

Provide clear, concise analysis with specific numbers. For validation results:
- Show each portfolio separately with its 100% total
- Mark positions at 19.25% as "At UCITS cap (compliant)" not as warnings
- Only flag actual compliance issues"""
