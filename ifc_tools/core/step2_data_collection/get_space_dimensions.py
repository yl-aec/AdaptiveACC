"""
Space Dimension Extraction Tools
Category: data_collection (Step2 - Data Collection)
Description: Extracts accurate space dimensions using BREP geometry with OBB.
"""

from typing import Dict, Any, List
from ifc_tool_utils.ifcopenshell.geometry_queries import get_element_geometry_metrics
from utils.ifc_file_manager import IFCFileManager


def get_space_dimensions(
    ifc_file_path: str,
    space_ids: List[str],
    method: str = "auto"
) -> Dict[str, Any]:
    """Extract accurate space dimensions with IfcSpace-specific enhancements.

    Calls get_element_geometry_metrics() from ifc_tool_utils and adds batch processing for multiple spaces.

    Uses BREP (Boundary Representation) geometry with OBB (Oriented Bounding Box)
    for accurate dimension calculation. This method is far more accurate than
    Space Boundaries which can include wall thickness and adjacent spaces.

    Args:
        ifc_file_path: Path to IFC file
        space_ids: List of IfcSpace GlobalIds to analyze
        method: "obb" (Oriented Bounding Box, recommended) - default and only supported method
                Parameter kept for API consistency but only "obb" is used

    Returns:
        {
            "method": "auto",
            "spaces": [
                {
                    "space_id": "3NIx40Q_PDXvRSHH8haptU",
                    "space_name": "Essen",
                    "width_mm": 986.0,
                    "depth_mm": 2726.0,
                    "height_mm": 2600.0,
                    "area_m2": 2.687,
                    "calculation_method": "obb",
                    "error": null
                },
                ...
            ],
            "count": 9,
            "success_count": 9,
            "error_count": 0
        }

    Use cases:
        # Replace inaccurate Space Boundaries method
        # OLD: dimensions from IfcRelSpaceBoundary (includes wall thickness)
        # NEW: dimensions from BREP+OBB (actual space geometry)
    """
    results = {
        "method": method,
        "spaces": [],
        "count": len(space_ids),
        "success_count": 0,
        "error_count": 0
    }

    with IFCFileManager(ifc_file_path) as ifc_file:
        for space_id in space_ids:
            space = ifc_file.by_guid(space_id)

            if not space or not space.is_a('IfcSpace'):
                results["spaces"].append({
                    "space_id": space_id,
                    "error": "Not a valid IfcSpace"
                })
                results["error_count"] += 1
                continue

            # Get space name
            space_name = space.LongName if hasattr(space, 'LongName') else space.Name

            # Call low-level geometry function (always use OBB)
            dims = get_element_geometry_metrics(space, method="obb")
            calc_method = "obb" if dims else None

            if dims:
                results["spaces"].append({
                    "space_id": space_id,
                    "space_name": space_name,
                    "width_mm": dims["width_mm"],
                    "depth_mm": dims["depth_mm"],
                    "height_mm": dims["height_mm"],
                    "area_m2": dims["area_m2"],
                    "calculation_method": calc_method,
                    "error": None
                })
                results["success_count"] += 1
            else:
                results["spaces"].append({
                    "space_id": space_id,
                    "space_name": space_name,
                    "error": f"Failed to calculate dimensions using {method}"
                })
                results["error_count"] += 1

    return results
