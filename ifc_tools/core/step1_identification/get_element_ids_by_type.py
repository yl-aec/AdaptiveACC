"""
Element Selection Tools
Category: identification (P1 - Identification & Scoping)
Description: Tools for selecting elements by type. This is typically the first step
             in compliance checking workflows to establish the scope of elements.
"""

from typing import Dict, Any
from ifc_tool_utils.ifcopenshell import get_elements_by_type as get_elems
from utils.ifc_file_manager import IFCFileManager


def get_element_ids_by_type(ifc_file_path: str, element_type: str) -> Dict[str, Any]:
    """Get element IDs of all elements of a specified IFC type.

    This function retrieves element IDs (GlobalIds) for all elements matching
    the specified IFC type. This is typically the first step in exploratory
    analysis: "get all door IDs", "get all wall IDs", etc. The returned element
    IDs can then be used with other tools to explore properties and relationships.

    Args:
        ifc_file_path: Path to the IFC file
        element_type: IFC type string (e.g., "IfcDoor", "IfcWall", "IfcSpace")

    Returns:
        Dictionary with:
        - element_type: The requested IFC type
        - element_ids: List of GlobalId strings for all matching elements
        - count: Total number of elements found

        Returns error dict if operation fails.

    Example:
        result = get_element_ids_by_type("model.ifc", "IfcDoor")
        # Returns: {"element_type": "IfcDoor",
        #           "element_ids": ["2O2Fr$t4X7Zf8NOew3FLOH", "3O2Fr$t4X7Zf8NOew3FLOI", ...],
        #           "count": 42}

    Note:
        Use this as the starting point for type-specific analysis. Once you have
        the element IDs, use data collection tools to explore properties and relationships.
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            elements = get_elems(ifc_file, element_type)
            element_ids = [elem.GlobalId for elem in elements]

            return {
                "element_type": element_type,
                "element_ids": element_ids,
                "count": len(element_ids)
            }
    except Exception as e:
        return {"element_type": element_type, "error": f"Failed to get elements: {str(e)}"}
