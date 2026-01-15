"""
Tool: extract_element_attributes
Category: step2_data_collection
Description: Retrieve specific attributes (e.g., Name, ObjectType) for a list of IFC element GlobalIds.
"""

import ifcopenshell
from typing import List, Dict, Any, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id

def extract_element_attributes(ifc_file_path: str, element_ids: List[str], attribute_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Retrieve specific direct attributes for a provided list of IFC element GlobalIds.

    This tool fetches direct IFC attributes (e.g., 'Name', 'ObjectType', 'PredefinedType', 'Description')
    for elements identified by their GlobalId. It does not retrieve properties from Property Sets.

    Args:
        ifc_file_path: Path to the IFC file.
        element_ids: List of GlobalIds to query.
        attribute_names: List of attribute names to retrieve (case-sensitive, e.g., ['Name', 'GlobalId']).

    Returns:
        A dictionary where keys are GlobalIds and values are dictionaries of the requested attributes.
        If an element is not found, its value in the main dictionary will be None.
        If an attribute does not exist on an element, its value will be None.

    Example:
        >>> extract_element_attributes("model.ifc", ["324...", "123..."], ["Name", "ObjectType"])
        {
            "324...": {"Name": "Wall-01", "ObjectType": "Basic Wall:200mm"},
            "123...": None
        }
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except (FileNotFoundError, OSError):
        raise ValueError(f"IFC file not found or invalid: {ifc_file_path}")

    results = {}

    for global_id in element_ids:
        element = get_element_by_id(ifc_file, global_id)

        if element is None:
            results[global_id] = None
            continue

        element_data = {}
        for attr_name in attribute_names:
            # Use getattr to safely retrieve the attribute.
            # Returns None if the attribute does not exist on the entity.
            value = getattr(element, attr_name, None)
            
            # If the value is a function (e.g. .id()), we skip it or return None to avoid serialization issues,
            # but standard attributes are not callables.
            element_data[attr_name] = value

        results[global_id] = element_data

    return results