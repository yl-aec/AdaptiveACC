"""
Tool: get_site_grade_plane_elevation
Category: step2_data_collection
Description: Retrieves the grade plane elevation from IfcSite.RefElevation or IfcBuilding Pset_BuildingCommon.ElevationOfRefHeight.
"""

import ifcopenshell
from typing import Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property

def get_site_grade_plane_elevation(ifc_file_path: str) -> Optional[float]:
    """Get grade plane elevation from IfcSite or IfcBuilding.

    Attempts to retrieve the grade plane elevation from two sources in order of priority:
    1. IfcSite.RefElevation (direct attribute)
    2. IfcBuilding property 'ElevationOfRefHeight' in 'Pset_BuildingCommon'

    Args:
        ifc_file_path: Path to the IFC file.

    Returns:
        The elevation value as a float if found, otherwise None.
    """
    ifc_file = ifcopenshell.open(ifc_file_path)

    # Priority 1: Check IfcSite.RefElevation
    sites = get_elements_by_type(ifc_file, "IfcSite")
    if sites:
        site = sites[0]
        # RefElevation is an optional attribute (IfcLengthMeasure)
        if hasattr(site, "RefElevation") and site.RefElevation is not None:
            return float(site.RefElevation)

    # Priority 2: Check IfcBuilding Pset_BuildingCommon.ElevationOfRefHeight
    buildings = get_elements_by_type(ifc_file, "IfcBuilding")
    if buildings:
        building = buildings[0]
        prop_data = get_pset_property(building, "Pset_BuildingCommon", "ElevationOfRefHeight")
        
        if prop_data and "value" in prop_data and prop_data["value"] is not None:
            return float(prop_data["value"])

    return None