"""
Quantity Queries - Functions for IFC quantity set operations

These functions provide quantity query operations for extracting geometric
and calculated quantities from IfcElementQuantity sets.
"""

import ifcopenshell
from typing import Dict, Any, Optional, List


def get_element_quantities(
    ifc_file: ifcopenshell.file,
    element_ids: List[str],
    quantity_names: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Batch extract quantity values from multiple elements.

    Extracts quantities from IfcElementQuantity sets (Qto_* standard quantity sets).
    Quantities include areas, volumes, lengths, counts, weights, etc.

    Args:
        ifc_file: Open IFC file instance
        element_ids: List of element GlobalIds
        quantity_names: Optional list of specific quantity names to extract.
                       If None, extracts all available quantities.

    Returns:
        List of dictionaries, each containing:
        - element_id: GlobalId of the element
        - quantities: Dict mapping quantity names to values
                     Empty dict if no quantities found

    Example:
        # Extract specific quantities
        results = get_element_quantities(
            ifc_file,
            ["space1", "space2"],
            ["NetFloorArea", "GrossFloorArea"]
        )
        # Returns: [
        #     {"element_id": "space1", "quantities": {"NetFloorArea": 35.5, "GrossFloorArea": 38.2}},
        #     {"element_id": "space2", "quantities": {"NetFloorArea": 42.0, "GrossFloorArea": 45.1}}
        # ]
    """
    results = []

    for element_id in element_ids:
        try:
            element = ifc_file.by_guid(element_id)
        except RuntimeError:
            # Element not found
            results.append({"element_id": element_id, "quantities": {}})
            continue

        quantities = {}

        # Check if element has quantity definitions
        if hasattr(element, 'IsDefinedBy'):
            for rel in element.IsDefinedBy:
                # Look for IfcRelDefinesByProperties with IfcElementQuantity
                if rel.is_a('IfcRelDefinesByProperties'):
                    qto = rel.RelatingPropertyDefinition

                    if qto.is_a('IfcElementQuantity'):
                        # Iterate through quantities in the set
                        for quantity in qto.Quantities:
                            quantity_name = quantity.Name

                            # Filter by quantity_names if specified
                            if quantity_names and quantity_name not in quantity_names:
                                continue

                            # Extract value based on quantity type
                            value = _extract_quantity_value(quantity)
                            if value is not None:
                                quantities[quantity_name] = value

        results.append({"element_id": element_id, "quantities": quantities})

    return results


def find_all_quantities(element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Find all quantity sets (IfcElementQuantity) for an element.

    Args:
        element: IFC element instance

    Returns:
        List of IfcElementQuantity objects
    """
    quantities = []
    if not element or not hasattr(element, 'IsDefinedBy'):
        return quantities

    for rel in element.IsDefinedBy:
        if rel.is_a('IfcRelDefinesByProperties'):
            qto = rel.RelatingPropertyDefinition
            if qto.is_a('IfcElementQuantity'):
                quantities.append(qto)

    return quantities


def get_quantity_value(element: ifcopenshell.entity_instance, qto_name: str, quantity_name: str) -> Optional[Dict[str, Any]]:
    """Get quantity value from specified quantity set with unit information.

    Args:
        element: IFC element instance
        qto_name: Quantity set name (e.g., "Qto_WindowBaseQuantities")
        quantity_name: Quantity name (e.g., "Height", "Width")

    Returns:
        Dict with 'value' and 'unit' keys, or None if not found
        Example: {"value": 0.9, "unit": "m"}
    """
    qtos = find_all_quantities(element)

    for qto in qtos:
        if qto.Name == qto_name:
            for quantity in qto.Quantities:
                if quantity.Name == quantity_name:
                    value = _extract_quantity_value(quantity)
                    unit = quantity.Unit if hasattr(quantity, 'Unit') else None

                    # Extract simplified unit name
                    unit_str = None
                    if unit:
                        from .property_queries import _extract_unit_name
                        unit_str = _extract_unit_name(unit)

                    return {"value": value, "unit": unit_str}

    return None


def _extract_quantity_value(quantity: ifcopenshell.entity_instance) -> Optional[float]:
    """Extract value from different IFC quantity types.

    Args:
        quantity: IFC quantity instance (IfcQuantityLength, IfcQuantityArea, etc.)

    Returns:
        Numeric value or None if not extractable
    """
    # Common quantity types and their value attributes
    value_attributes = [
        'LengthValue',      # IfcQuantityLength
        'AreaValue',        # IfcQuantityArea
        'VolumeValue',      # IfcQuantityVolume
        'CountValue',       # IfcQuantityCount
        'WeightValue',      # IfcQuantityWeight
        'TimeValue',        # IfcQuantityTime
    ]

    for attr in value_attributes:
        if hasattr(quantity, attr):
            value = getattr(quantity, attr)
            if value is not None:
                return value

    return None
