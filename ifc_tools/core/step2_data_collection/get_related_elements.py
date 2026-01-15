"""
Relationship Queries Tools
Category: data_collection (Step2 - Data Collection)
Description: Gets elements related through IFC relationships.
"""

from typing import Dict, Any, Optional, List
import ifcopenshell.util.element
from ifc_tool_utils.ifcopenshell import get_element_by_id
from ifc_tool_utils.ifcopenshell.relationship_queries import (
    get_host_element,
    get_filling_elements,
)
from utils.ifc_file_manager import IFCFileManager


def get_related_elements(
    ifc_file_path: str,
    element_ids: List[str],
    relationship_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get elements related through IFC relationships (batch version).

    This function discovers various types of relationships for a list of elements:
    - Spatial containment (which space/storey contains this element)
    - Host relationships (which wall hosts this door)
    - Contained elements (elements contained in a spatial element)
    - Filling elements (doors/windows filling an opening in a wall)

    Args:
        ifc_file_path: Path to the IFC file
        element_ids: List of element GlobalIds
        relationship_type: Optional filter for specific relationship types:
                          - "container" - Get spatial container (space, storey, building)
                          - "host" - Get host element (wall for door/window)
                          - "contained" - Get elements contained in this spatial element
                          - "filling" - Get filling elements (doors/windows in wall)
                          - None - Get all relationships

    Returns:
        Dictionary with:
        - element_ids: Input list of element GlobalIds
        - relationship_type: Requested relationship type filter (or None)
        - elements: List of dicts, each containing:
            - element_id: GlobalId of the element
            - relationships: List of relationship dicts, each with:
                - type: Relationship type description
                - related_elements: List of related element IDs
            - error: Optional error message if element not found
        - count: Number of elements processed

        Returns error dict if operation fails.

    Example:
        result = get_related_elements(
            "model.ifc",
            ["2O2Fr$t4X7Zf8NOew3FLOH", "3O2Fr$t4X7Zf8NOew3FLOI"],
            "host"
        )
        # result["elements"][0] -> relationships for first element
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            elements_out: List[Dict[str, Any]] = []

            for element_id in element_ids:
                element = get_element_by_id(ifc_file, element_id)
                if not element:
                    elements_out.append({
                        "element_id": element_id,
                        "relationships": [],
                        "error": "Element not found"
                    })
                    continue

                relationships: List[Dict[str, Any]] = []

                # Helper to add relationship if elements found
                def add_relationship(rel_type: str, related) -> None:
                    if not related:
                        return
                    ids = [e.GlobalId for e in related if e and hasattr(e, "GlobalId")]
                    if ids:
                        relationships.append({
                            "type": rel_type,
                            "related_elements": ids
                        })

                # Spatial container
                if relationship_type is None or relationship_type == "container":
                    container = ifcopenshell.util.element.get_container(element)
                    if container:
                        add_relationship("container", [container])

                # Host element (for doors, windows)
                if relationship_type is None or relationship_type == "host":
                    host = get_host_element(element)
                    if host:
                        add_relationship("host", [host])

                # Contained elements (for spatial elements)
                if relationship_type is None or relationship_type == "contained":
                    contained = ifcopenshell.util.element.get_contained(element)
                    if contained:
                        add_relationship("contained", contained)

                # Filling elements (for walls - get doors/windows)
                if relationship_type is None or relationship_type == "filling":
                    fillings = get_filling_elements(element)
                    if fillings:
                        add_relationship("filling", fillings)

                elements_out.append({
                    "element_id": element_id,
                    "relationships": relationships
                })

            return {
                "element_ids": element_ids,
                "relationship_type": relationship_type,
                "elements": elements_out,
                "count": len(elements_out)
            }
    except Exception as e:
        return {
            "element_ids": element_ids,
            "relationship_type": relationship_type,
            "error": f"Failed to get relationships: {str(e)}"
        }
