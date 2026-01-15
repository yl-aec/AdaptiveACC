"""
Tool: Data Grouping Operations
Category: aggregation
Description: Functions for grouping and organizing data by different criteria
"""

from typing import List, Dict, Any
from collections import defaultdict


def group_by_property(data: List[Dict[str, Any]], property_name: str) -> Dict[Any, List[Dict[str, Any]]]:
    """Group elements by a specific property value.

    Args:
        data: List of dictionaries containing element data
        property_name: Name of the property to group by

    Returns:
        Dictionary mapping property values to lists of elements

    Example:
        doors = [
            {"element_id": "D1", "floor": "Level 1", "width": 900},
            {"element_id": "D2", "floor": "Level 2", "width": 800},
            {"element_id": "D3", "floor": "Level 1", "width": 900}
        ]
        grouped = group_by_property(doors, "floor")
        # Returns: {
        #     "Level 1": [{"element_id": "D1", ...}, {"element_id": "D3", ...}],
        #     "Level 2": [{"element_id": "D2", ...}]
        # }
    """
    grouped = defaultdict(list)
    for item in data:
        key = item.get(property_name)
        if key is not None:
            grouped[key].append(item)
    return dict(grouped)

