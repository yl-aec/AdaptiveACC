"""
Tool: calculate_door_effective_threshold_height
Category: step3_analysis
Description: Calculates the effective threshold height for doors by subtracting 'Fußbodenaufbau' from 'Schwelle_Brüstung' and converting the result to millimeters.
"""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.unit
from typing import Dict, Any, List, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type, get_elements_by_ids

def calculate_door_effective_threshold_height(ifc_file_path: str, door_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Calculate effective threshold height in millimeters for doors.

    The calculation is: (Schwelle/Brüstung - Fußbodenaufbau).
    The result is converted to millimeters based on the project's unit settings.

    Args:
        ifc_file_path: Path to the IFC file.
        door_ids: Optional list of door GlobalIds to process. If None, processes all doors.

    Returns:
        Dictionary keyed by door GlobalId containing the calculation result and details.
        Example:
        {
            "3a1...2": {
                "effective_threshold_mm": 20.0,
                "schwelle_bruestung": 0.15,
                "fussbodenaufbau": 0.13,
                "unit": "m",
                "error": None
            }
        }
    """
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Determine unit scale to convert values to millimeters
    # calculate_unit_scale returns the factor to convert to meters (e.g., 1.0 for m, 0.001 for mm)
    unit_scale = ifcopenshell.util.unit.calculate_unit_scale(ifc_file)
    to_mm_factor = unit_scale * 1000.0

    # Get target doors
    if door_ids:
        doors = get_elements_by_ids(ifc_file, door_ids)
    else:
        doors = get_elements_by_type(ifc_file, "IfcDoor")

    results = {}

    for door in doors:
        global_id = door.GlobalId
        psets = ifcopenshell.util.element.get_psets(door)
        
        sb_val = None
        fb_val = None

        # Search for properties in any property set
        for pset_name, props in psets.items():
            if "Schwelle/Brüstung" in props:
                sb_val = props["Schwelle/Brüstung"]
            if "Fußbodenaufbau" in props:
                fb_val = props["Fußbodenaufbau"]
        
        # Prepare result entry
        entry = {
            "effective_threshold_mm": None,
            "schwelle_bruestung": sb_val,
            "fussbodenaufbau": fb_val,
            "unit_scale_used": unit_scale,
            "error": None
        }

        if sb_val is not None and fb_val is not None:
            try:
                val1 = float(sb_val)
                val2 = float(fb_val)
                
                # Calculate difference in file units
                diff = val1 - val2
                
                # Convert to millimeters
                effective_mm = diff * to_mm_factor
                
                entry["effective_threshold_mm"] = round(effective_mm, 2)
            except (ValueError, TypeError) as e:
                entry["error"] = f"Value conversion error: {str(e)}"
        else:
            missing = []
            if sb_val is None: missing.append("Schwelle/Brüstung")
            if fb_val is None: missing.append("Fußbodenaufbau")
            entry["error"] = f"Missing properties: {', '.join(missing)}"

        results[global_id] = entry

    return results