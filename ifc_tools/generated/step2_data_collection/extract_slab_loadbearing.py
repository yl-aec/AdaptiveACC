"""
Tool: extract_slab_loadbearing
Category: step2_data_collection
Description: Extract LoadBearing property from Pset_SlabCommon for specified IfcSlab elements, returning detailed metadata including property value, existence status, and error information.
"""

import ifcopenshell
import ifcopenshell.util.element
from typing import List, Dict, Any
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_ids

def extract_slab_loadbearing(ifc_file_path: str, slab_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    '''Extract LoadBearing property from Pset_SlabCommon for specified IfcSlab elements.

    Args:
        ifc_file_path: Path to the IFC file.
        slab_ids: List of GlobalIds for IfcSlab elements to analyze.

    Returns:
        Dictionary mapping each element ID to a result dict containing:
        - 'load_bearing': Boolean value of LoadBearing property (True/False/None)
        - 'property_found': Boolean indicating if property was found
        - 'pset_name': Name of property set where found (or None)
        - 'error_message': Error description if any (or None)

    Example:
        >>> result = extract_slab_loadbearing('model.ifc', ['2XQ$n5bynD5fRNOp3DzC4w', '3YQ$m6czoE6gSOQq4EaD5x'])
        >>> print(result['2XQ$n5bynD5fRNOp3DzC4w']['load_bearing'])
        True
    '''
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    except Exception as e:
        raise ValueError(f"Error opening IFC file: {str(e)}")
    
    # Get slab elements by IDs
    slabs = get_elements_by_ids(ifc_file, slab_ids)
    
    results = {}
    
    for slab in slabs:
        slab_id = slab.GlobalId
        
        # Initialize result structure
        result = {
            'load_bearing': None,
            'property_found': False,
            'pset_name': None,
            'error_message': None
        }
        
        # Get all property sets for the slab (including inherited from type)
        psets = ifcopenshell.util.element.get_psets(slab)
        
        # Look for Pset_SlabCommon
        if 'Pset_SlabCommon' in psets:
            pset_data = psets['Pset_SlabCommon']
            
            # Check if LoadBearing property exists
            if 'LoadBearing' in pset_data:
                load_bearing_value = pset_data['LoadBearing']
                
                # Convert to boolean if possible
                if isinstance(load_bearing_value, bool):
                    result['load_bearing'] = load_bearing_value
                elif isinstance(load_bearing_value, str):
                    # Handle string representations
                    lower_val = load_bearing_value.lower()
                    if lower_val in ['true', 'yes', '1']:
                        result['load_bearing'] = True
                    elif lower_val in ['false', 'no', '0']:
                        result['load_bearing'] = False
                    else:
                        result['error_message'] = f"Invalid LoadBearing value: {load_bearing_value}"
                elif isinstance(load_bearing_value, (int, float)):
                    # Handle numeric representations
                    result['load_bearing'] = bool(load_bearing_value)
                else:
                    result['error_message'] = f"Unsupported LoadBearing type: {type(load_bearing_value)}"
                
                if result['error_message'] is None:
                    result['property_found'] = True
                    result['pset_name'] = 'Pset_SlabCommon'
            else:
                result['error_message'] = "LoadBearing property not found in Pset_SlabCommon"
        else:
            result['error_message'] = "Pset_SlabCommon not found for element"
        
        results[slab_id] = result
    
    # Handle missing elements (IDs not found in model)
    found_ids = {slab.GlobalId for slab in slabs}
    for slab_id in slab_ids:
        if slab_id not in found_ids:
            results[slab_id] = {
                'load_bearing': None,
                'property_found': False,
                'pset_name': None,
                'error_message': f"Element with GlobalId '{slab_id}' not found in model"
            }
    
    return results