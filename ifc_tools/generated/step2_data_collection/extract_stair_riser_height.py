"""
Tool: extract_stair_riser_height
Category: step2_data_collection
Description: Extract RiserHeight property value from Pset_StairCommon property set for specified IfcStair elements. Returns a dictionary mapping each stair GlobalId to its riser height in millimeters (or None if not found).
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import Dict, List, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids


def extract_stair_riser_height(ifc_file_path: str, stair_ids: List[str]) -> Dict[str, Optional[float]]:
    '''Extract RiserHeight property value from Pset_StairCommon for IfcStair elements.

    Args:
        ifc_file_path: Path to the IFC file.
        stair_ids: List of GlobalIds for IfcStair elements to analyze.

    Returns:
        Dictionary mapping each stair GlobalId to its riser height value in millimeters.
        Returns None for stairs where the property is not found.

    Example:
        >>> result = extract_stair_riser_height('model.ifc', ['2XQ$n$0qH0hu1yqA2xzv7w', '3YQ$m$1pH1iv2zrB3yaw8x'])
        >>> print(result)
        {'2XQ$n$0qH0hu1yqA2xzv7w': 175.0, '3YQ$m$1pH1iv2zrB3yaw8x': None}
    '''
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    except Exception as e:
        raise ValueError(f"Error opening IFC file: {str(e)}")
    
    # Get stair elements by their GlobalIds
    stairs = get_elements_by_ids(ifc_file, stair_ids)
    
    # Create result dictionary
    results = {}
    
    for stair in stairs:
        stair_id = stair.GlobalId
        
        # Get all property sets for the stair element
        psets = ifcopenshell.util.element.get_psets(stair)
        
        # Look for Pset_StairCommon and extract RiserHeight
        riser_height = None
        if "Pset_StairCommon" in psets:
            stair_common_pset = psets["Pset_StairCommon"]
            if "RiserHeight" in stair_common_pset:
                riser_height = stair_common_pset["RiserHeight"]
                
                # Ensure the value is a float (handle potential string values)
                if isinstance(riser_height, str):
                    try:
                        riser_height = float(riser_height)
                    except (ValueError, TypeError):
                        riser_height = None
                elif not isinstance(riser_height, (int, float)):
                    riser_height = None
        
        results[stair_id] = riser_height
    
    # Handle any requested stairs that weren't found in the file
    for stair_id in stair_ids:
        if stair_id not in results:
            results[stair_id] = None
    
    return results