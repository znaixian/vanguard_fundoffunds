"""
Calculator Tools

Tools for running the fund calculation pipeline.
"""

from typing import Any, Dict
from datetime import datetime


def run_calculator(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the fund calculation pipeline.

    Args:
        args: Dictionary containing:
            - date: Date in YYYYMMDD format or 'today'
            - fund: Fund name (e.g., 'vanguard_lifestrat') or None for all funds

    Returns:
        Calculation results including status, output file path, and any warnings
    """
    try:
        from orchestration.main_pipeline import DailyPipeline

        date = args.get("date", "today")
        fund = args.get("fund")

        # Convert date if needed
        if date == "today":
            date = datetime.now().strftime('%Y%m%d')

        # Run pipeline
        pipeline = DailyPipeline(date)
        exit_code = pipeline.run(fund_filter=fund)

        # Format results
        status_map = {0: "SUCCESS", 1: "PARTIAL SUCCESS", 2: "FAILURE"}
        status = status_map.get(exit_code, f"UNKNOWN (code {exit_code})")

        result_text = f"Calculation Status: {status}\n\n"
        result_text += f"Date: {date}\n"
        result_text += f"Fund Filter: {fund or 'All funds'}\n\n"
        result_text += "Results:\n"

        for result in pipeline.results:
            result_text += f"\n- Fund: {result['fund']}\n"
            result_text += f"  Status: {result['status']}\n"
            if 'runtime' in result:
                result_text += f"  Runtime: {result['runtime']:.2f}s\n"
            if 'output_path' in result:
                result_text += f"  Output: {result['output_path']}\n"
            if 'warnings' in result and result['warnings']:
                result_text += f"  Warnings: {', '.join(result['warnings'])}\n"
            if 'error' in result:
                result_text += f"  Error: {result['error']}\n"

        return {
            "content": [{"type": "text", "text": result_text}]
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error running calculator: {str(e)}"}],
            "is_error": True
        }
