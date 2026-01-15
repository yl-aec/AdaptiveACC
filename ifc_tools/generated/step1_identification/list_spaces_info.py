"""
Tool: list_spaces_info
Category: step1_identification
Description: Extracts GlobalId and Name for all IfcSpace elements in the model.
"""

import ifcopenshell
from typing import List, Dict
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type

def list_spaces_info(ifc_file_path: str) -> List[Dict[str, str]]:
    """Get all IfcSpace elements from the model returning GlobalId and Name.

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        List of dictionaries containing 'GlobalId' and 'Name' for each space.
        Returns an empty list if no spaces are found.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    except OSError:
        raise ValueError(f"Unable to parse IFC file: {ifc_file_path}")

    spaces = get_elements_by_type(ifc_file, "IfcSpace")

    results = []
    for space in spaces:
        # Name is optional in IFC schema, provide safe default if None
        space_name = space.Name if space.Name else ""
        results.append({
            "GlobalId": space.GlobalId,
            "Name": space_name
        })

    return results