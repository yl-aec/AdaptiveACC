"""
Tool: extract_stair_number_of_risers
Category: step2_data_collection
Description: Extract NumberOfRiser property values from Pset_StairCommon property set for specified IfcStair elements
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import Dict, List, Optional, Union
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def extract_stair_number_of_risers(ifc_file_path: str, stair_ids: List[str]) -> Dict[str, Optional[Union[int, float]]]:
    '''Extract NumberOfRiser property values from Pset_StairCommon for specified IfcStair elements.

    Args:
        ifc_file_path: Path to the IFC file.
        stair_ids: List of GlobalIds for IfcStair elements to analyze.

    Returns:
        Dictionary mapping each stair GlobalId to its number of risers (int/float) or None if not found.
        Example: {"1a2b3c": 15, "4d5e6f": None}

    Example:
        >>> result = extract_stair_number_of_risers("model.ifc", ["1a2b3c", "4d5e6f"])
        >>> print(result)
        {"1a2b3c": 15, "4d5e6f": None}
    '''
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    except Exception as e:
        raise ValueError(f"Error opening IFC file: {e}")
    
    # Get stair elements by IDs
    stairs = get_elements_by_ids(ifc_file, stair_ids)
    
    # Initialize result dictionary
    results = {}
    
    # Process each stair
    for stair in stairs:
        stair_id = stair.GlobalId
        
        # Get all property sets for the stair (including inherited from type)
        psets = ifcopenshell.util.element.get_psets(stair)
        
        # Look for Pset_StairCommon and NumberOfRiser property
        number_of_risers = None
        if "Pset_StairCommon" in psets:
            pset_data = psets["Pset_StairCommon"]
            if "NumberOfRiser" in pset_data:
                number_of_risers = pset_data["NumberOfRiser"]
                # Convert to appropriate numeric type
                if isinstance(number_of_risers, (int, float)):
                    pass  # Keep as is
                elif isinstance(number_of_risers, str):
                    try:
                        # Try to convert string to float/int
                        if '.' in number_of_risers:
                            number_of_risers = float(number_of_risers)
                        else:
                            number_of_risers = int(number_of_risers)
                    except ValueError:
                        number_of_risers = None
                else:
                    number_of_risers = None
        
        results[stair_id] = number_of_risers
    
    # Ensure all requested IDs are in results (even if not found)
    for stair_id in stair_ids:
        if stair_id not in results:
            results[stair_id] = None
    
    return results