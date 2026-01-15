"""
Tool: extract_project_length_unit
Category: step2_data_collection
Description: Extract the length unit of measurement from an IFC model by checking IfcProject or IfcUnitAssignment. Returns detailed unit information including name, type, conversion factor, and whether it's SI or conversion-based.
"""

import ifcopenshell
import ifcopenshell.util.unit
from typing import Dict, Any, Optional

def extract_project_length_unit(ifc_file_path: str) -> Dict[str, Any]:
    '''Extract the length unit of measurement from an IFC model.
    
    This tool checks the IfcProject or IfcUnitAssignment for length units
    (e.g., millimeters, inches) and returns detailed unit information.
    Useful for determining the units used for riser height values and other
    length-based measurements.
    
    Args:
        ifc_file_path: Path to the IFC file.
        
    Returns:
        A dictionary containing:
            - 'unit_name': The name of the length unit (e.g., 'MILLIMETRE', 'INCH')
            - 'unit_type': The IFC unit type (e.g., 'LENGTHUNIT')
            - 'prefix': SI prefix if applicable (e.g., 'MILLI', None)
            - 'conversion_factor': Factor to convert to SI meters (float)
            - 'is_si': Boolean indicating if it's an SI unit
            - 'is_conversion_based': Boolean indicating if it's a conversion-based unit
            
        Returns an empty dict {} if no length unit is found.
        
    Example:
        >>> result = extract_project_length_unit('model.ifc')
        >>> print(result)
        {
            'unit_name': 'MILLIMETRE',
            'unit_type': 'LENGTHUNIT',
            'prefix': 'MILLI',
            'conversion_factor': 0.001,
            'is_si': True,
            'is_conversion_based': False
        }
    '''
    # Open the IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    except Exception as e:
        raise ValueError(f"Error opening IFC file: {str(e)}")
    
    # Get the IfcProject (should be exactly one)
    projects = ifc_file.by_type('IfcProject')
    if not projects:
        return {}
    
    project = projects[0]
    
    # Get the unit assignment from the project
    if not hasattr(project, 'UnitsInContext') or not project.UnitsInContext:
        return {}
    
    unit_assignment = project.UnitsInContext
    
    # Find length units in the unit assignment
    length_units = []
    for unit in unit_assignment.Units:
        # Check if it's a length unit
        if unit.is_a('IfcSIUnit') and unit.UnitType == 'LENGTHUNIT':
            length_units.append({
                'unit': unit,
                'is_si': True,
                'is_conversion_based': False
            })
        elif unit.is_a('IfcConversionBasedUnit') and unit.UnitType == 'LENGTHUNIT':
            length_units.append({
                'unit': unit,
                'is_si': False,
                'is_conversion_based': True
            })
        elif unit.is_a('IfcConversionBasedUnitWithOffset') and unit.UnitType == 'LENGTHUNIT':
            length_units.append({
                'unit': unit,
                'is_si': False,
                'is_conversion_based': True
            })
    
    # If no length units found, return empty
    if not length_units:
        return {}
    
    # Take the first length unit (typically there's only one)
    unit_info = length_units[0]
    unit = unit_info['unit']
    
    # Extract unit details
    result = {
        'is_si': unit_info['is_si'],
        'is_conversion_based': unit_info['is_conversion_based']
    }
    
    if unit_info['is_si']:
        # SI unit
        result['unit_name'] = unit.Name if hasattr(unit, 'Name') else 'LENGTHUNIT'
        result['unit_type'] = unit.UnitType
        result['prefix'] = unit.Prefix if hasattr(unit, 'Prefix') else None
        
        # Calculate conversion factor to SI meters
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(ifc_file)
        result['conversion_factor'] = unit_scale
        
    else:
        # Conversion-based unit
        result['unit_name'] = unit.Name if hasattr(unit, 'Name') else 'LENGTHUNIT'
        result['unit_type'] = unit.UnitType
        result['prefix'] = None  # Conversion-based units don't have SI prefixes
        
        # Get conversion factor
        conversion_factor = 1.0
        if hasattr(unit, 'ConversionFactor') and hasattr(unit.ConversionFactor, 'ValueComponent'):
            conversion_factor = unit.ConversionFactor.ValueComponent.wrappedValue
        
        # Handle offset if present
        if unit.is_a('IfcConversionBasedUnitWithOffset') and hasattr(unit, 'ConversionOffset'):
            # Note: For length units, offset is rarely used
            conversion_offset = unit.ConversionOffset.wrappedValue
            # The actual conversion would be: value * conversion_factor + conversion_offset
            # But for most practical purposes, we just note the factor
            result['conversion_offset'] = conversion_offset
        
        result['conversion_factor'] = conversion_factor
    
    return result