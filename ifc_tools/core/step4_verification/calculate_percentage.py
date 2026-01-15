"""
Tool: Ratio and Percentage Calculations
Category: quantification
Description: Pure mathematical functions for ratio and percentage calculations
"""



def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage of part relative to total.

    Args:
        part: Part value (numerator)
        total: Total value (denominator)

    Returns:
        Percentage as float (0-100 range). Returns 0.0 if total is 0.

    Example:
        percentage = calculate_percentage(5, 20)  # Returns: 25.0 (means 25%)
        percentage = calculate_percentage(3, 10)  # Returns: 30.0 (means 30%)
    """
    return (part / total * 100) if total > 0 else 0.0

