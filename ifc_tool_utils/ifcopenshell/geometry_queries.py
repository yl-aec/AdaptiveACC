"""
Geometry Queries - Functions for IFC element geometric operations

These functions provide basic geometric query operations for extracting
placement, coordinates, elevations, and bounding boxes from IFC elements.
"""

import ifcopenshell
from typing import Dict, Any, Optional, Tuple
import math


def get_element_placement(element: ifcopenshell.entity_instance) -> Optional[Dict[str, Any]]:
    """Get element's local placement (insertion point) coordinates.

    Extracts the placement point from IfcLocalPlacement attribute.
    This returns the element's INSERTION/REFERENCE POINT, not its geometric
    center or bounding box center.

    Args:
        element: IFC element instance

    Returns:
        Dict with 'location' (x, y, z coordinates) and 'has_placement' flag:
        {
            "has_placement": True,
            "location": (x, y, z),
            "x": float,
            "y": float,
            "z": float
        }
        Returns None if element has no placement.

    Note:
        - For IfcDoor: typically corner or centerline of door frame
        - For IfcWall: typically starting point of wall
        - For IfcStair: typically reference point at stair base
        - Use get_element_bounding_box() for full geometric extent

    Example:
        # Check if two floor slabs are at same elevation (with tolerance)
        slab1_z = get_element_placement(slab1)['z']
        slab2_z = get_element_placement(slab2)['z']
        if abs(slab1_z - slab2_z) <= 10.0:  # 10mm tolerance
            same_elevation = True

        # Calculate horizontal distance between two exits
        exit1 = get_element_placement(door1)
        exit2 = get_element_placement(door2)
        distance = calculate_distance_3d(exit1['location'], exit2['location'])
    """
    if not element or not hasattr(element, 'ObjectPlacement'):
        return None

    placement = element.ObjectPlacement
    if not placement or not placement.is_a('IfcLocalPlacement'):
        return None

    if not hasattr(placement, 'RelativePlacement'):
        return None

    rel_placement = placement.RelativePlacement
    if not hasattr(rel_placement, 'Location'):
        return None

    location = rel_placement.Location
    if not hasattr(location, 'Coordinates'):
        return None

    coords = location.Coordinates
    # Ensure we have 3 coordinates
    if len(coords) < 3:
        coords = list(coords) + [0.0] * (3 - len(coords))

    return {
        "has_placement": True,
        "location": (coords[0], coords[1], coords[2]),
        "x": coords[0],
        "y": coords[1],
        "z": coords[2]
    }


def get_element_elevation(element: ifcopenshell.entity_instance) -> Optional[float]:
    """Get element's insertion point elevation (Z-coordinate).

    Returns only the Z coordinate from element's placement point.
    This is the INSERTION POINT elevation, not the geometric center elevation.

    Args:
        element: IFC element instance

    Returns:
        Elevation as float (Z coordinate of insertion point), or None if not available

    Note:
        - For elements spanning multiple elevations (e.g., walls, stairs),
          this returns the placement point Z, not top/bottom/center
        - Use get_element_bounding_box() to get full vertical extent (min_z, max_z)

    Example:
        # Quick elevation comparison with tolerance
        door_z = get_element_elevation(door)
        slab_z = get_element_elevation(slab)
        if abs(door_z - slab_z) <= 10.0:
            on_same_level = True

        # Filter elements by storey elevation range
        storey1_elev = get_storey_elevation(storey1)
        storey2_elev = get_storey_elevation(storey2)
        element_z = get_element_elevation(element)
        if storey1_elev <= element_z < storey2_elev:
            element_on_storey1 = True
    """
    placement = get_element_placement(element)
    if placement:
        return placement["z"]
    return None


def get_element_bounding_box(element: ifcopenshell.entity_instance,
                             ifc_file: ifcopenshell.file) -> Optional[Dict[str, Any]]:
    """Get element's axis-aligned bounding box from actual geometry.

    Calculates the full geometric extent of an element using ifcopenshell.geom.
    Unlike get_element_placement() which returns only the insertion point,
    this returns the complete spatial bounds of the element's 3D geometry.

    Args:
        element: IFC element instance
        ifc_file: IFC file instance (needed for geometry processing)

    Returns:
        Dict with min/max coordinates and dimensions, or None if geometry unavailable:
        {
            "min_x": float, "max_x": float,
            "min_y": float, "max_y": float,
            "min_z": float, "max_z": float,
            "width": float,   # x dimension (max_x - min_x)
            "depth": float,   # y dimension (max_y - min_y)
            "height": float   # z dimension (max_z - min_z)
        }

    Note:
        - Computationally expensive (processes full 3D geometry)
        - May fail for elements without valid geometry representation
        - Use get_element_elevation() for quick elevation checks
        - Use this when you need full vertical/horizontal extent
        - For IfcSpace elements, uses multiple fallback strategies to handle
          complex geometries like IfcPolygonalFaceSet and IfcGeometricCurveSet

    Example:
        # Check if stair extends to roof elevation
        bbox = get_element_bounding_box(stair, ifc_file)
        roof_elevation = get_storey_elevation(roof_storey)
        if bbox and bbox["max_z"] >= roof_elevation:
            stair_reaches_roof = True

        # Get actual height of a wall (not just placement point)
        bbox = get_element_bounding_box(wall, ifc_file)
        wall_height = bbox["height"]  # Full vertical extent

        # Check if element is within a vertical range
        if bbox["min_z"] >= floor_z and bbox["max_z"] <= ceiling_z:
            within_range = True
    """
    try:
        import ifcopenshell.geom

        # Strategy 1: Try with USE_WORLD_COORDS (most common case)
        try:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)

            shape = ifcopenshell.geom.create_shape(settings, element)
            if shape and shape.geometry and shape.geometry.verts:
                bbox = shape.geometry.verts

                # Extract all coordinates (verts is a flat list: x1,y1,z1,x2,y2,z2,...)
                xs = [bbox[i] for i in range(0, len(bbox), 3)]
                ys = [bbox[i + 1] for i in range(0, len(bbox), 3)]
                zs = [bbox[i + 2] for i in range(0, len(bbox), 3)]

                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                min_z, max_z = min(zs), max(zs)

                return {
                    "min_x": min_x,
                    "max_x": max_x,
                    "min_y": min_y,
                    "max_y": max_y,
                    "min_z": min_z,
                    "max_z": max_z,
                    "width": max_x - min_x,
                    "depth": max_y - min_y,
                    "height": max_z - min_z
                }
        except Exception:
            pass

        # Strategy 2: Try without USE_WORLD_COORDS
        try:
            settings = ifcopenshell.geom.settings()

            shape = ifcopenshell.geom.create_shape(settings, element)
            if shape and shape.geometry and shape.geometry.verts:
                bbox = shape.geometry.verts

                # Extract coordinates
                xs = [bbox[i] for i in range(0, len(bbox), 3)]
                ys = [bbox[i + 1] for i in range(0, len(bbox), 3)]
                zs = [bbox[i + 2] for i in range(0, len(bbox), 3)]

                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                min_z, max_z = min(zs), max(zs)

                # Get element placement to transform to world coordinates
                placement = get_element_placement(element)
                if placement:
                    offset_x = placement["x"]
                    offset_y = placement["y"]
                    offset_z = placement["z"]
                else:
                    offset_x = offset_y = offset_z = 0.0

                return {
                    "min_x": min_x + offset_x,
                    "max_x": max_x + offset_x,
                    "min_y": min_y + offset_y,
                    "max_y": max_y + offset_y,
                    "min_z": min_z + offset_z,
                    "max_z": max_z + offset_z,
                    "width": max_x - min_x,
                    "depth": max_y - min_y,
                    "height": max_z - min_z
                }
        except Exception:
            pass

        # Strategy 3: For IfcSpace or other challenging geometries,
        # use get_element_geometry_metrics as fallback
        try:
            metrics = get_element_geometry_metrics(element, method="obb")
            if metrics:
                # get_element_geometry_metrics returns dimensions but not absolute position
                # We need to derive bounding box from placement + dimensions
                placement = get_element_placement(element)
                if placement:
                    # Assume element placement is at the lower corner
                    min_x = placement["x"]
                    min_y = placement["y"]
                    min_z = placement["z"]

                    # Add dimensions to get max coordinates
                    # Note: This is an approximation - actual orientation may vary
                    max_x = min_x + (metrics["width_mm"] / 1000.0)
                    max_y = min_y + (metrics["depth_mm"] / 1000.0)
                    max_z = min_z + (metrics["height_mm"] / 1000.0)

                    return {
                        "min_x": min_x,
                        "max_x": max_x,
                        "min_y": min_y,
                        "max_y": max_y,
                        "min_z": min_z,
                        "max_z": max_z,
                        "width": metrics["width_mm"] / 1000.0,
                        "depth": metrics["depth_mm"] / 1000.0,
                        "height": metrics["height_mm"] / 1000.0
                    }
        except Exception:
            pass

        # All strategies failed
        return None

    except Exception:
        # Unexpected error
        return None


def calculate_distance_3d(point1: Tuple[float, float, float],
                          point2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance between two 3D points.

    Pure mathematical function that doesn't depend on IFC objects.

    Args:
        point1: First point as (x, y, z) tuple
        point2: Second point as (x, y, z) tuple

    Returns:
        Distance as float

    Example:
        p1 = (0.0, 0.0, 0.0)
        p2 = (1000.0, 0.0, 0.0)
        distance = calculate_distance_3d(p1, p2)
        # Returns: 1000.0

        # To calculate horizontal distance between two elements:
        # placement1 = get_element_placement(element1)
        # placement2 = get_element_placement(element2)
        # distance = calculate_distance_3d(placement1["location"], placement2["location"])
    """
    return math.sqrt(
        (point1[0] - point2[0]) ** 2 +
        (point1[1] - point2[1]) ** 2 +
        (point1[2] - point2[2]) ** 2
    )


def get_storey_elevation(storey: ifcopenshell.entity_instance) -> Optional[float]:
    """Get building storey's elevation attribute.

    Extracts the Elevation attribute from an IfcBuildingStorey element.

    Args:
        storey: IfcBuildingStorey instance

    Returns:
        Elevation as float, or None if not available or not a storey

    Example:
        storey = ifc_file.by_guid("storey_id")
        elevation = get_storey_elevation(storey)
        # Returns: 3600.0 (or the storey elevation in mm)

        # Use case: Count storeys above grade plane
        # storeys = ifc_file.by_type("IfcBuildingStorey")
        # above_grade = [s for s in storeys if get_storey_elevation(s) and get_storey_elevation(s) > 0]
        # if len(above_grade) >= 4:
        #     building_qualifies = True
    """
    if not storey or not storey.is_a('IfcBuildingStorey'):
        return None

    if hasattr(storey, 'Elevation') and storey.Elevation is not None:
        return float(storey.Elevation)

    return None


def get_element_geometry_metrics(element: ifcopenshell.entity_instance,
                                 method: str = "obb") -> Optional[Dict[str, Any]]:
    """Extract geometric metrics from any IFC element using BREP analysis.

    This is a low-level utility function that uses BREP (Boundary Representation)
    geometry to calculate accurate dimensions for any IFC element.
    Can be used for IfcSpace, IfcWall, IfcDoor, or any geometric element.

    Uses either OBB (Oriented Bounding Box) or AABB (Axis-Aligned Bounding Box)
    to calculate element dimensions:
    - OBB: Minimum rotated rectangle - RECOMMENDED, most accurate
    - AABB: Axis-aligned rectangle - NOT RECOMMENDED, significantly overestimates dimensions

    Args:
        element: IFC element instance (any geometric element)
        method: "obb" (Oriented Bounding Box, RECOMMENDED) or "aabb" (not recommended)

    Returns:
        Dict with geometric metrics, or None if geometry extraction fails:
        {
            "width_mm": 986.0,           # Minimum dimension in XY plane
            "depth_mm": 2726.0,          # Maximum dimension in XY plane
            "height_mm": 2600.0,         # Z dimension
            "min_dimension_mm": 986.0,   # min(width, depth) - for compliance checks
            "area_m2": 2.687,            # 2D footprint area (width × depth)
            "volume_m3": 6.986,          # 3D volume (width × depth × height)
            "method": "obb",             # Method used
            "vertex_count": 18,          # Number of vertices processed
            "success": True              # Always True if returned
        }

    Note:
        - Returns None if geometry extraction or calculation fails
        - **Always use OBB method** - matches Solibri/BIM tools accuracy
        - AABB method significantly overestimates (e.g., 2023mm vs 986mm for same space)
        - Computationally expensive - use for validation, not real-time queries
        - Example: Essen space OBB=986mm×2726mm (2.687m²) vs AABB=2023mm×2877mm (5.82m²)
                  OBB matches IFC GrossFloorArea (2.678m²), AABB is 2x larger

    Use cases:
        # Calculate accurate space dimensions
        space = ifc_file.by_guid("space_id")
        dims = get_element_geometry_metrics(space, method="obb")
        if dims["min_dimension_mm"] >= 2134:  # 7 feet
            compliant = True

        # Get wall dimensions for material calculations
        wall = ifc_file.by_guid("wall_id")
        dims = get_element_geometry_metrics(wall, method="obb")
        wall_area = dims["area_m2"]

        # Foundation for higher-level analysis tools
        from ifc_tool_utils.ifcopenshell.geometry_queries import get_element_geometry_metrics
        dims = get_element_geometry_metrics(element, method="obb")
    """
    try:
        import ifcopenshell.geom
        import numpy as np
        from shapely.geometry import MultiPoint

        # Extract BREP geometry
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = shape.geometry.verts

        # Convert to 3D points
        points_3d = [(verts[i], verts[i+1], verts[i+2])
                     for i in range(0, len(verts), 3)]

        if len(points_3d) < 3:
            return None

        # Project to 2D (XY plane)
        points_2d = [(p[0], p[1]) for p in points_3d]
        unique_2d = list(set(points_2d))

        if method == "obb":
            # Oriented Bounding Box (minimum rotated rectangle)
            multipoint = MultiPoint(unique_2d)
            min_rect = multipoint.minimum_rotated_rectangle
            coords = list(min_rect.exterior.coords)

            # Calculate edge lengths
            edge_lengths = []
            for i in range(len(coords) - 1):
                x1, y1 = coords[i]
                x2, y2 = coords[i + 1]
                length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2) * 1000  # mm
                edge_lengths.append(length)

            unique_lengths = sorted(set([round(l, 1) for l in edge_lengths]))

            if len(unique_lengths) < 2:
                return None

            width_mm = unique_lengths[0]
            depth_mm = unique_lengths[1]

        else:  # method == "aabb"
            # Axis-Aligned Bounding Box
            xs = [p[0] for p in points_2d]
            ys = [p[1] for p in points_2d]
            width_mm = (max(xs) - min(xs)) * 1000
            depth_mm = (max(ys) - min(ys)) * 1000

        # Calculate height from Z coordinates
        zs = [p[2] for p in points_3d]
        height_mm = (max(zs) - min(zs)) * 1000

        # Calculate area and volume
        area_m2 = width_mm * depth_mm / 1_000_000
        volume_m3 = width_mm * depth_mm * height_mm / 1_000_000_000

        return {
            "width_mm": round(width_mm, 1),
            "depth_mm": round(depth_mm, 1),
            "height_mm": round(height_mm, 1),
            "min_dimension_mm": round(min(width_mm, depth_mm), 1),
            "area_m2": round(area_m2, 3),
            "volume_m3": round(volume_m3, 3),
            "method": method,
            "vertex_count": len(points_3d),
            "success": True
        }

    except Exception:
        return None
