"""
Tool: diagnose_file_access
Category: others
Description: Diagnose IFC file access issues and return basic file information without using restricted modules.
"""

import ifcopenshell
from typing import Dict, Any

def diagnose_file_access(ifc_file_path: str) -> Dict[str, Any]:
    '''Diagnose IFC file access issues and return basic file information.
    
    This tool attempts to open an IFC file using ifcopenshell and returns a status
    dictionary indicating whether the file is accessible. If successful, it provides
    basic file information like schema version and entity count. If unsuccessful,
    it returns an error message without using any restricted modules.
    
    Args:
        ifc_file_path: Path to the IFC file to diagnose.
        
    Returns:
        A dictionary with the following structure:
        {
            'success': bool,  # True if file opened successfully
            'error_message': str | None,  # Error message if unsuccessful
            'schema': str | None,  # IFC schema version (e.g., 'IFC4')
            'entity_count': int | None  # Total number of entities in the file
        }
        
    Example:
        >>> result = diagnose_file_access('model.ifc')
        >>> print(result)
        {'success': True, 'error_message': None, 'schema': 'IFC4', 'entity_count': 1234}
        
        >>> result = diagnose_file_access('nonexistent.ifc')
        >>> print(result)
        {'success': False, 'error_message': 'File not found or cannot be opened', 'schema': None, 'entity_count': None}
    '''
    result = {
        'success': False,
        'error_message': None,
        'schema': None,
        'entity_count': None
    }
    
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        result['error_message'] = 'File not found or cannot be opened'
        return result
    except Exception as e:
        result['error_message'] = f'Error opening file: {str(e)}'
        return result
    
    try:
        result['success'] = True
        result['schema'] = ifc_file.schema
        result['entity_count'] = len(list(ifc_file))
    except Exception as e:
        result['success'] = False
        result['error_message'] = f'Error reading file info: {str(e)}'
        
    return result