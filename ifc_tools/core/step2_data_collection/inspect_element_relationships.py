"""
Relationship Inspection Tools
Category: data_collection (Step2 - Data Collection)
Description: Inspects raw relationship data for debugging and exploration.
"""

from typing import Dict, Any, List
from ifc_tool_utils.ifcopenshell import get_element_by_id
from utils.ifc_file_manager import IFCFileManager


def inspect_element_relationships(
    ifc_file_path: str,
    element_id: str,
) -> Dict[str, Any]:
    """Inspect raw relationship data for a single element.

    This tool dumps all IFC relationship objects (IfcRel*) reachable from the
    element via its attributes. It is intended for debugging and exploration,
    not for direct compliance evaluation.

    For the element it reports:
    - Native attributes used to hold relations (e.g., "FillsVoids",
      "ContainedInStructure", "HasOpenings")
    - The underlying IfcRel* instances
    - The main endpoints of each relation (Relating*/Related* attributes)

    Args:
        ifc_file_path: Path to the IFC file.
        element_id: Single element GlobalId to inspect.

    Returns:
        Dictionary with:
        - element_id: GlobalId of the element
        - ifc_type: IFC type string (e.g., "IfcDoor", "IfcSpace")
        - relations: List of relation dicts:
            - attribute_name: Name of the attribute on the element that
              holds this relation (e.g., "FillsVoids")
            - relation_type: IFC type of the relation (e.g., "IfcRelFillsElement")
            - relation_id: GlobalId of the relation if available, otherwise
              the numeric STEP id as string
            - endpoints: List of endpoint dicts derived from the relation's
              Relating*/Related* attributes, each with:
                - role: Name of the endpoint attribute (e.g., "RelatingSpace")
                - element_id: GlobalId of the related element (if any)
                - ifc_type: IFC type of the related element (if any)
        - error: Optional error message if element not found.

        Returns error dict if operation fails.
    """
    try:
        import ifcopenshell

        with IFCFileManager(ifc_file_path) as ifc_file:
            element = get_element_by_id(ifc_file, element_id)
            if not element:
                return {
                    "element_id": element_id,
                    "ifc_type": None,
                    "relations": [],
                    "error": "Element not found",
                }

            ifc_type = element.is_a() if hasattr(element, "is_a") else None
            relations_out: List[Dict[str, Any]] = []

            # Inspect all attributes on the element and collect IfcRel* instances
            for attr_name in dir(element):
                if attr_name.startswith("_"):
                    continue
                try:
                    value = getattr(element, attr_name)
                except Exception:
                    continue

                # Normalise to iterable of potential relation objects
                candidates = []
                if isinstance(value, (list, tuple)):
                    candidates.extend(value)
                else:
                    candidates.append(value)

                for rel in candidates:
                    if not rel or not hasattr(rel, "is_a"):
                        continue
                    try:
                        rel_type = rel.is_a()
                    except Exception:
                        continue

                    if not isinstance(rel_type, str) or not rel_type.startswith("IfcRel"):
                        continue

                    # Determine a stable relation identifier
                    rel_id = None
                    if hasattr(rel, "GlobalId") and rel.GlobalId:
                        rel_id = rel.GlobalId
                    else:
                        # Fallback to numeric STEP id
                        try:
                            rel_id = f"#{rel.id()}"
                        except Exception:
                            rel_id = None

                    # Collect endpoints from Relating*/Related* attributes
                    endpoints: List[Dict[str, Any]] = []
                    if hasattr(rel, "get_info") and callable(rel.get_info):
                        try:
                            info = rel.get_info()
                        except Exception:
                            info = {}

                        for key, val in info.items():
                            if not isinstance(key, str):
                                continue
                            if not (key.startswith("Relating") or key.startswith("Related")):
                                continue

                            endpoint_candidates = []
                            if isinstance(val, (list, tuple)):
                                endpoint_candidates.extend(val)
                            else:
                                endpoint_candidates.append(val)

                            for ep in endpoint_candidates:
                                if not ep or not hasattr(ep, "GlobalId"):
                                    continue
                                ep_id = getattr(ep, "GlobalId", None)
                                ep_type = ep.is_a() if hasattr(ep, "is_a") else None
                                endpoints.append({
                                    "role": key,
                                    "element_id": ep_id,
                                    "ifc_type": ep_type,
                                })

                    relations_out.append({
                        "attribute_name": attr_name,
                        "relation_type": rel_type,
                        "relation_id": rel_id,
                        "endpoints": endpoints,
                    })

            return {
                "element_id": element_id,
                "ifc_type": ifc_type,
                "relations": relations_out,
            }

    except Exception as e:
        return {
            "error": f"Failed to inspect element relationships: {str(e)}",
        }
