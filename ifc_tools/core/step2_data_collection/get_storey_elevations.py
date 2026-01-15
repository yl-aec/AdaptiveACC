"""
Storey Elevation Queries
Category: data_collection (Step2 - Data Collection)
Description: Extracts elevation data for building storeys.
"""

from typing import Dict, Any, List, Optional
from ifc_tool_utils.ifcopenshell import get_elements_by_type, get_element_by_id
from ifc_tool_utils.ifcopenshell.geometry_queries import get_storey_elevation
from utils.ifc_file_manager import IFCFileManager


def get_storey_elevations(
    ifc_file_path: str,
    storey_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Extract elevation data for building storeys.

    Retrieves the elevation attribute (Z-coordinate of storey's base plane)
    from IfcBuildingStorey elements. Useful for vertical range checks,
    storey height calculations, and floor-level compliance validation.

    Args:
        ifc_file_path: Path to the IFC file
        storey_ids: Optional list of storey GlobalIds.
                   If None, returns elevations for all storeys in the building.

    Returns:
        Dictionary with:
        - storeys: List of dicts, each containing:
            - storey_id: Storey GlobalId
            - storey_name: Storey name (if available)
            - elevation: Z-coordinate of storey base plane (float or None)
            - has_elevation: Boolean indicating if elevation is available
        - count: Total number of storeys processed

        Returns error dict if operation fails.

    Examples:
        # Get elevations for specific storeys
        result = get_storey_elevations("model.ifc", ["storey_L1", "storey_L2"])
        # Returns: {
        #   "storeys": [
        #     {"storey_id": "storey_L1", "storey_name": "Level 1", "elevation": 0.0, "has_elevation": True},
        #     {"storey_id": "storey_L2", "storey_name": "Level 2", "elevation": 3600.0, "has_elevation": True}
        #   ],
        #   "count": 2
        # }

        # Get all storey elevations in building
        result = get_storey_elevations("model.ifc")
        # Returns all storeys with their elevations

        # Use case: Count storeys above grade plane (elevation > 0)
        all_storeys = get_storey_elevations("model.ifc")
        above_grade = [s for s in all_storeys["storeys"]
                      if s["has_elevation"] and s["elevation"] > 0]
        if len(above_grade) >= 4:
            # Building has 4+ storeys above grade
            pass

        # Use case: Calculate storey height
        result = get_storey_elevations("model.ifc", ["storey_L1", "storey_L2"])
        if len(result["storeys"]) == 2:
            s1, s2 = result["storeys"]
            if s1["has_elevation"] and s2["has_elevation"]:
                storey_height = abs(s2["elevation"] - s1["elevation"])

        # Use case: Check if element is within storey elevation range
        storey_data = get_storey_elevations("model.ifc", ["storey_L1"])
        storey_elev = storey_data["storeys"][0]["elevation"]
        # Then use with element elevation checks...
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            # Determine which storeys to process
            if storey_ids:
                # Get specific storeys by ID
                storeys_to_process = []
                for storey_id in storey_ids:
                    storey = get_element_by_id(ifc_file, storey_id)
                    if storey:
                        if storey.is_a('IfcBuildingStorey'):
                            storeys_to_process.append(storey)
                        else:
                            # Element exists but is not a storey - include with error info
                            storeys_to_process.append(None)
                    else:
                        # Element not found - include placeholder
                        storeys_to_process.append(None)
            else:
                # Get all storeys in building
                storeys_to_process = get_elements_by_type(ifc_file, 'IfcBuildingStorey')
                storey_ids = [s.GlobalId for s in storeys_to_process]

            # Extract elevation data
            storey_results = []
            for i, storey in enumerate(storeys_to_process):
                if storey is None:
                    # Storey not found or invalid type
                    storey_results.append({
                        "storey_id": storey_ids[i] if i < len(storey_ids) else "unknown",
                        "storey_name": None,
                        "elevation": None,
                        "has_elevation": False
                    })
                    continue

                # Extract elevation
                elevation = get_storey_elevation(storey)
                storey_results.append({
                    "storey_id": storey.GlobalId,
                    "storey_name": storey.Name if hasattr(storey, 'Name') else None,
                    "elevation": elevation,
                    "has_elevation": elevation is not None
                })

            return {
                "storeys": storey_results,
                "count": len(storey_results)
            }

    except Exception as e:
        return {
            "error": f"Failed to extract storey elevations: {str(e)}",
            "storeys": [],
            "count": 0
        }
