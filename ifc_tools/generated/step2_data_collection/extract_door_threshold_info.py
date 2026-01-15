"""
Tool: extract_door_threshold_info
Category: step2_data_collection
Description: Extracts threshold properties, sill height, and vertical geometry coordinates (insertion point and bounding box min Z) for a list of doors.
"""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def extract_door_threshold_info(ifc_file_path: str, door_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts threshold, sill, and vertical positioning information for specific doors.

    Retrieves:
    1. Property values for 'Threshold Thickness'/'ThresholdHeight' and 'Sill Height'/'Sill Elevation'.
    2. Absolute Z-coordinate of the insertion point.

    Args:
        ifc_file_path: Path to the IFC file.
        door_ids: List of GlobalIds for IfcDoor elements.

    Returns:
        List of dictionaries containing:
        - global_id: The door's GlobalId.
        - threshold_value: Value of found threshold property (or None).
        - sill_height_value: Value of found sill height/elevation property (or None).
        - insertion_z: Absolute Z coordinate of object placement (or None).
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Fetch requested doors
    doors = get_elements_by_ids(ifc_file, door_ids)
    
    results = []

    for door in doors:
        if not door.is_a("IfcDoor"):
            continue

        # 1. Extract Properties
        psets = ifcopenshell.util.element.get_psets(door)
        threshold_val = None
        sill_val = None

        for pset_name, props in psets.items():
            for key, value in props.items():
                key_lower = key.lower()
                # Check for Threshold
                if "threshold thickness" in key_lower or "thresholdheight" in key_lower:
                    if threshold_val is None: # Take first match
                        threshold_val = value
                
                # Check for Sill Height or Sill Elevation
                if "sill height" in key_lower or "sill elevation" in key_lower:
                    if sill_val is None: # Take first match
                        sill_val = value

        # 2. Extract Insertion Point Z
        insertion_z = None
        if door.ObjectPlacement:
            # get_local_placement returns a 4x4 matrix relative to world. Z is at [2][3]
            matrix = ifcopenshell.util.placement.get_local_placement(door.ObjectPlacement)
            insertion_z = float(matrix[2][3])

        results.append({
            "global_id": door.GlobalId,
            "threshold_value": threshold_val,
            "sill_height_value": sill_val,
            "insertion_z": insertion_z
        })

    return results