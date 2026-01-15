"""
Space Boundary Tools
Category: data_collection (Step2 - Data Collection)
Description: Gets building elements related to spaces via space boundaries.
"""

from typing import Dict, Any, List, Optional
from ifc_tool_utils.ifcopenshell import get_element_by_id
from ifc_tool_utils.ifcopenshell.relationship_queries import get_space_boundaries
from utils.ifc_file_manager import IFCFileManager


def get_space_related_elements(
    ifc_file_path: str,
    space_ids: List[str],
    boundary_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get elements related to spaces via space boundaries.

    This tool summarizes, for each requested IfcSpace, the building elements
    that form its boundaries. It uses IfcRelSpaceBoundary relationships as the
    primary source and returns a list of related elements (walls, doors,
    windows, slabs, etc.) with their IFC types.

    The function is intended as a higher-level, directly usable view compared
    to raw boundary dumps. It is typically used after identifying a subset of
    spaces (e.g., corridors, storage rooms) and you want to know which
    building elements are adjacent to those spaces.

    Args:
        ifc_file_path: Path to the IFC file
        space_ids: List of IfcSpace GlobalIds to analyze
        boundary_type: Optional filter for boundary type:
                       - "INTERNAL"  -> only internal boundaries
                       - "EXTERNAL"  -> only external boundaries
                       - None        -> all boundaries

    Returns:
        Dictionary with:
        - boundary_type: Requested boundary_type filter (or None)
        - spaces: List of dicts, each containing:
            - space_id: GlobalId of the space
            - related_elements: List of dicts with:
                - element_id: GlobalId of the related element
                - ifc_type: IFC type string of the related element
              Elements are deduplicated per space.
            - count: Number of related elements for this space
            - error: Optional error message if space not found or not IfcSpace
        - count: Number of spaces processed in total

        Returns error dict if operation fails.
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            spaces_out: List[Dict[str, Any]] = []

            for space_id in space_ids:
                space = get_element_by_id(ifc_file, space_id)
                if not space:
                    spaces_out.append({
                        "space_id": space_id,
                        "related_elements": [],
                        "count": 0,
                        "error": "Space not found",
                    })
                    continue

                if not space.is_a("IfcSpace"):
                    spaces_out.append({
                        "space_id": space_id,
                        "related_elements": [],
                        "count": 0,
                        "error": f"Element is {space.is_a()}, not IfcSpace",
                    })
                    continue

                # Get raw boundary relationships for this space
                boundaries = get_space_boundaries(ifc_file, space, boundary_type)

                # Collect unique related elements via boundaries
                related_map: Dict[str, Dict[str, Any]] = {}

                for boundary in boundaries:
                    host_element = getattr(boundary, "RelatedBuildingElement", None)
                    if not host_element or not hasattr(host_element, "GlobalId"):
                        continue

                    element_id = host_element.GlobalId
                    if not element_id:
                        continue

                    if element_id not in related_map:
                        related_map[element_id] = {
                            "element_id": element_id,
                            "ifc_type": host_element.is_a() if hasattr(host_element, "is_a") else None,
                        }

                spaces_out.append({
                    "space_id": space_id,
                    "related_elements": list(related_map.values()),
                    "count": len(related_map),
                })

            return {
                "boundary_type": boundary_type,
                "spaces": spaces_out,
                "count": len(spaces_out)
            }

    except Exception as e:
        return {
            "boundary_type": boundary_type,
            "error": f"Failed to get space related elements: {str(e)}"
        }
