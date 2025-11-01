"""
Query Tools

Tools for querying historical fund calculation data.
"""

import os
from typing import Any, Dict
from pathlib import Path
from datetime import datetime
import pandas as pd

# Project paths
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', os.getcwd()))
OUTPUT_DIR = PROJECT_ROOT / os.getenv('OUTPUT_DIR', 'output')


def query_weights(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query historical fund weights.

    Args:
        args: Dictionary containing:
            - fund: Fund name (e.g., 'vanguard_lifestrat')
            - date: Date in YYYYMMDD format
            - component: Optional component/benchmark ID to filter

    Returns:
        Weight data as formatted table
    """
    try:
        fund = args["fund"]
        date = args["date"]
        component = args.get("component")

        # Construct file path
        output_file = OUTPUT_DIR / fund / date / f"{fund}_{date}_latest.csv"

        if not output_file.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"No data found for {fund} on {date}\n"
                           f"Expected file: {output_file}"
                }],
                "is_error": True
            }

        # Read data
        df = pd.read_csv(output_file)

        # Filter by component if specified
        if component:
            df = df[df['Benchmark ID'] == component]
            if df.empty:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Component '{component}' not found in {fund} on {date}"
                    }],
                    "is_error": True
                }

        # Format output
        result_text = f"Fund: {fund}\n"
        result_text += f"Date: {date}\n"
        if component:
            result_text += f"Component: {component}\n"
        result_text += f"\nRecords: {len(df)}\n\n"
        result_text += df.to_string(index=False)

        return {
            "content": [{"type": "text", "text": result_text}]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error querying weights: {str(e)}"}],
            "is_error": True
        }


def list_calculations(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    List available calculation outputs.

    Args:
        args: Dictionary containing:
            - fund: Fund name (e.g., 'vanguard_lifestrat')
            - limit: Maximum number of dates to return (default: 10)

    Returns:
        List of available dates with metadata
    """
    try:
        fund = args["fund"]
        limit = args.get("limit", 10)

        fund_dir = OUTPUT_DIR / fund

        if not fund_dir.exists():
            return {
                "content": [{
                    "type": "text",
                    "text": f"No output directory found for fund: {fund}"
                }],
                "is_error": True
            }

        # Get all date directories
        date_dirs = sorted([d for d in fund_dir.iterdir() if d.is_dir()], reverse=True)
        date_dirs = date_dirs[:limit]

        result_text = f"Available calculations for {fund} (showing {len(date_dirs)} most recent):\n\n"

        for date_dir in date_dirs:
            date = date_dir.name
            latest_file = date_dir / f"{fund}_{date}_latest.csv"

            if latest_file.exists():
                # Get file metadata
                file_size = latest_file.stat().st_size
                mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)

                # Try to read row count
                try:
                    df = pd.read_csv(latest_file)
                    row_count = len(df)
                    result_text += f"- {date}: {row_count} records, "
                except:
                    result_text += f"- {date}: "

                result_text += f"{file_size/1024:.1f}KB, last modified {mod_time.strftime('%Y-%m-%d %H:%M:%S')}\n"

        return {
            "content": [{"type": "text", "text": result_text}]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error listing calculations: {str(e)}"}],
            "is_error": True
        }
