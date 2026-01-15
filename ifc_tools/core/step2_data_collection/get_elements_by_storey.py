"""
Storey Element Queries
Category: data_collection (Step2 - Data Collection)
Description: Queries elements contained in building storeys.
"""

from typing import Dict, Any, Optional
import ifcopenshell.util.element
from ifc_tool_utils.ifcopenshell import get_elements_by_type, get_element_by_id
from utils.ifc_file_manager import IFCFileManager


def get_elements_by_storey(
    ifc_file_path: str,
    storey_id: Optional[str] = None,
    element_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get elements contained in a specific building storey.

    This function retrieves all elements spatially contained in a building storey
    (IfcBuildingStorey). This is useful for storey-level compliance checking,
    such as verifying that each floor has required spaces or facilities.

    Args:
        ifc_file_path: Path to the IFC file
        storey_id: Optional GlobalId of the specific storey.
                  If None, returns data for all storeys in the building.
        element_type: Optional IFC type to filter results
                     (e.g., "IfcSpace", "IfcDoor").
                     If None, returns all element types.

    Returns:
        Dictionary with:
        - storey_id: GlobalId of the storey (None if querying all storeys)
        - storey_name: Name of the storey (None if querying all storeys)
        - element_type: Requested element type filter (None if all types)
        - element_ids: List of element GlobalIds
        - count: Number of elements found

        If querying all storeys (storey_id=None), returns:
        - storeys: List of dicts, each containing storey info and its elements

        Returns error dict if operation fails.

    Example:
        # Get all spaces in a specific storey
        result = get_elements_by_storey(
            "model.ifc",
            storey_id="storey_L1",
            element_type="IfcSpace"
        )
        # Returns: {
        #   "storey_id": "storey_L1",
        #   "storey_name": "Level 1",
        #   "element_type": "IfcSpace",
        #   "element_ids": ["space1", "space2", "space3"],
        #   "count": 3
        # }

        # Get all doors in a specific storey
        result = get_elements_by_storey(
            "model.ifc",
            storey_id="storey_L2",
            element_type="IfcDoor"
        )

        # Get all storeys and their spaces
        result = get_elements_by_storey(
            "model.ifc",
            element_type="IfcSpace"
        )
        # Returns: {
        #   "storey_id": None,
        #   "storey_name": None,
        #   "element_type": "IfcSpace",
        #   "storeys": [
        #     {"storey_id": "L1", "storey_name": "Level 1", "element_ids": ["s1", "s2"], "count": 2},
        #     {"storey_id": "L2", "storey_name": "Level 2", "element_ids": ["s3", "s4"], "count": 2}
        #   ]
        # }

        # Use case: Check each floor has circulation space
        storeys_result = get_elements_by_storey("model.ifc", element_type="IfcSpace")
        for storey in storeys_result["storeys"]:
            space_ids = storey["element_ids"]
            # Check if any space is circulation type...
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            if storey_id:
                # Query single storey
                storey = get_element_by_id(ifc_file, storey_id)
                if not storey:
                    return {
                        "storey_id": storey_id,
                        "error": "Storey not found"
                    }

                if not storey.is_a('IfcBuildingStorey'):
                    return {
                        "storey_id": storey_id,
                        "error": f"Element is {storey.is_a()}, not IfcBuildingStorey"
                    }

                # Get elements related to this storey
                # Use both get_contained (for IfcRelContainedInSpatialStructure)
                # and get_decomposition (for IfcRelAggregates, used by IfcSpace)
                contained = list(ifcopenshell.util.element.get_contained(storey))
                decomposed = list(ifcopenshell.util.element.get_decomposition(storey))

                # Combine and deduplicate by GlobalId
                seen = set()
                all_elements = []
                for elem in contained + decomposed:
                    if elem.GlobalId not in seen:
                        seen.add(elem.GlobalId)
                        all_elements.append(elem)

                # Filter by element type if specified
                if element_type:
                    all_elements = [e for e in all_elements if e.is_a(element_type)]

                element_ids = [e.GlobalId for e in all_elements]

                return {
                    "storey_id": storey_id,
                    "storey_name": storey.Name or "",
                    "element_type": element_type,
                    "element_ids": element_ids,
                    "count": len(element_ids)
                }

            else:
                # Query all storeys
                all_storeys = get_elements_by_type(ifc_file, 'IfcBuildingStorey')
                storey_results = []

                for storey in all_storeys:
                    # Get elements related to this storey
                    # Use both get_contained (for IfcRelContainedInSpatialStructure)
                    # and get_decomposition (for IfcRelAggregates, used by IfcSpace)
                    contained = list(ifcopenshell.util.element.get_contained(storey))
                    decomposed = list(ifcopenshell.util.element.get_decomposition(storey))

                    # Combine and deduplicate by GlobalId
                    seen = set()
                    all_elements = []
                    for elem in contained + decomposed:
                        if elem.GlobalId not in seen:
                            seen.add(elem.GlobalId)
                            all_elements.append(elem)

                    # Filter by element type if specified
                    if element_type:
                        all_elements = [e for e in all_elements if e.is_a(element_type)]

                    element_ids = [e.GlobalId for e in all_elements]

                    storey_results.append({
                        "storey_id": storey.GlobalId,
                        "storey_name": storey.Name or "",
                        "element_ids": element_ids,
                        "count": len(element_ids)
                    })

                return {
                    "storey_id": None,
                    "storey_name": None,
                    "element_type": element_type,
                    "storeys": storey_results
                }

    except Exception as e:
        return {
            "storey_id": storey_id,
            "element_type": element_type,
            "error": f"Failed to query storey elements: {str(e)}"
        }
