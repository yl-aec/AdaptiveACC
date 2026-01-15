"""
Tool: get_door_operation_type
Category: step2_data_collection
Description: Retrieves the 'OperationType' attribute from the IfcDoorType associated with specific IfcDoor elements.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def get_door_operation_type(ifc_file_path: str, door_ids: List[str]) -> Dict[str, Optional[str]]:
    """Retrieves the OperationType from the associated IfcDoorType for a list of doors.

    Args:
        ifc_file_path: Path to the IFC file.
        door_ids: List of GlobalIds of IfcDoor elements.

    Returns:
        Dictionary mapping door GlobalId to its OperationType (e.g., 'SINGLE_SWING_LEFT').
        Values are None if the door is not found, is not an IfcDoor, has no assigned type, 
        or the type lacks the OperationType attribute.
    """
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except (FileNotFoundError, OSError):
        raise ValueError(f"IFC file not found or invalid: {ifc_file_path}")

    # Retrieve all requested elements efficiently
    elements = get_elements_by_ids(ifc_file, door_ids)
    element_map = {el.GlobalId: el for el in elements}

    results = {}

    for door_id in door_ids:
        door = element_map.get(door_id)

        # Validate element existence and class
        if door is None or not door.is_a("IfcDoor"):
            results[door_id] = None
            continue

        # Retrieve the associated type object
        # ifcopenshell.util.element.get_type returns the relating type entity or None
        door_type = ifcopenshell.util.element.get_type(door)

        if door_type is None:
            results[door_id] = None
            continue

        # Extract the OperationType attribute
        # OperationType is a direct attribute of IfcDoorType
        operation_type = getattr(door_type, "OperationType", None)
        
        # Return the value if it exists, otherwise None
        results[door_id] = str(operation_type) if operation_type else None

    return results