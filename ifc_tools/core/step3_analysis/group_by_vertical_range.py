"""
Geometry Analysis Tools
Category: analysis (P3 - Analysis & Calculation)
Description: In-memory analysis of geometric data for elevation filtering and vertical range checks.
             These tools support the P3 "Analysis & Calculation" phase by processing
             geometric data extracted in P2 phase.
"""

from typing import List, Dict, Any, Optional



def group_by_vertical_range(
    elements: List[Dict[str, Any]],
    range_definitions: List[Dict[str, Any]],
    elevation_key: str = "elevation"
) -> Dict[str, Any]:
    """Group elements into vertical ranges (in-memory operation).

    Groups elements based on their elevation into predefined vertical ranges.
    Useful for categorizing elements by storey, zone, or vertical region.
    This is a pure P3 analysis function.

    Args:
        elements: List of dicts containing element data with elevation information.
                 Each dict should have an elevation field.
        range_definitions: List of range specifications. Each dict should contain:
            - "name": Name/label for the range (required)
            - "min_elevation": Minimum elevation (inclusive, optional)
            - "max_elevation": Maximum elevation (inclusive, optional)
            If both min/max are None, the range captures all elements.
        elevation_key: Name of the key containing elevation value in each dict.
                      Default is "elevation".

    Returns:
        Dictionary with:
        - ranges: List of dicts, each containing:
            - name: Range name
            - min_elevation: Minimum elevation for this range
            - max_elevation: Maximum elevation for this range
            - elements: List of elements in this range
            - count: Number of elements in this range
        - unassigned_elements: Elements that didn't fit any range
        - unassigned_count: Number of unassigned elements
        - total_elements: Total number of elements processed

    Examples:
        # Use case: Group elements by storey elevation ranges
        elements = [
            {"element_id": "door1", "elevation": 500.0},
            {"element_id": "door2", "elevation": 3800.0},
            {"element_id": "door3", "elevation": 7400.0},
            {"element_id": "door4", "elevation": 11000.0}
        ]

        ranges = [
            {"name": "Level 0", "min_elevation": 0.0, "max_elevation": 3600.0},
            {"name": "Level 1", "min_elevation": 3600.0, "max_elevation": 7200.0},
            {"name": "Level 2", "min_elevation": 7200.0, "max_elevation": 10800.0}
        ]

        result = group_by_vertical_range(elements, ranges)
        # Returns: {
        #   "ranges": [
        #     {
        #       "name": "Level 0",
        #       "min_elevation": 0.0,
        #       "max_elevation": 3600.0,
        #       "elements": [{"element_id": "door1", "elevation": 500.0}],
        #       "count": 1
        #     },
        #     {
        #       "name": "Level 1",
        #       "min_elevation": 3600.0,
        #       "max_elevation": 7200.0,
        #       "elements": [{"element_id": "door2", "elevation": 3800.0}],
        #       "count": 1
        #     },
        #     {
        #       "name": "Level 2",
        #       "min_elevation": 7200.0,
        #       "max_elevation": 10800.0,
        #       "elements": [],
        #       "count": 0
        #     }
        #   ],
        #   "unassigned_elements": [{"element_id": "door4", "elevation": 11000.0}],
        #   "unassigned_count": 1,
        #   "total_elements": 4
        # }

        # Use case: Group stairs by vertical zones
        stair_extents = [
            {"stair_id": "s1", "min_z": 0.0, "max_z": 3600.0},
            {"stair_id": "s2", "min_z": 3600.0, "max_z": 7200.0}
        ]

        zones = [
            {"name": "Ground Floor Zone", "min_elevation": 0.0, "max_elevation": 3600.0},
            {"name": "First Floor Zone", "min_elevation": 3600.0, "max_elevation": 7200.0}
        ]

        # Group by bottom elevation
        result = group_by_vertical_range(stair_extents, zones, elevation_key="min_z")

        # Workflow example:
        # Step 1 (P2): Get storey elevations
        storey_data = get_storey_elevations(ifc_file)
        storeys = storey_data["storeys"]  # [{"storey_id": ..., "elevation": ...}]

        # Step 2 (P2): Get element elevations
        elem_data = get_element_geometry_data(ifc_file, element_ids, "elevation")
        elements = elem_data["elements"]

        # Step 3 (P3): Create ranges from storey elevations
        ranges = []
        for i in range(len(storeys) - 1):
            ranges.append({
                "name": storeys[i]["storey_name"],
                "min_elevation": storeys[i]["elevation"],
                "max_elevation": storeys[i+1]["elevation"]
            })

        # Step 4 (P3): Group elements by storey ranges
        grouped = group_by_vertical_range(elements, ranges, elevation_key="value")
    """
    # Validate range definitions
    for range_def in range_definitions:
        if "name" not in range_def:
            raise ValueError("Each range definition must have a 'name' key")

    # Initialize result structure
    range_results = []
    for range_def in range_definitions:
        range_results.append({
            "name": range_def["name"],
            "min_elevation": range_def.get("min_elevation"),
            "max_elevation": range_def.get("max_elevation"),
            "elements": [],
            "count": 0
        })

    unassigned_elements = []
    assigned_element_ids = set()

    # Process each element
    for element in elements:
        elevation = element.get(elevation_key)

        # Skip elements without elevation
        if elevation is None:
            unassigned_elements.append(element)
            continue

        # Try to assign to a range
        assigned = False
        for i, range_def in enumerate(range_definitions):
            min_elev = range_def.get("min_elevation")
            max_elev = range_def.get("max_elevation")

            # Check if element fits in this range
            in_range = True

            if min_elev is not None and elevation < min_elev:
                in_range = False

            if max_elev is not None and elevation > max_elev:
                in_range = False

            if in_range:
                range_results[i]["elements"].append(element)
                range_results[i]["count"] += 1
                assigned = True
                # Get element ID for tracking (to avoid double counting)
                element_id = element.get("element_id") or element.get("storey_id") or id(element)
                assigned_element_ids.add(element_id)
                break  # Assign to first matching range only

        if not assigned:
            unassigned_elements.append(element)

    return {
        "ranges": range_results,
        "unassigned_elements": unassigned_elements,
        "unassigned_count": len(unassigned_elements),
        "total_elements": len(elements)
    }
