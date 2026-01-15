"""
Tool: find_products_by_keywords
Category: step1_identification
Description: Search for all IfcProduct elements where the Name, ObjectType, Description, or PredefinedType contains any of the provided keywords (case-insensitive).
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any

def find_products_by_keywords(ifc_file_path: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Search for IfcProduct elements matching specific keywords in their attributes.

    Searches within Name, ObjectType, Description, and PredefinedType attributes.
    The search is case-insensitive.

    Args:
        ifc_file_path: Path to the IFC file.
        keywords: List of strings to search for.

    Returns:
        List of dictionaries containing element details and the matched property.
        Example: [{'GlobalId': '...', 'Name': 'Wall-01', 'IfcClass': 'IfcWall', 'matched_property': 'Name'}]
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except Exception as e:
        raise ValueError(f"Failed to load IFC file: {str(e)}")

    # Normalize keywords for case-insensitive search
    search_terms = [k.lower() for k in keywords if k]
    if not search_terms:
        return []

    products = ifc_file.by_type("IfcProduct")
    results = []

    for product in products:
        matched_prop = None

        # Check Name (IfcRoot)
        if product.Name:
            val = product.Name.lower()
            if any(term in val for term in search_terms):
                matched_prop = "Name"

        # Check ObjectType (IfcObject)
        if not matched_prop and product.ObjectType:
            val = product.ObjectType.lower()
            if any(term in val for term in search_terms):
                matched_prop = "ObjectType"

        # Check Description (IfcRoot)
        if not matched_prop and product.Description:
            val = product.Description.lower()
            if any(term in val for term in search_terms):
                matched_prop = "Description"

        # Check PredefinedType (Various subclasses)
        if not matched_prop:
            # ifcopenshell.util.element.get_predefined_type handles the attribute lookup safely
            p_type = ifcopenshell.util.element.get_predefined_type(product)
            if p_type:
                val = p_type.lower()
                if any(term in val for term in search_terms):
                    matched_prop = "PredefinedType"

        if matched_prop:
            results.append({
                "GlobalId": product.GlobalId,
                "Name": product.Name,
                "IfcClass": product.is_a(),
                "matched_property": matched_prop
            })

    return results