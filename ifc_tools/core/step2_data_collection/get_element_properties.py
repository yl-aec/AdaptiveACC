"""
Property Extraction Tools
Category: data_collection (Step2 - Data Collection)
Description: Smart property extraction from IFC elements with automatic fallback.
"""

from typing import Dict, Any, List, Optional
import ifcopenshell.util.element
from ifc_tool_utils.ifcopenshell import (
    get_direct_attribute,
    find_all_psets,
    get_pset_property,
)
from ifc_tool_utils.ifcopenshell.quantity_queries import (
    find_all_quantities,
    get_quantity_value
)
from utils.ifc_file_manager import IFCFileManager


def get_element_properties(
    ifc_file_path: str,
    element_ids: List[str],
    property_name: str,
    pset_name: Optional[str] = None
) -> Dict[str, Any]:
    """Smart property extraction with automatic fallback across multiple sources.

    This is the primary tool for extracting properties from IFC elements. It automatically
    searches multiple property sources in priority order:
    1. Direct attributes (e.g., IfcWindow.OverallHeight)
    2. Property sets (Pset_*)
    3. Quantity sets (Qto_*)
    4. Type object attributes (e.g., IfcDoorType.OperationType)
    5. Type object property sets

    Args:
        ifc_file_path: Path to the IFC file
        element_ids: List of element GlobalIds
        property_name: Property name to extract (e.g., "Height", "Width", "FireRating")
        pset_name: Optional specific property set name for targeted extraction.
                  If provided, searches only in that Pset (precise mode).
                  If None, searches all sources automatically (smart mode).

    Returns:
        Dictionary with:
        - property_name: Name of the requested property
        - pset_name: Specified Pset name or None
        - elements: List of dicts, each containing:
            - element_id: Element GlobalId
            - value: Property value (or None if not found)
            - unit: Unit string (e.g., "m", "mm", "m2") or None
            - source: Where the value was found ("attribute"|"pset"|"quantity"|"type_attribute"|"type_pset")
            - source_name: Specific source name (e.g., "Pset_DoorCommon", "OverallHeight")
        - count: Number of elements processed

    Examples:
        # Smart mode - automatically find "Height" from any source
        result = get_element_properties("model.ifc", window_ids, "Height")
        # May find from: IfcWindow.OverallHeight, Pset_WindowCommon.Height, Qto_WindowBaseQuantities.Height

        # Precise mode - extract from specific Pset only
        result = get_element_properties("model.ifc", door_ids, "FireRating", "Pset_DoorCommon")

        # Returns:
        # {
        #   "property_name": "Height",
        #   "pset_name": None,  # or "Pset_DoorCommon" if specified
        #   "elements": [
        #     {
        #       "element_id": "2O2Fr$t4X7Zf8NOew3FLOH",
        #       "value": 0.9,
        #       "unit": "m",
        #       "source": "attribute",
        #       "source_name": "OverallHeight"
        #     },
        #     {
        #       "element_id": "3P3Gs$u5Y8Ag9OPfx4GMPJ",
        #       "value": 900,
        #       "unit": "mm",
        #       "source": "pset",
        #       "source_name": "Pset_WindowCommon"
        #     }
        #   ],
        #   "count": 2
        # }
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            results = []

            for element_id in element_ids:
                try:
                    element = ifc_file.by_guid(element_id)
                except RuntimeError:
                    # Element not found
                    results.append({
                        "element_id": element_id,
                        "value": None,
                        "unit": None,
                        "source": None,
                        "source_name": None
                    })
                    continue

                # Extract property using smart or precise mode
                if pset_name:
                    # Precise mode: search only in specified Pset
                    prop_result = get_pset_property(element, pset_name, property_name)
                    if prop_result:
                        results.append({
                            "element_id": element_id,
                            "value": prop_result.get("value"),
                            "unit": prop_result.get("unit"),
                            "source": "pset",
                            "source_name": pset_name
                        })
                    else:
                        results.append({
                            "element_id": element_id,
                            "value": None,
                            "unit": None,
                            "source": None,
                            "source_name": None
                        })
                else:
                    # Smart mode: automatic fallback across sources
                    prop_result = _smart_property_search(element, property_name)
                    results.append({
                        "element_id": element_id,
                        **prop_result
                    })

            return {
                "property_name": property_name,
                "pset_name": pset_name,
                "elements": results,
                "count": len(results)
            }

    except Exception as e:
        return {
            "property_name": property_name,
            "pset_name": pset_name,
            "error": f"Failed to extract properties: {str(e)}"
        }


def _smart_property_search(element, property_name: str) -> Dict[str, Any]:
    """Internal function: Smart search for property across all sources.

    Search priority:
    1. Direct attributes (with common variants)
    2. All Property Sets (Pset_*)
    3. All Quantity Sets (Qto_*)
    4. Type object direct attributes (e.g., IfcDoorType.OperationType)
    5. Type object Property Sets

    Args:
        element: IFC element instance
        property_name: Property name to find

    Returns:
        Dict with value, unit, source, source_name
    """
    # 1. Try direct attributes with common variants
    attribute_variants = [
        property_name,  # Exact match (e.g., "Height")
        f"Overall{property_name}",  # Common IFC pattern (e.g., "OverallHeight")
        property_name.lower(),
        property_name.upper(),
        property_name.capitalize()
    ]

    for variant in attribute_variants:
        value = get_direct_attribute(element, variant)
        if value is not None:
            return {
                "value": value,
                "unit": None,  # Direct attributes typically don't have units
                "source": "attribute",
                "source_name": variant
            }

    # 2. Try all Property Sets
    psets = find_all_psets(element)
    for pset in psets:
        prop_result = get_pset_property(element, pset.Name, property_name)
        if prop_result and prop_result.get("value") is not None:
            return {
                "value": prop_result.get("value"),
                "unit": prop_result.get("unit"),
                "source": "pset",
                "source_name": pset.Name
            }

    # 3. Try all Quantity Sets
    qtos = find_all_quantities(element)
    for qto in qtos:
        qto_result = get_quantity_value(element, qto.Name, property_name)
        if qto_result and qto_result.get("value") is not None:
            return {
                "value": qto_result.get("value"),
                "unit": qto_result.get("unit"),
                "source": "quantity",
                "source_name": qto.Name
            }

    # 4. Try Type object
    type_element = ifcopenshell.util.element.get_type(element)
    if type_element:
        # 4a. Try type direct attributes (e.g., IfcDoorType.OperationType)
        for variant in attribute_variants:
            value = get_direct_attribute(type_element, variant)
            if value is not None:
                return {
                    "value": value,
                    "unit": None,
                    "source": "type_attribute",
                    "source_name": f"{type_element.is_a()}.{variant}"
                }

        # 4b. Try type property sets
        type_psets = find_all_psets(type_element)
        for pset in type_psets:
            prop_result = get_pset_property(type_element, pset.Name, property_name)
            if prop_result and prop_result.get("value") is not None:
                return {
                    "value": prop_result.get("value"),
                    "unit": prop_result.get("unit"),
                    "source": "type_pset",
                    "source_name": f"{type_element.Name}.{pset.Name}"
                }

    # Not found in any source
    return {
        "value": None,
        "unit": None,
        "source": None,
        "source_name": None
    }
