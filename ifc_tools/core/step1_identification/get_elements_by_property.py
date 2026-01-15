"""
Property-based Element Identification
Category: identification (Step1 - Identification & Scoping)
Description: Identifies elements by property values from attributes or property sets.
"""

from typing import Dict, Any, Optional
import ifcopenshell.util.element
from ifc_tool_utils.ifcopenshell import (
    get_elements_by_property_value,
    get_elements_by_type,
    get_pset_property,
)
from utils.ifc_file_manager import IFCFileManager


def get_elements_by_property(
    ifc_file_path: str,
    element_type: str,
    property_name: str,
    property_value: Any,
    pset_name: Optional[str] = None
) -> Dict[str, Any]:
    """Get elements matching a specific property value.

    Identifies elements where a specific property matches the given value.
    Searches in property sets if pset_name is specified, otherwise searches
    direct element attributes (like IsExternal, Tag, etc.).

    Args:
        ifc_file_path: Path to the IFC file
        element_type: IFC type string (e.g., "IfcWall", "IfcDoor", "IfcSpace")
        property_name: Name of the property to check
        property_value: Expected value of the property (can be str, int, float, bool)
        pset_name: Optional property set name to search in (e.g., "Pset_WallCommon")

    Returns:
        Dictionary with:
        - element_type: The requested IFC type
        - property_filter: Dictionary describing the filter criteria
        - element_ids: List of GlobalId strings for matching elements
        - count: Total number of elements found

        Returns error dict if operation fails.

    Example:
        # Get all external walls using direct attribute
        result = get_elements_by_property("model.ifc", "IfcWall", "IsExternal", True)
        # Returns: {"element_type": "IfcWall",
        #           "property_filter": {"property_name": "IsExternal", "value": True},
        #           "element_ids": ["2O2Fr$...", ...], "count": 24}

        # Get fire-rated doors from property set
        result = get_elements_by_property(
            "model.ifc", "IfcDoor", "FireRating", "EI30", "Pset_DoorCommon"
        )
        # Returns: {"element_type": "IfcDoor",
        #           "property_filter": {"pset": "Pset_DoorCommon", "property_name": "FireRating", "value": "EI30"},
        #           "element_ids": ["3O2Fr$...", ...], "count": 6}
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            def _matches_property(element) -> bool:
                """Match direct attr, any Pset, or type Pset when pset_name is None."""
                # Direct attribute
                if hasattr(element, property_name) and getattr(element, property_name) == property_value:
                    return True

                # Any property set on the element
                psets = ifcopenshell.util.element.get_psets(element)
                for props in psets.values():
                    if isinstance(props, dict) and property_name in props and props[property_name] == property_value:
                        return True

                # Property sets on the type object (if present)
                type_element = ifcopenshell.util.element.get_type(element)
                if type_element:
                    type_psets = ifcopenshell.util.element.get_psets(type_element)
                    for props in type_psets.values():
                        if isinstance(props, dict) and property_name in props and props[property_name] == property_value:
                            return True

                return False

            if pset_name:
                # Precise mode: delegate to existing helper to match only the specified Pset
                elements = get_elements_by_property_value(
                    ifc_file,
                    element_type,
                    property_name,
                    property_value,
                    pset_name
                )
            else:
                # Smart mode: search direct attributes, any Pset, and type Psets
                elements = [
                    element
                    for element in get_elements_by_type(ifc_file, element_type)
                    if _matches_property(element)
                ]

            element_ids = [elem.GlobalId for elem in elements]

            property_filter = {
                "property_name": property_name,
                "value": property_value
            }

            if pset_name:
                property_filter["pset"] = pset_name

            return {
                "element_type": element_type,
                "property_filter": property_filter,
                "element_ids": element_ids,
                "count": len(element_ids)
            }

    except Exception as e:
        return {
            "element_type": element_type,
            "property_filter": {
                "property_name": property_name,
                "value": property_value
            },
            "error": f"Failed to filter by property: {str(e)}"
        }
