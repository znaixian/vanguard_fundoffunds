"""
Analysis Tools

Tools for analyzing trends and performing statistical analysis on fund data.
"""

import os
from typing import Any, Dict
from pathlib import Path
import pandas as pd
import numpy as np

# Project paths
PROJECT_ROOT = Path(os.getenv('PROJECT_ROOT', os.getcwd()))
OUTPUT_DIR = PROJECT_ROOT / os.getenv('OUTPUT_DIR', 'output')


def analyze_weight_trends(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how a component's weight has changed over time.

    Args:
        args: Dictionary containing:
            - fund: Fund name
            - component: Component/benchmark ID
            - start_date: Start date (YYYYMMDD)
            - end_date: End date (YYYYMMDD)

    Returns:
        Trend analysis with statistics
    """
    try:
        fund = args["fund"]
        component = args["component"]
        start_date = args["start_date"]
        end_date = args["end_date"]

        # Collect data across date range
        fund_dir = OUTPUT_DIR / fund
        all_data = []

        for date_dir in sorted(fund_dir.glob("*")):
            if date_dir.is_dir():
                date_str = date_dir.name
                if start_date <= date_str <= end_date:
                    latest_file = date_dir / f"{fund}_{date_str}_latest.csv"
                    if latest_file.exists():
                        df = pd.read_csv(latest_file)
                        component_data = df[df['Benchmark ID'] == component]
                        if not component_data.empty:
                            all_data.append({
                                'Date': date_str,
                                'Weight': component_data['Weight'].iloc[0]
                            })

        if not all_data:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No data found for {component} in {fund} between {start_date} and {end_date}"
                }],
                "is_error": True
            }

        # Create DataFrame
        trend_df = pd.DataFrame(all_data)
        trend_df['Date'] = pd.to_datetime(trend_df['Date'])
        trend_df = trend_df.sort_values('Date')

        # Calculate statistics
        mean_weight = trend_df['Weight'].mean()
        std_weight = trend_df['Weight'].std()
        min_weight = trend_df['Weight'].min()
        max_weight = trend_df['Weight'].max()
        current_weight = trend_df['Weight'].iloc[-1]
        change = trend_df['Weight'].iloc[-1] - trend_df['Weight'].iloc[0]
        change_pct = (change / trend_df['Weight'].iloc[0]) * 100 if trend_df['Weight'].iloc[0] != 0 else 0

        # Check trend direction
        if len(trend_df) > 1:
            correlation = trend_df.index.to_series().corr(trend_df['Weight'])
            if correlation > 0.5:
                trend_direction = "INCREASING"
            elif correlation < -0.5:
                trend_direction = "DECREASING"
            else:
                trend_direction = "STABLE"
        else:
            trend_direction = "INSUFFICIENT DATA"

        # Format output
        result_text = f"Weight Trend Analysis\n\n"
        result_text += f"Fund: {fund}\n"
        result_text += f"Component: {component}\n"
        result_text += f"Period: {start_date} to {end_date}\n"
        result_text += f"Data Points: {len(trend_df)}\n\n"

        result_text += f"Statistics:\n"
        result_text += f"  Current Weight: {current_weight:.4f}%\n"
        result_text += f"  Mean Weight: {mean_weight:.4f}%\n"
        result_text += f"  Std Deviation: {std_weight:.4f}%\n"
        result_text += f"  Min Weight: {min_weight:.4f}% on {trend_df[trend_df['Weight'] == min_weight]['Date'].iloc[0].strftime('%Y-%m-%d')}\n"
        result_text += f"  Max Weight: {max_weight:.4f}% on {trend_df[trend_df['Weight'] == max_weight]['Date'].iloc[0].strftime('%Y-%m-%d')}\n"
        result_text += f"  Total Change: {change:+.4f}% ({change_pct:+.2f}%)\n"
        result_text += f"  Trend Direction: {trend_direction}\n\n"

        # UCITS cap check
        ucits_cap = 19.25
        distance_to_cap = ucits_cap - current_weight
        result_text += f"UCITS Compliance:\n"
        result_text += f"  Distance to Cap (19.25%): {distance_to_cap:.4f}%\n"
        if current_weight > ucits_cap:
            result_text += f"  WARNING: EXCEEDS UCITS CAP\n"
        elif distance_to_cap < 0.5:
            result_text += f"  CAUTION: Within 0.5% of cap\n"
        else:
            result_text += f"  Status: OK\n"

        return {
            "content": [{"type": "text", "text": result_text}]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error analyzing trends: {str(e)}"}],
            "is_error": True
        }
