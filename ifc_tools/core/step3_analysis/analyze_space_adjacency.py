"""
Tool: Space Topological Analysis
Category: topological
Description: Functions for analyzing spatial topology and connectivity
"""

import ifcopenshell
from typing import List, Dict, Any, Optional
from ifc_tool_utils.ifcopenshell import get_elements_by_type, get_elements_by_ids
from ifc_tool_utils.ifcopenshell.relationship_queries import (
    get_space_boundaries,
    find_adjacent_spaces_via_boundaries
)
from utils.ifc_file_manager import IFCFileManager


def analyze_space_adjacency(ifc_file_path: str, space_ids: List[str] = None) -> Dict[str, Any]:
    """Analyze adjacency relationships between spaces using IfcRelSpaceBoundary.

    This function uses IFC space boundary relationships to determine which spaces
    are adjacent to each other through shared building elements (walls, doors, etc.).
    This approach is more accurate and efficient than geometric calculations.

    Args:
        ifc_file_path: Path to the IFC file
        space_ids: Optional list of specific space GlobalIds to analyze

    Returns:
        Dictionary containing adjacency analysis results with format:
        {
            "spaces": [...],                    # List of space information
            "adjacency_matrix": [[...]],        # Boolean adjacency matrix
            "adjacent_pairs": [...]             # List of adjacency pair dictionaries
        }
        Note: Use len(spaces) for total spaces count, len(adjacent_pairs) for total adjacencies
    """
    try:
        with IFCFileManager(ifc_file_path) as ifc_file:
            # Get spaces to analyze
            if space_ids:
                spaces = get_elements_by_ids(ifc_file, space_ids)
                # Filter to only include IfcSpace elements
                spaces = [s for s in spaces if s and s.is_a('IfcSpace')]
            else:
                spaces = get_elements_by_type(ifc_file, 'IfcSpace')

            if not spaces:
                return {
                    "spaces": [],
                    "adjacency_matrix": [],
                    "adjacent_pairs": [],
                    "error": "No spaces found in IFC file"
                }

            # Check if space boundaries are available
            all_boundaries = get_space_boundaries(ifc_file)
            boundaries_available = len(all_boundaries) > 0

            if not boundaries_available:
                return {
                    "spaces": [],
                    "adjacency_matrix": [],
                    "adjacent_pairs": [],
                    "error": "IfcRelSpaceBoundary data not available in this IFC file. Please ensure the IFC model includes space boundary relationships.",
                    "suggestion": "Re-export the model with space boundary information enabled, or use a more complete BIM model."
                }

            space_info = []
            adjacency_matrix = []

            for space in spaces:
                space_data = {
                    "space_id": space.GlobalId,
                    "name": space.Name or ""
                }
                space_info.append(space_data)

            # Build adjacency matrix
            n_spaces = len(spaces)
            adjacency_matrix = [[False for _ in range(n_spaces)] for _ in range(n_spaces)]

            for i, space1 in enumerate(spaces):
                adjacent_spaces = find_adjacent_spaces_via_boundaries(ifc_file, space1)
                for space2 in adjacent_spaces:
                    try:
                        j = spaces.index(space2)
                        adjacency_matrix[i][j] = True
                        adjacency_matrix[j][i] = True  # Symmetric relationship
                    except ValueError:
                        # space2 not in our analysis list, skip
                        continue

            # Convert to readable format
            adjacency_pairs = []
            for i in range(n_spaces):
                for j in range(i + 1, n_spaces):
                    if adjacency_matrix[i][j]:
                        adjacency_pairs.append({
                            "space1_id": space_info[i]["space_id"],
                            "space1_name": space_info[i]["name"],
                            "space2_id": space_info[j]["space_id"],
                            "space2_name": space_info[j]["name"]
                        })

            return {
                "spaces": space_info,
                "adjacency_matrix": adjacency_matrix,
                "adjacent_pairs": adjacency_pairs
            }

    except Exception as e:
        return {
            "spaces": [],
            "adjacency_matrix": [],
            "adjacent_pairs": [],
            "error": f"Space adjacency analysis failed: {str(e)}"
        }
