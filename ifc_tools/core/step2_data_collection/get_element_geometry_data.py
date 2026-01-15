"""
Geometry Extraction Tools
Category: data_collection (Step2 - Data Collection)
Description: Extracts geometric data from IFC elements (placement, elevation, bounding box).
"""

from typing import Dict, Any, List
from ifc_tool_utils.ifcopenshell import get_element_by_id
from ifc_tool_utils.ifcopenshell.geometry_queries import (
    get_element_placement,
    get_element_elevation,
    get_element_bounding_box,
)
from utils.ifc_file_manager import IFCFileManager


def get_element_geometry_data(
    ifc_file_path: str,
    element_ids: List[str],
    geometry_type: str = "placement"
) -> Dict[str, Any]:
    """Extract geometric data from IFC elements.

    Batch extraction of geometric information (placement coordinates, elevation, or
    bounding box) for multiple elements. Returns the insertion point coordinates,
    not the geometric center.

    Args:
        ifc_file_path: Path to the IFC file
        element_ids: List of element GlobalIds
        geometry_type: Type of geometry data to extract:
            - "placement": Full 3D placement coordinates (x, y, z)
            - "elevation": Z-coordinate only (insertion point elevation)
            - "bounding_box": Complete axis-aligned bounding box with dimensions

    Returns:
        Dictionary with:
        - geometry_type: Type of geometry extracted
        - elements: List of dicts, each containing:
            For "placement" mode:
                - element_id: Element GlobalId
                - value: Dict with keys {x, y, z, location, has_placement}
                - has_geometry: Boolean indicating if geometry data exists
            For "elevation" mode:
                - element_id: Element GlobalId
                - value: Float elevation (Z coordinate) or None
                - has_geometry: Boolean indicating if geometry data exists
            For "bounding_box" mode:
                - element_id: Element GlobalId
                - value: Dict with keys {min_x, max_x, min_y, max_y, min_z, max_z, width, depth, height}
                - has_geometry: Boolean indicating if geometry data exists
        - count: Number of elements processed

    Examples:
        # Extract elevation for floor slabs
        result = get_element_geometry_data("model.ifc", slab_ids, "elevation")
        # Returns: {
        #   "geometry_type": "elevation",
        #   "elements": [
        #     {"element_id": "slab1", "value": 0.0, "has_geometry": True},
        #     {"element_id": "slab2", "value": 3600.0, "has_geometry": True}
        #   ],
        #   "count": 2
        # }

        # Extract bounding box for stairs
        result = get_element_geometry_data("model.ifc", stair_ids, "bounding_box")
        # Returns: {
        #   "geometry_type": "bounding_box",
        #   "elements": [
        #     {
        #       "element_id": "stair1",
        #       "value": {
        #         "min_z": 0.0, "max_z": 7200.0, "height": 7200.0,
        #         "min_x": 0.0, "max_x": 3000.0, "width": 3000.0,
        #         "min_y": 0.0, "max_y": 1200.0, "depth": 1200.0
        #       },
        #       "has_geometry": True
        #     }
        #   ],
        #   "count": 1
        # }
    """
    valid_types = ["placement", "elevation", "bounding_box"]
    if geometry_type not in valid_types:
        return {
            "error": f"Invalid geometry_type '{geometry_type}'. Must be one of: {valid_types}",
            "geometry_type": geometry_type,
            "elements": [],
            "count": 0
        }

    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            elements_data = []

            for element_id in element_ids:
                element = get_element_by_id(ifc_file, element_id)

                if not element:
                    elements_data.append({
                        "element_id": element_id,
                        "value": None,
                        "has_geometry": False
                    })
                    continue

                # Extract geometry based on type
                if geometry_type == "placement":
                    placement = get_element_placement(element)
                    elements_data.append({
                        "element_id": element_id,
                        "value": placement,
                        "has_geometry": placement is not None
                    })

                elif geometry_type == "elevation":
                    elevation = get_element_elevation(element)
                    elements_data.append({
                        "element_id": element_id,
                        "value": elevation,
                        "has_geometry": elevation is not None
                    })

                elif geometry_type == "bounding_box":
                    bbox = get_element_bounding_box(element, ifc_file)
                    elements_data.append({
                        "element_id": element_id,
                        "value": bbox,
                        "has_geometry": bbox is not None
                    })

            return {
                "geometry_type": geometry_type,
                "elements": elements_data,
                "count": len(elements_data)
            }

    except Exception as e:
        return {
            "error": f"Failed to extract geometry data: {str(e)}",
            "geometry_type": geometry_type,
            "elements": [],
            "count": 0
        }
