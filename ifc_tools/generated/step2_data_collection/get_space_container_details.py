"""
Tool: get_space_container_details
Category: step2_data_collection
Description: Counts all IfcSpace elements and retrieves identification and spatial container details (via IfcRelContainedInSpatialStructure) for the first 5 spaces.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import Dict, Any, List, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type

def get_space_container_details(ifc_file_path: str) -> Dict[str, Any]:
    """Counts IfcSpace elements and retrieves container details for the first 5.

    Retrieves the GlobalId, Name, and the spatial container (via 
    IfcRelContainedInSpatialStructure) for the first 5 spaces found.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        A dictionary with:
        - 'total_count': Total number of IfcSpace elements.
        - 'sampled_spaces': List of dicts for the first 5 spaces, each containing:
            - 'GlobalId': The space's GlobalId.
            - 'Name': The space's Name.
            - 'Container': Dict with 'GlobalId' and 'Type' of the container, or None.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")

    # Get all spaces
    spaces = get_elements_by_type(ifc_file, "IfcSpace")
    total_count = len(spaces)
    
    sampled_spaces = []
    # Process first 5 spaces (or fewer if less than 5 exist)
    for space in spaces[:5]:
        # Retrieve container via IfcRelContainedInSpatialStructure
        # Note: This returns None if the space is only linked via IfcRelAggregates
        container = ifcopenshell.util.element.get_container(space)
        
        container_info = None
        if container:
            container_info = {
                "GlobalId": container.GlobalId,
                "Type": container.is_a()
            }
            
        sampled_spaces.append({
            "GlobalId": space.GlobalId,
            "Name": space.Name,
            "Container": container_info
        })

    return {
        "total_count": total_count,
        "sampled_spaces": sampled_spaces
    }