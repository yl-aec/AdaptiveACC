"""
Tool: inspect_space_geometry_representation
Category: step2_data_collection
Description: Inspect geometric representation attributes for IfcSpace elements to understand why they lack bounding box geometry data. Examines attributes like Representation, ObjectPlacement, and geometric representation types to determine if geometry exists, is of a different type, or is missing.
"""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.shape
from typing import List, Dict, Any, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def inspect_space_geometry_representation(ifc_file_path: str, space_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Inspect geometric representation attributes for IfcSpace elements.
    
    This tool examines the geometric representation of specified IfcSpace elements to understand
    why they might lack bounding box geometry data. It checks attributes like Representation,
    ObjectPlacement, and geometric representation types to determine if geometry exists,
    is of a different type, or is missing.
    
    Args:
        ifc_file_path: Path to the IFC file.
        space_ids: Optional list of GlobalId strings for specific spaces to inspect.
            If None, inspects all IfcSpace elements in the file.
    
    Returns:
        List of dictionaries, each containing detailed geometric representation information
        for a space. Each dictionary has the following keys:
        - space_id: GlobalId of the space
        - has_object_placement: Boolean indicating if ObjectPlacement exists
        - has_representation: Boolean indicating if Representation exists
        - representation_type: String describing the representation type (e.g., 'IfcProductDefinitionShape', 'None')
        - representation_contexts: List of representation context identifiers (e.g., ['Body', 'Plan'])
        - representation_items: List of representation item types (e.g., ['IfcExtrudedAreaSolid', 'IfcFacetedBrep'])
        - geometry_summary: String summarizing geometry status ('missing', 'present', 'different_type')
    
    Example:
        >>> result = inspect_space_geometry_representation('model.ifc', ['2XQ$n5H1DD8QeB$sCzPkC4'])
        >>> print(result[0]['geometry_summary'])
        'present'
    """
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    
    # Get spaces to inspect
    if space_ids is None:
        # Get all IfcSpace elements
        spaces = ifc_file.by_type('IfcSpace')
    else:
        # Get specific spaces by GlobalId
        spaces = get_elements_by_ids(ifc_file, space_ids)
    
    results = []
    for space in spaces:
        space_info = {
            'space_id': space.GlobalId,
            'has_object_placement': False,
            'has_representation': False,
            'representation_type': None,
            'representation_contexts': [],
            'representation_items': [],
            'geometry_summary': 'missing'
        }
        
        # Check ObjectPlacement
        if hasattr(space, 'ObjectPlacement') and space.ObjectPlacement:
            space_info['has_object_placement'] = True
        
        # Check Representation
        if hasattr(space, 'Representation') and space.Representation:
            space_info['has_representation'] = True
            
            # Get representation type
            rep = space.Representation
            space_info['representation_type'] = rep.is_a()
            
            # If it's a product definition shape, examine its representations
            if rep.is_a('IfcProductDefinitionShape'):
                if hasattr(rep, 'Representations') and rep.Representations:
                    for representation in rep.Representations:
                        # Get representation context identifier
                        if hasattr(representation, 'ContextOfItems'):
                            context = representation.ContextOfItems
                            if hasattr(context, 'ContextIdentifier'):
                                space_info['representation_contexts'].append(context.ContextIdentifier)
                            else:
                                space_info['representation_contexts'].append('unknown')
                        
                        # Get representation items
                        if hasattr(representation, 'Items') and representation.Items:
                            for item in representation.Items:
                                space_info['representation_items'].append(item.is_a())
            
            # Determine geometry summary
            if space_info['representation_items']:
                space_info['geometry_summary'] = 'present'
            else:
                space_info['geometry_summary'] = 'different_type'
        
        results.append(space_info)
    
    return results