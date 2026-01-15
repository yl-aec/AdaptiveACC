"""
Tool: extract_slab_spatial_containment
Category: step2_data_collection
Description: Extract spatial containment data for IfcSlab elements, retrieving their containing spatial elements (e.g., IfcBuildingStorey, IfcSpace) with GlobalId, type, and name.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import Dict, List, Any, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def extract_slab_spatial_containment(ifc_file_path: str, slab_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    '''Extract spatial containment data for IfcSlab elements.
    
    For each slab ID, retrieves the containing spatial element (e.g., IfcBuildingStorey, IfcSpace)
    via the RelContainedInSpatialStructure relationship, including the spatial element's
    GlobalId, type, and name.
    
    Args:
        ifc_file_path: Path to the IFC file.
        slab_ids: List of GlobalIds for IfcSlab elements to analyze.
    
    Returns:
        Dictionary mapping slab GlobalIds to their spatial containment details.
        Each value is a dict with keys:
            - spatial_element_id: GlobalId of the containing spatial element (str)
            - spatial_element_type: IFC class name of the spatial element (str)
            - spatial_element_name: Name of the spatial element (str or None)
        If a slab has no spatial container, the value is None.
    
    Example:
        >>> result = extract_slab_spatial_containment('model.ifc', ['1a2b3c', '4d5e6f'])
        >>> print(result)
        {
            '1a2b3c': {
                'spatial_element_id': 'storey_001',
                'spatial_element_type': 'IfcBuildingStorey',
                'spatial_element_name': 'Level 01'
            },
            '4d5e6f': None
        }
    '''
    # Load IFC file
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Get slab elements by their IDs
    slabs = get_elements_by_ids(ifc_file, slab_ids)
    
    # Create mapping from GlobalId to element for quick lookup
    slab_dict = {slab.GlobalId: slab for slab in slabs if slab is not None}
    
    # Initialize result dictionary
    result = {}
    
    # Process each requested slab ID
    for slab_id in slab_ids:
        slab = slab_dict.get(slab_id)
        
        if slab is None:
            # Slab not found in the model
            result[slab_id] = None
            continue
        
        # Get spatial container using ifcopenshell.util.element
        container = ifcopenshell.util.element.get_container(slab)
        
        if container is None:
            # No spatial container found
            result[slab_id] = None
            continue
        
        # Extract container details
        container_details = {
            'spatial_element_id': container.GlobalId,
            'spatial_element_type': container.is_a(),
            'spatial_element_name': container.Name
        }
        
        result[slab_id] = container_details
    
    return result