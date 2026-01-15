"""
Tool: extract_space_attributes_and_properties
Category: step2_data_collection
Description: Extracts standard attributes (Name, LongName, ObjectType) and common properties (Reference, IsExternal) for all IfcSpace elements.
"""

import ifcopenshell
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property

def extract_space_attributes_and_properties(ifc_file_path: str) -> List[Dict[str, Any]]:
    """Extracts Name, LongName, ObjectType, and specific Pset_SpaceCommon properties for all spaces.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        List of dictionaries containing space details. Each dictionary includes:
        - GlobalId
        - Name
        - LongName
        - ObjectType
        - Reference (from Pset_SpaceCommon)
        - IsExternal (from Pset_SpaceCommon)
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")

    spaces = get_elements_by_type(ifc_file, "IfcSpace")
    results = []

    for space in spaces:
        # Extract direct attributes safely
        name = getattr(space, "Name", None)
        long_name = getattr(space, "LongName", None)
        object_type = getattr(space, "ObjectType", None)

        # Extract properties from Pset_SpaceCommon
        # get_pset_property returns a dict {'value': ..., 'unit': ...} or None
        ref_data = get_pset_property(space, "Pset_SpaceCommon", "Reference")
        reference = ref_data["value"] if ref_data else None

        ext_data = get_pset_property(space, "Pset_SpaceCommon", "IsExternal")
        is_external = ext_data["value"] if ext_data else None

        results.append({
            "GlobalId": space.GlobalId,
            "Name": name,
            "LongName": long_name,
            "ObjectType": object_type,
            "Reference": reference,
            "IsExternal": is_external
        })

    return results