"""
Tool: get_space_elevation
Category: step2_data_collection
Description: Retrieves elevation for IfcSpace elements by checking 'ElevationWithFlooring' property or calculating global Z coordinate.
"""

import ifcopenshell
import ifcopenshell.util.placement
from typing import List, Dict, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property

def get_space_elevation(ifc_file_path: str, space_ids: List[str]) -> Dict[str, Optional[float]]:
    """Retrieve elevation for a list of IfcSpace elements.

    Checks 'ElevationWithFlooring' property in 'Pset_SpaceCommon' first.
    If missing, calculates global Z coordinate from IfcLocalPlacement.

    Args:
        ifc_file_path: Path to the IFC file.
        space_ids: List of GlobalIds of IfcSpace elements.

    Returns:
        Dictionary mapping space GlobalId to elevation (float) or None if undetermined.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    results = {}

    for space_id in space_ids:
        space = get_element_by_id(ifc_file, space_id)
        
        if not space or not space.is_a("IfcSpace"):
            results[space_id] = None
            continue

        elevation = None

        # 1. Try Property: ElevationWithFlooring (Pset_SpaceCommon)
        prop_data = get_pset_property(space, "Pset_SpaceCommon", "ElevationWithFlooring")
        if prop_data and "value" in prop_data and prop_data["value"] is not None:
            try:
                elevation = float(prop_data["value"])
            except (ValueError, TypeError):
                pass # Fallback to geometry if value is non-numeric
        
        # 2. Try Geometric Placement if property failed or missing
        if elevation is None:
            if space.ObjectPlacement:
                try:
                    # get_local_placement returns a 4x4 matrix representing global transformation
                    # The Z coordinate is located at row 2, column 3 (0-indexed)
                    matrix = ifcopenshell.util.placement.get_local_placement(space.ObjectPlacement)
                    elevation = float(matrix[2][3])
                except Exception:
                    # If placement calculation fails (e.g. invalid placement), leave as None
                    pass

        results[space_id] = elevation

    return results