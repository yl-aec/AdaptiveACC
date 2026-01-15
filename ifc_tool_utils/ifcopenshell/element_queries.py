"""
Element Queries - Atomic functions for basic IFC element operations

These functions provide fundamental element query operations that return
native ifcopenshell objects or basic Python types.
"""

import ifcopenshell
from typing import List, Optional, Union


def get_elements_by_type(ifc_file: ifcopenshell.file, element_type: str) -> List[ifcopenshell.entity_instance]:
    """Get all elements of specified IFC type.

    Args:
        ifc_file: Open IFC file instance
        element_type: IFC type string (e.g., "IfcWall", "IfcDoor")

    Returns:
        List of IFC element instances
    """
    if not ifc_file:
        return []
    return ifc_file.by_type(element_type)


def get_element_by_id(ifc_file: ifcopenshell.file, global_id: str) -> Optional[ifcopenshell.entity_instance]:
    """Get element by GlobalId.

    Args:
        ifc_file: Open IFC file instance
        global_id: Element's GlobalId

    Returns:
        IFC element instance or None if not found
    """
    if not ifc_file:
        return None
    try:
        return ifc_file.by_guid(global_id)
    except RuntimeError:
        return None


def get_elements_by_ids(ifc_file: ifcopenshell.file, global_ids: List[str]) -> List[ifcopenshell.entity_instance]:
    """Get multiple elements by their GlobalIds.

    Args:
        ifc_file: Open IFC file instance
        global_ids: List of GlobalId strings

    Returns:
        List of found IFC element instances (excludes not found elements)
    """
    elements = []
    for global_id in global_ids:
        element = get_element_by_id(ifc_file, global_id)
        if element:
            elements.append(element)
    return elements


def get_elements_by_property_value(
    ifc_file: ifcopenshell.file,
    element_type: str,
    property_name: str,
    property_value,
    pset_name: Optional[str] = None
) -> List[ifcopenshell.entity_instance]:
    """Get elements filtered by a simple property value.

    Filters elements where a specific property matches the given value.
    Searches in property sets if pset_name specified, otherwise searches direct attributes.

    Args:
        ifc_file: Open IFC file instance
        element_type: IFC type string (e.g., "IfcWall", "IfcDoor")
        property_name: Name of the property to check
        property_value: Expected value of the property
        pset_name: Optional property set name to search in

    Returns:
        List of IFC element instances where property matches value

    Example:
        # Get all external walls using direct attribute
        external_walls = get_elements_by_property_value(
            ifc_file, "IfcWall", "IsExternal", True
        )

        # Get fire-rated doors from property set
        fire_doors = get_elements_by_property_value(
            ifc_file, "IfcDoor", "FireRating", "EI30", "Pset_DoorCommon"
        )
    """
    import ifcopenshell.util.element

    if not ifc_file:
        return []

    elements = get_elements_by_type(ifc_file, element_type)
    filtered = []

    for element in elements:
        if pset_name:
            # Use ifcopenshell.util.element.get_psets() instead of removed get_all_psets()
            psets = ifcopenshell.util.element.get_psets(element)
            if pset_name in psets and property_name in psets[pset_name]:
                if psets[pset_name][property_name] == property_value:
                    filtered.append(element)
        else:
            if hasattr(element, property_name) and getattr(element, property_name) == property_value:
                filtered.append(element)

    return filtered
