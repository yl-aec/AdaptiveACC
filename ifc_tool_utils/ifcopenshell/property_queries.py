"""
Property Queries - Atomic functions for IFC property and property set operations

These functions provide property query operations that return native Python types
or ifcopenshell objects for property data extraction.
"""

import ifcopenshell
from typing import Dict, Any, Optional, List, Union


def _extract_unit_name(unit) -> Optional[str]:
    """Extract simplified unit name from IFC unit object.

    Args:
        unit: IFC unit object

    Returns:
        Simplified unit string (e.g., "m", "mm", "m2") or None
    """
    if not unit:
        return None

    try:
        # Handle IfcSIUnit
        if unit.is_a('IfcSIUnit'):
            prefix_map = {
                'MILLI': 'm',
                'CENTI': 'c',
                'KILO': 'k',
                None: ''
            }
            prefix = prefix_map.get(unit.Prefix if hasattr(unit, 'Prefix') else None, '')

            unit_map = {
                'METRE': 'm',
                'SQUARE_METRE': 'm2',
                'CUBIC_METRE': 'm3',
                'GRAM': 'g',
                'SECOND': 's',
                'DEGREE_CELSIUS': '°C',
                'KELVIN': 'K',
                'PASCAL': 'Pa'
            }
            base_unit = unit_map.get(unit.Name, unit.Name)
            return f"{prefix}{base_unit}"

        # Handle other unit types
        elif hasattr(unit, 'Name'):
            return str(unit.Name)
    except:
        pass

    return None


def get_direct_attribute(element: ifcopenshell.entity_instance, attribute_name: str) -> Any:
    """Get direct attribute value from element (e.g., IfcWindow.OverallHeight).

    Args:
        element: IFC element instance
        attribute_name: Attribute name (e.g., "OverallHeight", "OverallWidth")

    Returns:
        Attribute value or None if not found
    """
    if not element or not hasattr(element, attribute_name):
        return None

    value = getattr(element, attribute_name)
    return value


def get_pset_property(element: ifcopenshell.entity_instance, pset_name: str, property_name: str) -> Optional[Dict[str, Any]]:
    """Get property value from property set with unit information.

    Args:
        element: IFC element instance
        pset_name: Property set name (e.g., "Pset_DoorCommon")
        property_name: Property name within the set

    Returns:
        Dict with 'value' and 'unit' keys, or None if not found
        Example: {"value": 0.9, "unit": "m"}
    """
    if not element or not hasattr(element, 'IsDefinedBy'):
        return None

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a('IfcPropertySet') and pset.Name == pset_name:
                for prop in pset.HasProperties:
                    if prop.Name == property_name:
                        value = None
                        if hasattr(prop, 'NominalValue') and prop.NominalValue:
                            value = prop.NominalValue.wrappedValue

                        # Extract unit if available
                        unit = None
                        if hasattr(prop, 'Unit') and prop.Unit:
                            unit = _extract_unit_name(prop.Unit)

                        return {"value": value, "unit": unit}
    return None


def find_all_psets(element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Find all property sets (IfcPropertySet) for an element.

    Args:
        element: IFC element instance

    Returns:
        List of IfcPropertySet objects (not including IfcElementQuantity)
    """
    psets = []
    if not element or not hasattr(element, 'IsDefinedBy'):
        return psets

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a('IfcPropertySet'):
                psets.append(pset)
    return psets


# Note: get_type_element() and get_all_psets() have been removed as they duplicate
# ifcopenshell.util.element.get_type() and ifcopenshell.util.element.get_psets().
# For sandbox execution, these functions are injected directly as 'get_type' and 'get_psets'.
# For non-sandbox code (like core tools), import ifcopenshell.util.element directly.
