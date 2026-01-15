"""
Relationship Queries - Atomic functions for IFC relationship operations

These functions provide relationship query operations that return native
ifcopenshell objects for relationship and connection analysis.
"""

import ifcopenshell
from typing import List, Optional, Union, Dict, Any


# Note: get_spatial_container() and get_contained_elements() have been removed
# as they duplicate ifcopenshell.util.element.get_container() and get_contained().
# For sandbox execution, these functions are injected directly.
# For non-sandbox code (like core tools), import ifcopenshell.util.element directly.


def get_filling_elements(host_element: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Get elements that fill openings in the host element (e.g., doors/windows in walls).

    Args:
        host_element: Host element (typically IfcWall)

    Returns:
        List of filling elements (doors, windows, etc.)
    """
    filling_elements = []
    if not host_element or not hasattr(host_element, 'HasOpenings'):
        return filling_elements

    for rel_voids in host_element.HasOpenings:
        if rel_voids.is_a('IfcRelVoidsElement'):
            opening = rel_voids.RelatedOpeningElement
            if hasattr(opening, 'HasFillings'):
                for rel_fills in opening.HasFillings:
                    if rel_fills.is_a('IfcRelFillsElement'):
                        filling_elements.append(rel_fills.RelatedBuildingElement)
    return filling_elements


def get_host_element(filling_element: ifcopenshell.entity_instance) -> Optional[ifcopenshell.entity_instance]:
    """Get the host element that contains this filling element.

    Args:
        filling_element: Filling element (door, window, etc.)

    Returns:
        Host element or None if not found
    """
    if not filling_element or not hasattr(filling_element, 'FillsVoids'):
        return None

    for rel_fills in filling_element.FillsVoids:
        if rel_fills.is_a('IfcRelFillsElement'):
            opening = rel_fills.RelatingOpeningElement
            if hasattr(opening, 'VoidsElements'):
                for rel_voids in opening.VoidsElements:
                    if rel_voids.is_a('IfcRelVoidsElement'):
                        return rel_voids.RelatingBuildingElement
    return None


def get_space_boundaries(ifc_file: ifcopenshell.entity_instance,
                        space: Optional[ifcopenshell.entity_instance] = None,
                        boundary_type: Optional[str] = None) -> List[ifcopenshell.entity_instance]:
    """Get space boundary relationships from IFC file with optional filtering.

    Args:
        ifc_file: IFC file instance
        space: Specific space to get boundaries for (optional, None = all spaces)
        boundary_type: Filter by boundary type: 'INTERNAL' or 'EXTERNAL' (optional, None = both)

    Returns:
        List of IfcRelSpaceBoundary instances matching filters.
        Returns empty list [] if no boundaries found or file has no IfcRelSpaceBoundary.
    """
    boundaries = ifc_file.by_type('IfcRelSpaceBoundary')

    filtered_boundaries = []
    for boundary in boundaries:
        # Filter by space if specified
        if space and boundary.RelatingSpace != space:
            continue

        # Filter by boundary type if specified
        if boundary_type and hasattr(boundary, 'InternalOrExternalBoundary'):
            if str(boundary.InternalOrExternalBoundary) != boundary_type:
                continue

        filtered_boundaries.append(boundary)

    return filtered_boundaries


def get_space_boundary_info(boundary: ifcopenshell.entity_instance) -> Dict[str, Any]:
    """Extract structured information from a space boundary relationship.

    Args:
        boundary: IfcRelSpaceBoundary instance

    Returns:
        Dict with keys: 'boundary_id', 'space_id', 'element_id', 'element_type',
        'physical_virtual', 'internal_external', 'level', 'description'.
        Values are GlobalId strings or property values. Missing attributes are omitted from dict.
    """
    info = {}

    try:
        info['boundary_id'] = boundary.GlobalId if hasattr(boundary, 'GlobalId') else str(boundary)
        info['space_id'] = boundary.RelatingSpace.GlobalId if boundary.RelatingSpace else None
        info['element_id'] = boundary.RelatedBuildingElement.GlobalId if boundary.RelatedBuildingElement else None
        info['element_type'] = boundary.RelatedBuildingElement.is_a() if boundary.RelatedBuildingElement else None

        if hasattr(boundary, 'PhysicalOrVirtualBoundary'):
            info['physical_virtual'] = str(boundary.PhysicalOrVirtualBoundary)

        if hasattr(boundary, 'InternalOrExternalBoundary'):
            info['internal_external'] = str(boundary.InternalOrExternalBoundary)

        if hasattr(boundary, 'Name'):
            info['level'] = boundary.Name

        if hasattr(boundary, 'Description'):
            info['description'] = boundary.Description

    except Exception as e:
        # Return partial info if some attributes are missing
        pass

    return info


def find_adjacent_spaces_via_boundaries(ifc_file: ifcopenshell.entity_instance,
                                       space: ifcopenshell.entity_instance) -> List[ifcopenshell.entity_instance]:
    """Find spaces adjacent to given space by analyzing shared INTERNAL boundary elements.

    This function uses boundary pairing logic with distance validation:
    - Two spaces are adjacent if they share the same building element (wall/slab)
    - For elements shared by exactly 2 spaces: both spaces are adjacent
    - For elements shared by 3+ spaces: use boundary distance check (< 5 meters)
      to determine which pairs are truly adjacent

    This approach handles both simple adjacency (2 spaces sharing a wall) and
    complex cases (multiple spaces along a long corridor wall).

    Args:
        ifc_file: IFC file instance
        space: Space to find adjacencies for

    Returns:
        List of unique adjacent space instances that share building elements with the input space.
        Returns empty list [] if space has no INTERNAL boundaries or no adjacent spaces found.
    """
    # Step 1: Get all INTERNAL boundaries for the target space
    space_boundaries = get_space_boundaries(ifc_file, space, 'INTERNAL')

    if not space_boundaries:
        return []

    # Step 2: Collect all building elements that bound the target space
    target_elements = set()
    for boundary in space_boundaries:
        element = boundary.RelatedBuildingElement
        if element:
            target_elements.add(element)

    if not target_elements:
        return []

    # Step 3: Get all INTERNAL boundaries in the IFC file and group by element
    # This creates a mapping: {building_element: [space1, space2, ...]}
    all_boundaries = get_space_boundaries(ifc_file, boundary_type='INTERNAL')
    element_to_spaces = {}

    for boundary in all_boundaries:
        element = boundary.RelatedBuildingElement
        relating_space = boundary.RelatingSpace

        if element and relating_space:
            if element not in element_to_spaces:
                element_to_spaces[element] = []
            # Avoid duplicates - each space should appear once per element
            if relating_space not in element_to_spaces[element]:
                element_to_spaces[element].append(relating_space)

    # Step 4: Find adjacent spaces using boundary pairing logic with distance validation
    adjacent_spaces = []

    # Helper function to get boundary location from ConnectionGeometry
    def get_boundary_location(boundary):
        """Extract 3D location from boundary's ConnectionGeometry."""
        try:
            if boundary.ConnectionGeometry:
                surface = boundary.ConnectionGeometry.SurfaceOnRelatingElement
                basis = surface.BasisSurface
                position = basis.Position
                if hasattr(position, 'Location') and position.Location:
                    coords = position.Location.Coordinates
                    return (coords[0], coords[1], coords[2] if len(coords) > 2 else 0)
        except:
            pass
        return None

    # Helper function to calculate 3D distance
    def calculate_distance(loc1, loc2):
        """Calculate Euclidean distance between two 3D points."""
        import math
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(loc1, loc2)))

    # Create a mapping of element + space -> boundary for distance checks
    element_space_boundaries = {}
    for boundary in all_boundaries:
        element = boundary.RelatedBuildingElement
        relating_space = boundary.RelatingSpace
        if element and relating_space:
            key = (element, relating_space)
            element_space_boundaries[key] = boundary

    for element in target_elements:
        if element in element_to_spaces:
            spaces_on_element = element_to_spaces[element]

            # Case 1: Element shared by EXACTLY 2 spaces
            # These are definitely adjacent (simple wall between two rooms)
            if len(spaces_on_element) == 2 and space in spaces_on_element:
                other_space = [s for s in spaces_on_element if s != space][0]
                if other_space not in adjacent_spaces:
                    adjacent_spaces.append(other_space)

            # Case 2: Element shared by 3+ spaces
            # Use distance check to determine which are truly adjacent
            # (e.g., multiple rooms along a long corridor wall)
            elif len(spaces_on_element) >= 3 and space in spaces_on_element:
                # Get boundary location for target space
                target_boundary = element_space_boundaries.get((element, space))
                if not target_boundary:
                    continue

                target_location = get_boundary_location(target_boundary)
                if not target_location:
                    continue  # Skip if no location data

                # Check distance to each other space on this element
                DISTANCE_THRESHOLD = 5000.0  # 5 meters in mm

                for other_space in spaces_on_element:
                    if other_space == space:
                        continue

                    # Get boundary location for other space
                    other_boundary = element_space_boundaries.get((element, other_space))
                    if not other_boundary:
                        continue

                    other_location = get_boundary_location(other_boundary)
                    if not other_location:
                        continue

                    # Calculate distance between boundaries
                    distance = calculate_distance(target_location, other_location)

                    # If distance is small enough, consider them adjacent
                    if distance < DISTANCE_THRESHOLD:
                        if other_space not in adjacent_spaces:
                            adjacent_spaces.append(other_space)

    return adjacent_spaces
