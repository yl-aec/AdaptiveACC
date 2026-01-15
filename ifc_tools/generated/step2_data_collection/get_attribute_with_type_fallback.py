"""
Tool: get_attribute_with_type_fallback
Category: step2_data_collection
Description: Retrieves an attribute from elements, falling back to their Type Object if the instance attribute is missing.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id

def get_attribute_with_type_fallback(ifc_file_path: str, element_ids: List[str], attribute_name: str) -> Dict[str, Any]:
    """Retrieve an attribute value for elements, falling back to the Type Object if missing on the instance.

    For each provided element GlobalId, this function attempts to retrieve the specified
    attribute (e.g., 'Description', 'ObjectType', 'PredefinedType'). If the attribute
    is None or missing on the element instance, it checks the associated IfcTypeObject
    (via IsTypedBy) and retrieves the value from there.

    Args:
        ifc_file_path: Path to the IFC file.
        element_ids: List of GlobalIds of the elements to query.
        attribute_name: The name of the direct IFC attribute to retrieve.

    Returns:
        A dictionary mapping element GlobalIds to the resolved attribute value.
        Returns None for an ID if the element is not found or the attribute exists nowhere.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    results = {}

    for eid in element_ids:
        element = get_element_by_id(ifc_file, eid)
        
        if element is None:
            results[eid] = None
            continue

        # Try to get attribute from the instance
        value = getattr(element, attribute_name, None)

        # If instance value is missing, try the Type Object
        if value is None:
            type_obj = ifcopenshell.util.element.get_type(element)
            if type_obj:
                value = getattr(type_obj, attribute_name, None)

        results[eid] = value

    return results