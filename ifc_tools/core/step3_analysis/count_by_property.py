"""
Counting and Aggregation Tools
Category: analysis (P3 - Analysis & Calculation)
Description: Tools for counting elements and performing aggregations.
             Supports simple counting and grouped counting by property values.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict


def count_by_property(
    data: List[Dict[str, Any]],
    group_by: Optional[str] = None
) -> Dict[str, Any]:
    """Count elements, optionally grouped by a property value.

    This function counts the number of elements in the data list. If group_by is
    specified, it groups elements by the unique values of that property and returns
    counts for each group.

    Use this tool for regulations that require counting elements (e.g., "each room
    must have at least 2 exits", "each floor must have at least 1 circulation space").

    Args:
        data: List of dictionaries representing element data
        group_by: Optional property name to group by.
                 If None, returns total count only.
                 If specified, returns count for each unique property value.

    Returns:
        Dictionary with:
        - total_count: Total number of elements
        - grouped_counts: Dict mapping property values to counts
                         (only if group_by specified, otherwise None)
        - group_by: Name of the grouping property (None if not grouped)

    Example:
        # Simple count: Total number of doors
        doors = [
            {"element_id": "d1", "space": "Room1"},
            {"element_id": "d2", "space": "Room1"},
            {"element_id": "d3", "space": "Room2"}
        ]
        result = count_by_property(doors)
        # Returns: {"total_count": 3, "grouped_counts": None, "group_by": None}

        # Grouped count: Count doors per space
        result = count_by_property(doors, group_by="space")
        # Returns: {
        #   "total_count": 3,
        #   "grouped_counts": {"Room1": 2, "Room2": 1},
        #   "group_by": "space"
        # }

        # Use case: Check each room has at least 2 exits
        doors_data = extract_property_from_elements(...)["elements"]
        # doors_data = [{"element_id": "d1", "value": "Room1"}, ...]
        # Reshape to match count_by_property input
        doors_with_space = [{"element_id": d["element_id"], "space": d["value"]}
                           for d in doors_data]
        counts = count_by_property(doors_with_space, group_by="space")
        for room, count in counts["grouped_counts"].items():
            if count < 2:
                # Room has insufficient exits

        # Use case: Count circulation spaces per floor
        spaces_by_storey = get_elements_by_storey(...)["storeys"]
        # Flatten to list with storey info
        all_spaces = []
        for storey in spaces_by_storey:
            for space_id in storey["element_ids"]:
                all_spaces.append({
                    "element_id": space_id,
                    "storey": storey["storey_name"]
                })
        result = count_by_property(all_spaces, group_by="storey")
        # Returns counts per floor
    """
    total_count = len(data)

    if group_by is None:
        # Simple count
        return {
            "total_count": total_count,
            "grouped_counts": None,
            "group_by": None
        }

    # Grouped count
    grouped_counts = defaultdict(int)

    for item in data:
        key = item.get(group_by)
        if key is not None:
            # Convert to string for consistent grouping
            key_str = str(key)
            grouped_counts[key_str] += 1

    return {
        "total_count": total_count,
        "grouped_counts": dict(grouped_counts),
        "group_by": group_by
    }
