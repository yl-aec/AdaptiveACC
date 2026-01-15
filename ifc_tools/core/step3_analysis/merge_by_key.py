"""
Tool: Data Merging Operations
Category: aggregation
Description: Functions for merging and combining data from multiple sources
"""

from typing import List, Dict, Any


def merge_by_key(
    data1: List[Dict[str, Any]],
    data2: List[Dict[str, Any]],
    key_field: str,
    merge_strategy: str = "left"
) -> List[Dict[str, Any]]:
    """Merge two datasets based on a common key field.


    Args:
        data1: First dataset (list of dictionaries)
        data2: Second dataset (list of dictionaries)
        key_field: Field name to use as merge key
        merge_strategy: "left", "right", "inner", or "outer"

    Returns:
        Merged dataset

    Example:
        doors = [{"element_id": "D1", "width": 900}, {"element_id": "D2", "width": 800}]
        fire_ratings = [{"element_id": "D1", "fire_rating": "FD30"}]
        merged = merge_by_key(doors, fire_ratings, "element_id", "left")
        # Returns: [
        #     {"element_id": "D1", "width": 900, "fire_rating": "FD30"},
        #     {"element_id": "D2", "width": 800}
        # ]
    """
    # Create lookup dictionary for data2
    lookup = {item[key_field]: item for item in data2 if key_field in item}

    result = []

    if merge_strategy in ["left", "outer"]:
        for item1 in data1:
            merged_item = item1.copy()
            key = item1.get(key_field)
            if key and key in lookup:
                # Merge data2 fields into item1
                for k, v in lookup[key].items():
                    if k != key_field:  # Don't duplicate the key field
                        merged_item[k] = v
            result.append(merged_item)

    if merge_strategy in ["right", "outer"]:
        # Add items from data2 that weren't in data1
        keys_in_data1 = {item.get(key_field) for item in data1}
        for item2 in data2:
            key = item2.get(key_field)
            if key and key not in keys_in_data1:
                result.append(item2.copy())

    if merge_strategy == "inner":
        for item1 in data1:
            key = item1.get(key_field)
            if key and key in lookup:
                merged_item = item1.copy()
                for k, v in lookup[key].items():
                    if k != key_field:
                        merged_item[k] = v
                result.append(merged_item)

    return result

