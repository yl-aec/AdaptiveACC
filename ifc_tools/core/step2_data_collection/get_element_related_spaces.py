"""
Element-Space Boundary Tools
Category: data_collection (Step2 - Data Collection)
Description: Gets spaces related to elements via space boundaries (inverse view).
"""

from typing import Dict, Any, List, Optional
from ifc_tool_utils.ifcopenshell import get_element_by_id
from ifc_tool_utils.ifcopenshell.relationship_queries import get_space_boundaries
from utils.ifc_file_manager import IFCFileManager


def get_element_related_spaces(
    ifc_file_path: str,
    element_ids: List[str],
    boundary_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get spaces related to elements via space boundaries.

    This tool is the inverse view of ``get_space_related_elements``.
    For each requested element (typically doors, windows, or walls), it finds
    all IfcSpace instances that are connected to the element through
    IfcRelSpaceBoundary relationships.

    Args:
        ifc_file_path: Path to the IFC file.
        element_ids: List of element GlobalIds to analyze (e.g., door IDs).
        boundary_type: Optional filter for boundary type:
                       - "INTERNAL"  -> only internal boundaries
                       - "EXTERNAL"  -> only external boundaries
                       - None        -> all boundaries

    Returns:
        Dictionary with:
        - boundary_type: Requested boundary_type filter (or None)
        - element_ids: Input list of element GlobalIds
        - elements: List of dicts, each containing:
            - element_id: GlobalId of the element
            - ifc_type: IFC type string of the element
            - related_spaces: List of dicts with:
                - space_id: GlobalId of the related space
                - ifc_type: IFC type string for the space (typically "IfcSpace")
              Spaces are deduplicated per element.
            - count: Number of related spaces for this element
            - error: Optional error message if element not found
        - count: Number of elements processed in total

        Returns error dict if operation fails.
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            elements_out: List[Dict[str, Any]] = []

            # Build an index: host element GlobalId -> list of spaces
            boundaries = get_space_boundaries(ifc_file, None, boundary_type)
            element_to_spaces: Dict[str, List[Any]] = {}

            for boundary in boundaries:
                space = getattr(boundary, "RelatingSpace", None)
                host_element = getattr(boundary, "RelatedBuildingElement", None)

                if not space or not host_element:
                    continue
                if not hasattr(space, "GlobalId") or not hasattr(host_element, "GlobalId"):
                    continue

                element_id = host_element.GlobalId
                if not element_id:
                    continue

                bucket = element_to_spaces.setdefault(element_id, [])
                if space not in bucket:
                    bucket.append(space)

            # Build output per requested element
            for element_id in element_ids:
                element = get_element_by_id(ifc_file, element_id)
                if not element:
                    elements_out.append({
                        "element_id": element_id,
                        "ifc_type": None,
                        "related_spaces": [],
                        "count": 0,
                        "error": "Element not found",
                    })
                    continue

                spaces = element_to_spaces.get(element_id, [])
                related_spaces = [
                    {
                        "space_id": s.GlobalId,
                        "ifc_type": s.is_a() if hasattr(s, "is_a") else None,
                    }
                    for s in spaces
                    if hasattr(s, "GlobalId") and s.GlobalId
                ]

                elements_out.append({
                    "element_id": element_id,
                    "ifc_type": element.is_a() if hasattr(element, "is_a") else None,
                    "related_spaces": related_spaces,
                    "count": len(related_spaces),
                })

            return {
                "boundary_type": boundary_type,
                "element_ids": element_ids,
                "elements": elements_out,
                "count": len(elements_out),
            }

    except Exception as e:
        return {
            "boundary_type": boundary_type,
            "element_ids": element_ids,
            "error": f"Failed to get element related spaces: {str(e)}",
        }
