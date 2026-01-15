"""
Tool: calculate_stair_riser_heights
Category: step3_analysis
Description: Calculate individual riser heights for IfcStair elements based on RiserHeight and NumberOfRiser property values. Determines if RiserHeight is individual or total height and calculates accordingly.
"""

import ifcopenshell
from typing import Dict, Any, List
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property

def calculate_stair_riser_heights(ifc_file_path: str, stair_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    '''Calculate individual riser heights for IfcStair elements.
    
    This tool calculates the individual riser height for each stair based on
    collected RiserHeight and NumberOfRiser values from property sets.
    If RiserHeight appears to be an individual riser height (102-178 mm regulatory range),
    it is used directly; otherwise, it is divided by NumberOfRiser.
    
    Args:
        ifc_file_path: Path to the IFC file.
        stair_data: Dictionary mapping stair GlobalIds to their property data.
                    Expected format: {
                        "stair_id_1": {
                            "RiserHeight": float,  # in mm
                            "NumberOfRiser": int
                        },
                        ...
                    }
    
    Returns:
        Dictionary mapping each stair ID to a dict containing:
            - "individual_riser_height_mm": float (calculated individual riser height in mm)
            - "calculation_method": str ("direct" or "divided" or "missing_data" or "invalid_number_of_risers")
            - "original_riser_height_mm": float (original RiserHeight value)
            - "number_of_risers": int (NumberOfRiser value)
        
    Example:
        >>> stair_data = {
        ...     "2a3b4c5d": {"RiserHeight": 170.0, "NumberOfRiser": 10},
        ...     "3b4c5d6e": {"RiserHeight": 1500.0, "NumberOfRiser": 10},
        ...     "4e5f6g7h": {"RiserHeight": 171.428571428571, "NumberOfRiser": 7}
        ... }
        >>> result = calculate_stair_riser_heights("model.ifc", stair_data)
        >>> print(result["2a3b4c5d"]["individual_riser_height_mm"])
        170.0
        >>> print(result["2a3b4c5d"]["calculation_method"])
        "direct"
        >>> print(result["3b4c5d6e"]["individual_riser_height_mm"])
        150.0
        >>> print(result["3b4c5d6e"]["calculation_method"])
        "divided"
        >>> print(result["4e5f6g7h"]["individual_riser_height_mm"])
        171.428571428571
        >>> print(result["4e5f6g7h"]["calculation_method"])
        "direct"
    '''
    
    # Open IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Get stair elements by their GlobalIds
    stair_ids = list(stair_data.keys())
    stairs = get_elements_by_ids(ifc_file, stair_ids)
    
    results = {}
    
    for stair in stairs:
        stair_id = stair.GlobalId
        
        # Skip if stair_id not in provided data
        if stair_id not in stair_data:
            continue
            
        data = stair_data[stair_id]
        riser_height = data.get("RiserHeight")
        number_of_risers = data.get("NumberOfRiser")
        
        # Skip if required data is missing
        if riser_height is None or number_of_risers is None:
            results[stair_id] = {
                "individual_riser_height_mm": None,
                "calculation_method": "missing_data",
                "original_riser_height_mm": riser_height,
                "number_of_risers": number_of_risers
            }
            continue
        
        # Determine if riser_height is likely individual riser height (102-178 mm regulatory range)
        # or total stair height
        if 102.0 <= riser_height <= 178.0:
            individual_height = riser_height
            method = "direct"
        else:
            # Calculate individual riser height by dividing total by number of risers
            if number_of_risers > 0:
                individual_height = riser_height / number_of_risers
                method = "divided"
            else:
                individual_height = None
                method = "invalid_number_of_risers"
        
        results[stair_id] = {
            "individual_riser_height_mm": individual_height,
            "calculation_method": method,
            "original_riser_height_mm": riser_height,
            "number_of_risers": number_of_risers
        }
    
    return results