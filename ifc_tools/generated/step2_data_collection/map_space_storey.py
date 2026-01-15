"""
Tool: map_space_storey
Category: step2_data_collection
Description: Maps IfcSpace elements to their parent IfcBuildingStorey via containment relationships.
"""

import ifcopenshell
from typing import Dict

def map_space_storey(ifc_file_path: str) -> Dict[str, str]:
    """Maps every IfcSpace to its parent IfcBuildingStorey.

    Iterates through IfcRelContainedInSpatialStructure relationships. If the 
    RelatingStructure is an IfcBuildingStorey, maps the GlobalId of each 
    IfcSpace in RelatedElements to the GlobalId of that storey.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        Dictionary mapping IfcSpace GlobalId to IfcBuildingStorey GlobalId.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")

    space_storey_map = {}
    
    # Iterate through all containment relationships
    containment_rels = ifc_file.by_type("IfcRelContainedInSpatialStructure")
    
    for rel in containment_rels:
        relating_structure = rel.RelatingStructure
        
        # Ensure structure exists and is a BuildingStorey
        if relating_structure and relating_structure.is_a("IfcBuildingStorey"):
            storey_id = relating_structure.GlobalId
            
            # Check related elements
            if rel.RelatedElements:
                for element in rel.RelatedElements:
                    if element.is_a("IfcSpace"):
                        space_storey_map[element.GlobalId] = storey_id
                        
    return space_storey_map