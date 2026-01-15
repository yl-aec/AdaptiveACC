"""
Tool: extract_storeys_info
Category: step2_data_collection
Description: Finds all IfcBuildingStorey elements and extracts their identification, elevation, and common properties.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any

def extract_storeys_info(ifc_file_path: str) -> List[Dict[str, Any]]:
    """Extracts GlobalId, Name, Elevation, and Pset_BuildingStoreyCommon properties for all storeys.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        List of dictionaries, where each dictionary represents a storey and contains:
        - GlobalId (str)
        - Name (str)
        - Elevation (float or None)
        - Pset_BuildingStoreyCommon (Dict): Key-value pairs of properties in this property set.
    """
    # Open the IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)

    # Get all IfcBuildingStorey elements
    storeys = ifc_file.by_type("IfcBuildingStorey")

    results = []
    for storey in storeys:
        # Extract basic attributes
        # Elevation is a direct attribute of IfcBuildingStorey
        elevation = storey.Elevation if hasattr(storey, "Elevation") else None

        # Extract property sets using utility
        # get_psets returns a dict of dicts: {"Pset_Name": {"PropName": Value, ...}}
        all_psets = ifcopenshell.util.element.get_psets(storey)
        
        # Extract specifically Pset_BuildingStoreyCommon, default to empty dict if missing
        pset_common = all_psets.get("Pset_BuildingStoreyCommon", {})

        storey_info = {
            "GlobalId": storey.GlobalId,
            "Name": storey.Name,
            "Elevation": elevation,
            "Pset_BuildingStoreyCommon": pset_common
        }
        results.append(storey_info)

    return results