"""
Tool: get_element_storey_info
Category: step2_data_collection
Description: Identifies the spatial container (e.g., IfcBuildingStorey) for a list of elements and extracts its Name, GlobalId, and Elevation.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id

def get_element_storey_info(ifc_file_path: str, element_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Finds the containing spatial structure (typically IfcBuildingStorey) for a list of elements.

    Uses IfcRelContainedInSpatialStructure relationships to identify where elements are located
    within the spatial hierarchy. Retrieves Name, GlobalId, and Elevation of the container.

    Args:
        ifc_file_path: Path to the IFC file.
        element_ids: List of GlobalIds of the elements to query.

    Returns:
        A dictionary mapping element GlobalIds to a dictionary containing:
        - 'Name': Name of the storey/container
        - 'GlobalId': GlobalId of the storey/container
        - 'Elevation': Elevation of the storey (if available)
        Returns None for a specific ID if the element is not found or has no container.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    results = {}

    for eid in element_ids:
        element = get_element_by_id(ifc_file, eid)
        if not element:
            results[eid] = None
            continue

        # Use ifcopenshell utility to resolve the spatial container
        container = ifcopenshell.util.element.get_container(element)

        if not container:
            results[eid] = None
            continue

        # Extract relevant attributes. Elevation is specific to IfcBuildingStorey.
        # getattr is used safely in case the container is not a storey (e.g., IfcSpace or IfcBuilding).
        elevation = getattr(container, "Elevation", None)

        results[eid] = {
            "Name": container.Name,
            "GlobalId": container.GlobalId,
            "Elevation": elevation
        }

    return results