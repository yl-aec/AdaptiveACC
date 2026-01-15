"""
PredefinedType-based Element Identification
Category: identification (Step1 - Identification & Scoping)
Description: Identifies elements by IFC type and PredefinedType attribute.
"""

from typing import Dict, Any
from ifc_tool_utils.ifcopenshell import get_elements_by_type
from utils.ifc_file_manager import IFCFileManager


def get_elements_by_predefined_type(
    ifc_file_path: str,
    element_type: str,
    predefined_type: str
) -> Dict[str, Any]:
    """Get elements by IFC type and PredefinedType attribute.

    Identifies elements of a specific IFC type that have a matching PredefinedType.
    PredefinedType is a standard IFC attribute that provides additional classification
    within an element type (e.g., SOLIDWALL vs ELEMENTEDWALL for walls, SWING vs SLIDING for doors).

    This is a specialized filtering tool for a common use case in compliance checking,
    where regulations often distinguish between element subtypes (e.g., "load-bearing walls"
    typically correspond to SOLIDWALL predefined type).

    Args:
        ifc_file_path: Path to the IFC file
        element_type: IFC type string (e.g., "IfcWall", "IfcDoor", "IfcSlab")
        predefined_type: PredefinedType value to filter by (e.g., "SOLIDWALL", "SWING", "ROOF")

    Returns:
        Dictionary with:
        - element_type: The requested IFC type
        - predefined_type: The requested PredefinedType value
        - element_ids: List of GlobalId strings for matching elements
        - count: Total number of elements found

        Returns error dict if operation fails.

    Example:
        # Get all solid walls
        result = get_elements_by_predefined_type("model.ifc", "IfcWall", "SOLIDWALL")
        # Returns: {"element_type": "IfcWall",
        #           "predefined_type": "SOLIDWALL",
        #           "element_ids": ["2O2Fr$...", ...], "count": 15}

        # Get all swing doors
        result = get_elements_by_predefined_type("model.ifc", "IfcDoor", "SWING")
        # Returns: {"element_type": "IfcDoor",
        #           "predefined_type": "SWING",
        #           "element_ids": ["3O2Fr$...", ...], "count": 8}

        # Get roof slabs
        result = get_elements_by_predefined_type("model.ifc", "IfcSlab", "ROOF")
        # Returns: {"element_type": "IfcSlab",
        #           "predefined_type": "ROOF",
        #           "element_ids": ["4O2Fr$...", ...], "count": 3}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            # Get all elements of the specified type
            elements = get_elements_by_type(ifc_file, element_type)

            # Filter by PredefinedType
            filtered = []
            for element in elements:
                if hasattr(element, 'PredefinedType'):
                    element_predefined_type = element.PredefinedType
                    # Handle enum types by converting to string
                    if element_predefined_type is not None:
                        predefined_type_str = str(element_predefined_type)
                        if predefined_type_str == predefined_type:
                            filtered.append(element)

            element_ids = [elem.GlobalId for elem in filtered]

            return {
                "element_type": element_type,
                "predefined_type": predefined_type,
                "element_ids": element_ids,
                "count": len(element_ids)
            }

    except Exception as e:
        return {
            "element_type": element_type,
            "predefined_type": predefined_type,
            "error": f"Failed to get elements by predefined type: {str(e)}"
        }
