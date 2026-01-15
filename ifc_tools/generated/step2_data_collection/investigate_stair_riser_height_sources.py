"""
Tool: investigate_stair_riser_height_sources
Category: step2_data_collection
Description: Examines IfcStair elements to identify potential sources of riser height information, including quantity sets, property sets, and geometric representations.
"""

import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.geom
from typing import List, Dict, Any, Optional
from ifc_tool_utils.ifcopenshell.element_queries import get_element_by_id, get_elements_by_type
from ifc_tool_utils.ifcopenshell.property_queries import find_all_psets, get_pset_property
from ifc_tool_utils.ifcopenshell.quantity_queries import find_all_quantities, get_quantity_value

def investigate_stair_riser_height_sources(ifc_file_path: str, stair_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Investigate riser height data sources in IfcStair elements.
    
    Examines properties, quantities, and geometric representation of specified IfcStair
    elements to identify potential sources of riser height information. Returns detailed
    information about available data sources including quantity sets, property sets,
    and geometric measurements.
    
    Args:
        ifc_file_path: Path to the IFC file.
        stair_ids: Optional list of GlobalIds for specific IfcStair elements to analyze.
            If None, analyzes all IfcStair elements in the file.
    
    Returns:
        List of dictionaries, each containing:
            - stair_id: GlobalId of the IfcStair element
            - stair_name: Name of the stair (if available)
            - quantity_sets: List of quantity sets with potential riser height data
            - property_sets: List of property sets with potential riser height data
            - geometric_measurements: List of geometric measurements that could be used
              to calculate riser height
            - riser_height_sources: Summary of identified riser height data sources
    
    Example:
        >>> results = investigate_stair_riser_height_sources("model.ifc", ["3qKJzL9r5B6gT2wX1yZ"])
        >>> print(results[0]['riser_height_sources'])
    """
    # Open IFC file with specific error handling
    try:
        ifc_file = ifcopenshell.open(ifc_file_path)
    except FileNotFoundError:
        raise ValueError(f"IFC file not found: {ifc_file_path}")
    
    # Get stair elements
    if stair_ids:
        stairs = []
        for stair_id in stair_ids:
            stair = get_element_by_id(ifc_file, stair_id)
            if stair and stair.is_a("IfcStair"):
                stairs.append(stair)
            elif stair and not stair.is_a("IfcStair"):
                raise ValueError(f"Element {stair_id} is not an IfcStair")
    else:
        stairs = get_elements_by_type(ifc_file, "IfcStair")
    
    results = []
    
    for stair in stairs:
        stair_info = {
            "stair_id": stair.GlobalId,
            "stair_name": stair.Name if hasattr(stair, "Name") and stair.Name else None,
            "quantity_sets": [],
            "property_sets": [],
            "geometric_measurements": [],
            "riser_height_sources": []
        }
        
        # 1. Analyze quantity sets
        quantity_sets = find_all_quantities(stair)
        for qset in quantity_sets:
            qset_name = qset.Name if hasattr(qset, "Name") and qset.Name else "Unnamed"
            quantities = []
            
            # Check for quantities that might contain riser height information
            if hasattr(qset, "Quantities"):
                for quantity in qset.Quantities:
                    if hasattr(quantity, "Name"):
                        quantity_name = quantity.Name.lower()
                        # Look for riser-related quantities
                        if "riser" in quantity_name or "height" in quantity_name:
                            quantity_value = None
                            if hasattr(quantity, "LengthValue"):
                                quantity_value = quantity.LengthValue
                            elif hasattr(quantity, "Value"):
                                quantity_value = quantity.Value
                            
                            if quantity_value:
                                quantities.append({
                                    "name": quantity.Name,
                                    "value": quantity_value,
                                    "unit": getattr(quantity, "Unit", None)
                                })
            
            if quantities:
                stair_info["quantity_sets"].append({
                    "name": qset_name,
                    "quantities": quantities
                })
                stair_info["riser_height_sources"].append(f"Quantity set: {qset_name}")
        
        # 2. Analyze property sets
        property_sets = find_all_psets(stair)
        for pset in property_sets:
            pset_name = pset.Name if hasattr(pset, "Name") and pset.Name else "Unnamed"
            properties = []
            
            # Check for properties that might contain riser height information
            if hasattr(pset, "HasProperties"):
                for prop in pset.HasProperties:
                    if hasattr(prop, "Name"):
                        prop_name = prop.Name.lower()
                        # Look for riser-related properties
                        if "riser" in prop_name or "height" in prop_name:
                            prop_value = None
                            if hasattr(prop, "NominalValue"):
                                prop_value = prop.NominalValue.wrappedValue if prop.NominalValue else None
                            elif hasattr(prop, "EnumerationValues"):
                                prop_value = [v.wrappedValue for v in prop.EnumerationValues]
                            
                            if prop_value:
                                properties.append({
                                    "name": prop.Name,
                                    "value": prop_value,
                                    "type": prop.is_a()
                                })
            
            if properties:
                stair_info["property_sets"].append({
                    "name": pset_name,
                    "properties": properties
                })
                stair_info["riser_height_sources"].append(f"Property set: {pset_name}")
        
        # 3. Analyze geometric representation for potential riser height calculation
        if hasattr(stair, "Representation"):
            representations = []
            if stair.Representation:
                representations = stair.Representation.Representations
            
            for rep in representations:
                if rep.is_a("IfcShapeRepresentation"):
                    # Check for stair flight representation
                    if rep.RepresentationIdentifier == "Body" and rep.RepresentationType == "SweptSolid":
                        stair_info["geometric_measurements"].append({
                            "type": "SweptSolid representation",
                            "description": "Can be used to calculate riser height from flight geometry"
                        })
                        stair_info["riser_height_sources"].append("Geometric representation: SweptSolid")
                    
                    # Check for advanced boundary representation
                    elif rep.RepresentationIdentifier == "Body" and rep.RepresentationType == "AdvancedBrep":
                        stair_info["geometric_measurements"].append({
                            "type": "AdvancedBrep representation",
                            "description": "Detailed geometry that can be analyzed for riser dimensions"
                        })
                        stair_info["riser_height_sources"].append("Geometric representation: AdvancedBrep")
        
        # 4. Check for stair flight decomposition
        if hasattr(stair, "IsDecomposedBy"):
            for rel in stair.IsDecomposedBy:
                for flight in rel.RelatedObjects:
                    if flight.is_a("IfcStairFlight"):
                        # Check flight properties for riser information
                        flight_psets = ifcopenshell.util.element.get_psets(flight)
                        for pset_name, props in flight_psets.items():
                            for prop_name, prop_value in props.items():
                                if isinstance(prop_name, str) and ("riser" in prop_name.lower() or "height" in prop_name.lower()):
                                    stair_info["geometric_measurements"].append({
                                        "type": "Stair flight property",
                                        "description": f"Riser height from flight {flight.GlobalId}: {prop_name} = {prop_value}"
                                    })
                                    stair_info["riser_height_sources"].append(f"Stair flight property: {prop_name}")
        
        results.append(stair_info)
    
    return results