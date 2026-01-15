"""
Tool: Numerical Comparison Operations
Category: quantification
Description: Pure comparison helper focused on evaluating values against thresholds
"""

from typing import Dict, Any


def compare_to_threshold(value: float, threshold: float, operator: str) -> Dict[str, Any]:
    """Compare a numeric value to a threshold using specified operator.

    Args:
        value: Numeric value to compare
        threshold: Threshold value
        operator: Comparison operator as string: '>', '<', '>=', '<=', '==', '!='

    Returns:
        Dict with comparison string and boolean result

    Example:
        result = compare_to_threshold(1000, 914.4, '>=')
        # Returns: {"comparison": "1000 >= 914.4", "meets_threshold": True}

        result = compare_to_threshold(800, 914.4, '>=')
        # Returns: {"comparison": "800 >= 914.4", "meets_threshold": False}
    """
    operators = {
        '>': lambda v, t: v > t,
        '<': lambda v, t: v < t,
        '>=': lambda v, t: v >= t,
        '<=': lambda v, t: v <= t,
        '==': lambda v, t: v == t,
        '!=': lambda v, t: v != t
    }

    meets_threshold = operators.get(operator, lambda v, t: False)(value, threshold)
    comparison = f"{value} {operator} {threshold}"

    return {
        "comparison": comparison,
        "meets_threshold": meets_threshold
    }
