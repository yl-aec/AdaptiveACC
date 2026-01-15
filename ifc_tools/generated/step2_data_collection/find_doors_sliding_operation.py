"""
Tool: find_doors_sliding_operation
Category: step2_data_collection
Description: Identifies sliding doors by checking the OperationType attribute on the door instance or its type definition.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any

def find_doors_sliding_operation(ifc_file_path: str) -> List[Dict[str, Any]]:
    """Find all IfcDoor elements where the OperationType indicates a sliding door.

    The tool checks the 'OperationType' attribute on the IfcDoor instance. 
    If it is not defined or is 'USERDEFINED', it checks the associated IfcDoorType.
    It selects doors where the operation type string contains 'SLIDING' (case-insensitive).

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        List of dictionaries containing 'GlobalId', 'Name', and 'OperationType' for each matching door.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    doors = ifc_file.by_type("IfcDoor")
    
    sliding_doors = []
    
    for door in doors:
        # 1. Check instance attribute (IFC4+)
        # getattr is used because IFC2x3 IfcDoor does not have OperationType
        op_type = getattr(door, "OperationType", None)
        
        # 2. Determine if we need to fallback to the Type object
        # Fallback if op_type is None (not present) or explicitly "USERDEFINED"
        use_type_fallback = False
        if op_type is None:
            use_type_fallback = True
        elif str(op_type).upper() == "USERDEFINED":
            use_type_fallback = True
            
        if use_type_fallback:
            type_element = ifcopenshell.util.element.get_type(door)
            if type_element:
                type_op = getattr(type_element, "OperationType", None)
                if type_op:
                    op_type = type_op
        
        # 3. Check if 'SLIDING' is in the operation type string
        if op_type and "SLIDING" in str(op_type).upper():
            sliding_doors.append({
                "GlobalId": door.GlobalId,
                "Name": door.Name,
                "OperationType": str(op_type)
            })
            
    return sliding_doors