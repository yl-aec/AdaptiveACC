"""
Tool: find_elements_by_property_value
Category: step2_data_collection
Description: Finds elements of a specific IFC type with a specific property value in a given property set.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any

def find_elements_by_property_value(
    ifc_file_path: str,
    element_type: str,
    pset_name: str,
    property_name: str,
    property_value: Any
) -> List[Dict[str, Any]]:
    """Find elements of a specific type that have a specific property value within a specific property set.

    Args:
        ifc_file_path: Path to the IFC file.
        element_type: The IFC entity type (e.g., 'IfcWall').
        pset_name: The name of the property set (e.g., 'Pset_WallCommon').
        property_name: The name of the property (e.g., 'IsExternal').
        property_value: The value to match (e.g., True, 'External').

    Returns:
        A list of dictionaries containing 'GlobalId' and 'Name' of matching elements.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Get all elements of the specified type
    elements = ifc_file.by_type(element_type)
    results = []

    for element in elements:
        # Use ifcopenshell.util.element.get_psets to retrieve all property sets
        psets = ifcopenshell.util.element.get_psets(element)
        
        # Check if the specified property set exists
        if pset_name in psets:
            properties = psets[pset_name]
            
            # Check if the property exists and matches the value
            if property_name in properties and properties[property_name] == property_value:
                results.append({
                    "GlobalId": element.GlobalId,
                    "Name": element.Name if element.Name else None
                })

    return results