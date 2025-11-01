"""
Custom tools for the Vanguard AI Agent

These tools provide Claude with the ability to interact with the fund calculation system.
"""

from .calculator_tools import run_calculator
from .query_tools import query_weights, list_calculations
from .validation_tools import validate_weights
from .analysis_tools import analyze_weight_trends

__all__ = [
    'run_calculator',
    'query_weights',
    'list_calculations',
    'validate_weights',
    'analyze_weight_trends'
]
