"""
Tool: convert_height_mm_to_inches
Category: others
Description: Convert height values from millimeters to inches using the conversion factor 1 inch = 25.4 mm. This tool performs a single unit conversion operation on provided height values.
"""

def convert_height_mm_to_inches(height_mm: float) -> float:
    '''Convert height values from millimeters to inches.
    
    Uses the conversion factor 1 inch = 25.4 mm to perform unit conversion.
    This is a pure mathematical conversion without IFC file dependencies.
    
    Args:
        height_mm: Height value in millimeters to be converted to inches.
        
    Returns:
        Height value converted to inches as a float.
        
    Example:
        >>> convert_height_mm_to_inches(254.0)
        10.0
        >>> convert_height_mm_to_inches(127.0)
        5.0
    '''
    # Conversion factor: 1 inch = 25.4 mm
    INCHES_PER_MM = 1 / 25.4
    
    # Perform the conversion
    height_inches = height_mm * INCHES_PER_MM
    
    return height_inches