"""
Tool: find_spaces_by_circulation_keywords
Category: step1_identification
Description: Identify circulation spaces by checking Name, LongName, ObjectType, and Pset_SpaceCommon.Category against a list of keywords (e.g., Circulation, Lobby, Stair, Elevator, Corridor, Hall). Return a list of GlobalIds for matching spaces.
"""

import ifcopenshell
from typing import List, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type
from ifc_tool_utils.ifcopenshell.property_queries import get_pset_property

def find_spaces_by_circulation_keywords(ifc_file_path: str, keywords: Optional[List[str]] = None) -> List[str]:
    """Identify circulation spaces by checking Name, LongName, ObjectType, and Pset_SpaceCommon.Category.

    Args:
        ifc_file_path: Path to the IFC file.
        keywords: Optional list of keywords to match against. 
                  Defaults to ["Circulation", "Lobby", "Stair", "Elevator", "Corridor", "Hall"].
                  Matching is case-insensitive partial match.

    Returns:
        List of GlobalIds of spaces that match the criteria.
    """
    # Default keywords if none provided
    if keywords is None:
        keywords = ["Circulation", "Lobby", "Stair", "Elevator", "Corridor", "Hall"]
    
    # Normalize keywords for case-insensitive matching
    search_terms = [k.lower() for k in keywords]

    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Get all spaces
    spaces = get_elements_by_type(ifc_file, "IfcSpace")
    
    matching_ids = []

    for space in spaces:
        # Collect candidate strings from attributes and properties
        candidates = []
        
        # 1. Name (IfcRoot)
        if space.Name:
            candidates.append(space.Name)
            
        # 2. LongName (IfcSpace) - Optional attribute
        if hasattr(space, "LongName") and space.LongName:
            candidates.append(space.LongName)
            
        # 3. ObjectType (IfcObject) - Optional attribute
        if hasattr(space, "ObjectType") and space.ObjectType:
            candidates.append(space.ObjectType)
            
        # 4. Pset_SpaceCommon.Category
        # get_pset_property returns Dict{'value': ..., 'unit': ...} or None
        category_data = get_pset_property(space, "Pset_SpaceCommon", "Category")
        if category_data and category_data.get("value"):
            candidates.append(str(category_data["value"]))
            
        # Check if any candidate string contains any keyword
        match_found = False
        for candidate in candidates:
            candidate_lower = candidate.lower()
            for term in search_terms:
                if term in candidate_lower:
                    match_found = True
                    break
            if match_found:
                break
        
        if match_found:
            matching_ids.append(space.GlobalId)
            
    return matching_ids