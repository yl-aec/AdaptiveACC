"""
Tool: analyze_space_elevations_by_storey
Category: step3_analysis
Description: Groups spaces by their building storey and calculates elevation statistics (min, max, range) for each storey.
"""

import ifcopenshell
import ifcopenshell.util.placement
from typing import Dict, Any, List, Optional

def analyze_space_elevations_by_storey(ifc_file_path: str) -> Dict[str, Any]:
    """Groups spaces by their building storey and calculates elevation statistics.

    For each building storey containing spaces, this function identifies the spaces,
    extracts their absolute bottom elevation (Z-coordinate), and calculates the
    minimum, maximum, and range of elevations for that storey.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        A dictionary keyed by the Storey GlobalId. Each value is a dictionary containing:
        - storey_name: Name of the storey
        - spaces: List of dicts with space 'id', 'name', and 'elevation'
        - stats: Dict with 'min_elevation', 'max_elevation', and 'range'
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    spaces = ifc_file.by_type("IfcSpace")
    
    grouped_data = {}

    def get_spatial_container(element):
        """Traverses up the hierarchy to find the IfcBuildingStorey."""
        current = element
        # Limit traversal to prevent infinite loops
        for _ in range(20):
            # Check if the current element is already a Storey
            if current.is_a("IfcBuildingStorey"):
                return current

            # 1. Check ContainedInStructure (Spatial Containment)
            if hasattr(current, "ContainedInStructure") and current.ContainedInStructure:
                rel = current.ContainedInStructure[0]
                container = rel.RelatingStructure
                if container.is_a("IfcBuildingStorey"):
                    return container
                # If contained in Building or Site, stop traversal as it's not in a Storey
                return None
            
            # 2. Check Decomposes (Aggregation/Nesting)
            if hasattr(current, "Decomposes") and current.Decomposes:
                rel = current.Decomposes[0]
                current = rel.RelatingObject
                continue
            
            # No parent found
            break
        return None

    for space in spaces:
        # Find the spatial container (Storey) using custom traversal
        container = get_spatial_container(space)
        
        if not container:
            continue
            
        storey_id = container.GlobalId
        storey_name = container.Name if container.Name else "Unnamed Storey"
        
        if storey_id not in grouped_data:
            grouped_data[storey_id] = {
                "storey_name": storey_name,
                "spaces": []
            }
            
        elevation = 0.0
        if space.ObjectPlacement:
            matrix = ifcopenshell.util.placement.get_local_placement(space.ObjectPlacement)
            elevation = float(matrix[2][3])
            
        grouped_data[storey_id]["spaces"].append({
            "id": space.GlobalId,
            "name": space.Name if space.Name else "Unnamed Space",
            "elevation": elevation
        })

    results = {}
    for s_id, data in grouped_data.items():
        space_list = data["spaces"]
        if not space_list:
            continue
            
        elevations = [s["elevation"] for s in space_list]
        min_el = min(elevations)
        max_el = max(elevations)
        range_el = max_el - min_el
        
        results[s_id] = {
            "storey_name": data["storey_name"],
            "spaces": space_list,
            "stats": {
                "min_elevation": min_el,
                "max_elevation": max_el,
                "range": range_el
            }
        }
        
    return results