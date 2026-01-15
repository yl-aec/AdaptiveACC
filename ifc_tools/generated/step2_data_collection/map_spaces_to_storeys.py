"""
Tool: map_spaces_to_storeys
Category: step2_data_collection
Description: Maps IfcSpace elements to their parent IfcBuildingStorey by checking containment and aggregation relationships.
"""

import ifcopenshell
from typing import Dict, Any, Optional

def map_spaces_to_storeys(ifc_file_path: str) -> Dict[str, Dict[str, Any]]:
    """Map every IfcSpace to its parent IfcBuildingStorey.

    Checks both IfcRelContainedInSpatialStructure (standard containment) and 
    IfcRelAggregates (aggregation/decomposition) to find the relating storey.
    Traverses up the spatial hierarchy if a space is nested within another space.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        A dictionary where keys are Space GlobalIds and values are dictionaries
        containing space and storey details.
        Example:
        {
            "2O2Fr$t4X7Zf8NOew3FLOH": {
                "space_name": "Living Room",
                "storey_name": "Level 1",
                "storey_id": "1xS3BCk291Mw89nGdLpQ5K"
            }
        }
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    spaces = ifc_file.by_type("IfcSpace")
    
    results = {}

    for space in spaces:
        storey = None
        current_element = space
        steps = 0
        max_steps = 10  # Prevent infinite loops in circular references

        # Traverse up the hierarchy to find a Storey
        while steps < max_steps:
            parent = None

            # 1. Check Aggregation (Decomposes) - e.g., Space inside Space
            # Inverse attribute: Decomposes -> IfcRelAggregates
            if hasattr(current_element, "Decomposes") and current_element.Decomposes:
                for rel in current_element.Decomposes:
                    if rel.is_a("IfcRelAggregates"):
                        parent = rel.RelatingObject
                        break
            
            # 2. Check Containment - e.g., Space inside Storey
            # Inverse attribute: ContainedInStructure -> IfcRelContainedInSpatialStructure
            if not parent and hasattr(current_element, "ContainedInStructure") and current_element.ContainedInStructure:
                for rel in current_element.ContainedInStructure:
                    if rel.is_a("IfcRelContainedInSpatialStructure"):
                        parent = rel.RelatingStructure
                        break
            
            if not parent:
                break  # Orphan element

            if parent.is_a("IfcBuildingStorey"):
                storey = parent
                break
            
            # If we hit a Building, Site, or Project, we stop (no Storey found)
            if parent.is_a("IfcBuilding") or parent.is_a("IfcSite") or parent.is_a("IfcProject"):
                break

            # If parent is another Space, continue traversing up
            current_element = parent
            steps += 1

        if storey:
            results[space.GlobalId] = {
                "space_name": space.Name,
                "storey_name": storey.Name,
                "storey_id": storey.GlobalId
            }
        else:
            # Include space even if no storey found, with None values
            results[space.GlobalId] = {
                "space_name": space.Name,
                "storey_name": None,
                "storey_id": None
            }

    return results
