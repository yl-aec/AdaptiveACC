"""
Property Inspection Tools
Category: data_collection (Step2 - Data Collection)
Description: Inspects complete raw data for elements including attributes, property sets, and quantities.
"""

from typing import Dict, Any
import ifcopenshell.util.element
from ifc_tool_utils.ifcopenshell import (
    get_element_by_id,
    find_all_psets,
    get_pset_property,
)
from ifc_tool_utils.ifcopenshell.quantity_queries import (
    find_all_quantities,
    get_quantity_value
)
from utils.ifc_file_manager import IFCFileManager


def inspect_element_properties(
    ifc_file_path: str,
    element_id: str,
) -> Dict[str, Any]:
    """Inspect raw data for a single element: attributes, property sets, and quantities.

    This tool is intended for investigation and exploration. Given an element
    GlobalId (for example, IfcWindow, IfcDoor, IfcWall), it dumps all available data
    sources for that element so that downstream tools or agents can see where specific
    information (such as height) is stored.

    The returned data includes:
    - attributes: Native IFC attributes via element.get_info()
    - property_sets: All IfcPropertySet values via find_all_psets()
    - quantities: All IfcElementQuantity values via find_all_quantities()
    - type_info: Type object information (if element has a type)
        - type_name: Name of the type (e.g., "Entrance Door 27")
        - type_class: IFC class (e.g., "IfcDoorType")
        - type_attributes: Dict of type attributes
        - type_property_sets: Dict of type property sets

    Args:
        ifc_file_path: Path to the IFC file
        element_id: Single element GlobalId to inspect

    Returns:
        Dictionary with:
        - element_id: GlobalId of the element
        - ifc_type: IFC type string (e.g., "IfcWindow")
        - attributes: Dict of native IFC attributes
        - property_sets: Dict of property sets and their properties
                         {pset_name: {prop_name: {"value": v, "unit": u}}}
        - quantities: Dict of quantities from IfcElementQuantity sets
                      {qto_name: {quantity_name: {"value": v, "unit": u}}}
        - type_info: Type object information (None if no type)
        - error: Optional error message if element not found

        Returns error dict if operation fails.
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {
                    "element_id": element_id,
                    "error": "Element not found"
                }

            # 1) Native attributes
            attributes: Dict[str, Any] = {}
            if hasattr(element, "get_info"):
                attributes = element.get_info()

            # 2) Property sets with values and units
            property_sets: Dict[str, Dict[str, Any]] = {}
            psets = find_all_psets(element)
            for pset in psets:
                props: Dict[str, Any] = {}
                for prop in getattr(pset, "HasProperties", []):
                    prop_name = getattr(prop, "Name", None)
                    if not prop_name:
                        continue
                    prop_result = get_pset_property(element, pset.Name, prop_name)
                    if prop_result is None:
                        props[prop_name] = {"value": None, "unit": None}
                    else:
                        props[prop_name] = {
                            "value": prop_result.get("value"),
                            "unit": prop_result.get("unit")
                        }
                property_sets[pset.Name] = props

            # 3) Quantity sets with values and units
            quantities: Dict[str, Dict[str, Any]] = {}
            qtos = find_all_quantities(element)
            for qto in qtos:
                qto_quantities: Dict[str, Any] = {}
                for quantity in getattr(qto, "Quantities", []):
                    q_name = getattr(quantity, "Name", None)
                    if not q_name:
                        continue
                    q_result = get_quantity_value(element, qto.Name, q_name)
                    if q_result is None:
                        qto_quantities[q_name] = {"value": None, "unit": None}
                    else:
                        qto_quantities[q_name] = {
                            "value": q_result.get("value"),
                            "unit": q_result.get("unit")
                        }
                quantities[qto.Name] = qto_quantities

            # 4) Type object information
            type_info = None
            type_element = ifcopenshell.util.element.get_type(element)
            if type_element:
                # Type attributes
                type_attributes: Dict[str, Any] = {}
                if hasattr(type_element, "get_info"):
                    type_attributes = type_element.get_info()

                # Type property sets
                type_property_sets: Dict[str, Dict[str, Any]] = {}
                type_psets = find_all_psets(type_element)
                for pset in type_psets:
                    props: Dict[str, Any] = {}
                    for prop in getattr(pset, "HasProperties", []):
                        prop_name = getattr(prop, "Name", None)
                        if not prop_name:
                            continue
                        prop_result = get_pset_property(type_element, pset.Name, prop_name)
                        if prop_result is None:
                            props[prop_name] = {"value": None, "unit": None}
                        else:
                            props[prop_name] = {
                                "value": prop_result.get("value"),
                                "unit": prop_result.get("unit")
                            }
                    type_property_sets[pset.Name] = props

                type_info = {
                    "type_name": type_element.Name if hasattr(type_element, "Name") else None,
                    "type_class": type_element.is_a() if hasattr(type_element, "is_a") else None,
                    "type_attributes": type_attributes,
                    "type_property_sets": type_property_sets
                }

            return {
                "element_id": element_id,
                "ifc_type": element.is_a() if hasattr(element, "is_a") else None,
                "attributes": attributes,
                "property_sets": property_sets,
                "quantities": quantities,
                "type_info": type_info
            }

    except Exception as e:
        return {
            "error": f"Failed to inspect element: {str(e)}"
        }
