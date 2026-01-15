"""
Tool: analyze_riser_height_completeness
Category: step3_analysis
Description: Analyze riser height values for completeness and validity, checking for missing values, non-numeric values, and optionally values outside a specified range.
"""

import ifcopenshell
from typing import Dict, List, Any, Optional

def analyze_riser_height_completeness(
    ifc_file_path: str,
    riser_height_data: Dict[str, Optional[float]],
    min_valid_height: Optional[float] = None,
    max_valid_height: Optional[float] = None
) -> Dict[str, Any]:
    '''Analyze riser height values for completeness and validity.

    This tool checks a dataset of riser height values for:
    1. Missing values (null/None)
    2. Invalid values (non-numeric)
    3. Optionally, values outside a specified range

    Args:
        ifc_file_path: Path to the IFC file (kept for interface consistency, not used).
        riser_height_data: Dictionary with element GlobalIds as keys and riser height
            values in millimeters as values. Values can be float, int, or None.
        min_valid_height: Minimum valid riser height in millimeters (optional).
            If provided, values below this will be flagged as out-of-range.
        max_valid_height: Maximum valid riser height in millimeters (optional).
            If provided, values above this will be flagged as out-of-range.

    Returns:
        Dictionary containing:
        - total_count: Total number of elements in the dataset
        - missing_count: Number of elements with missing (None) values
        - invalid_count: Number of elements with non-numeric values
        - out_of_range_count: Number of elements with values outside specified range
        - missing_ids: List of element IDs with missing values
        - invalid_ids: List of element IDs with non-numeric values
        - out_of_range_ids: List of element IDs with values outside specified range
        - completeness_status: 'complete' if no missing/invalid values, 'incomplete' otherwise
        - validity_status: 'valid' if no invalid/out-of-range values, 'invalid' otherwise

    Example:
        >>> data = {
        ...     '2a3b4c5d': 150.0,
        ...     '3b4c5d6e': None,
        ...     '4c5d6e7f': 'invalid',
        ...     '5d6e7f8g': 600.0
        ... }
        >>> result = analyze_riser_height_completeness(
        ...     'model.ifc',
        ...     data,
        ...     min_valid_height=0,
        ...     max_valid_height=500
        ... )
        >>> print(result['completeness_status'])
        'incomplete'
        >>> print(result['invalid_ids'])
        ['4c5d6e7f']
        >>> print(result['out_of_range_ids'])
        ['5d6e7f8g']
    '''
    # Validate input data
    if not isinstance(riser_height_data, dict):
        raise TypeError("riser_height_data must be a dictionary")
    
    # Initialize counters and lists
    total_count = len(riser_height_data)
    missing_ids = []
    invalid_ids = []
    out_of_range_ids = []
    
    # Validate each entry
    for element_id, height_value in riser_height_data.items():
        # Check for missing values
        if height_value is None:
            missing_ids.append(element_id)
            continue
        
        # Check for non-numeric values
        if not isinstance(height_value, (int, float)):
            invalid_ids.append(element_id)
            continue
        
        # Check for out-of-range values if range is specified
        if min_valid_height is not None or max_valid_height is not None:
            is_out_of_range = False
            
            if min_valid_height is not None and height_value < min_valid_height:
                is_out_of_range = True
            
            if max_valid_height is not None and height_value > max_valid_height:
                is_out_of_range = True
            
            if is_out_of_range:
                out_of_range_ids.append(element_id)
    
    # Calculate counts
    missing_count = len(missing_ids)
    invalid_count = len(invalid_ids)
    out_of_range_count = len(out_of_range_ids)
    
    # Determine overall statuses
    completeness_status = 'complete' if missing_count == 0 else 'incomplete'
    validity_status = 'valid' if (invalid_count == 0 and out_of_range_count == 0) else 'invalid'
    
    # Compile results
    results = {
        'total_count': total_count,
        'missing_count': missing_count,
        'invalid_count': invalid_count,
        'out_of_range_count': out_of_range_count,
        'missing_ids': missing_ids,
        'invalid_ids': invalid_ids,
        'out_of_range_ids': out_of_range_ids,
        'completeness_status': completeness_status,
        'validity_status': validity_status
    }
    
    return results