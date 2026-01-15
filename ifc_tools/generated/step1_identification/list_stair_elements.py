"""
Tool: list_stair_elements
Category: step1_identification
Description: Extract all stair-related elements (IfcStair, IfcStairFlight, etc.) with their GlobalIds and basic type information to understand stair modeling in IFC files.
"""

import ifcopenshell
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type

def list_stair_elements(ifc_file_path: str) -> List[Dict[str, Any]]:
    '''List all stair-related elements with their GlobalIds and type information.
    
    This tool extracts all elements of types IfcStair, IfcStairFlight, and related
    components to understand how stairs are modeled in the IFC file.
    
    Args:
        ifc_file_path: Path to the IFC file.
        
    Returns:
        List of dictionaries, each containing:
        - element_id: GlobalId of the element
        - element_type: IFC class name (e.g., 'IfcStair', 'IfcStairFlight')
        - predefined_type: PredefinedType attribute if available
        - name: Name attribute if available
        
    Example:
        >>> elements = list_stair_elements('model.ifc')
        >>> for elem in elements:
        ...     print(f"ID: {elem['element_id']}, Type: {elem['element_type']}")
    '''
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    
    # Define stair-related element types to search for
    stair_types = [
        'IfcStair',
        'IfcStairFlight',
        'IfcRailing',
        'IfcSlab',  # Sometimes used for stair landings
        'IfcMember'  # Sometimes used for stair components
    ]
    
    results = []
    
    # Get elements for each stair-related type
    for element_type in stair_types:
        elements = get_elements_by_type(ifc_file, element_type)
        
        for element in elements:
            # Extract basic information
            element_info = {
                'element_id': element.GlobalId,
                'element_type': element_type,
                'predefined_type': None,
                'name': None
            }
            
            # Get PredefinedType if available
            if hasattr(element, 'PredefinedType'):
                element_info['predefined_type'] = element.PredefinedType
            
            # Get Name if available
            if hasattr(element, 'Name'):
                element_info['name'] = element.Name
            
            results.append(element_info)
    
    return results