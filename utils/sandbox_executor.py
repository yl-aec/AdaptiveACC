
from datetime import datetime
from typing import Dict, Any, Optional

from smolagents.local_python_executor import LocalPythonExecutor as SmolagentsExecutor
from models.common_models import TestResult

# Import ifcopenshell.util modules for function injection
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.shape
import ifcopenshell.util.unit


class LocalPythonExecutor:
    """Local Python code executor using smolagents with sandboxing"""

    def __init__(self, timeout: int = 30, max_memory_mb: int = 512):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        # Fallback for older ifcopenshell builds that lack certain helpers.
        get_openings = getattr(ifcopenshell.util.element, "get_openings", lambda *_, **__: [])
        # Add print function and other basic functions to allowed functions
        additional_functions = {
            # Basic Python functions
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'type': type,
            'isinstance': isinstance,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,

            # Injected ifcopenshell.util.element functions (most commonly used)
            # Property and type access
            'get_psets': ifcopenshell.util.element.get_psets,
            'get_pset': ifcopenshell.util.element.get_pset,
            'get_property': ifcopenshell.util.element.get_property,
            'get_type': ifcopenshell.util.element.get_type,
            'get_predefined_type': ifcopenshell.util.element.get_predefined_type,

            # Material access
            'get_material': ifcopenshell.util.element.get_material,
            'get_materials': ifcopenshell.util.element.get_materials,

            # Quantities
            'get_quantities': ifcopenshell.util.element.get_quantities,
            'get_quantity': ifcopenshell.util.element.get_quantity,

            # Spatial relationships
            'get_container': ifcopenshell.util.element.get_container,
            'get_contained': ifcopenshell.util.element.get_contained,

            # Opening relationships
            'get_openings': get_openings,
            'get_filled_void': ifcopenshell.util.element.get_filled_void,
            'get_voided_element': ifcopenshell.util.element.get_voided_element,

            # Decomposition and aggregation
            'get_decomposition': ifcopenshell.util.element.get_decomposition,
            'get_aggregate': ifcopenshell.util.element.get_aggregate,
            'get_parts': ifcopenshell.util.element.get_parts,

            # Groups
            'get_groups': ifcopenshell.util.element.get_groups,
            'get_grouped_by': ifcopenshell.util.element.get_grouped_by,

            # Placement and geometry (from ifcopenshell.util.placement)
            'get_local_placement': ifcopenshell.util.placement.get_local_placement,
            'get_storey_elevation': ifcopenshell.util.placement.get_storey_elevation,

            # Shape queries (from ifcopenshell.util.shape)
            'get_volume': ifcopenshell.util.shape.get_volume,
            'get_footprint_area': ifcopenshell.util.shape.get_footprint_area,
            'get_side_area': ifcopenshell.util.shape.get_side_area,
            'get_top_elevation': ifcopenshell.util.shape.get_top_elevation,
            'get_bottom_elevation': ifcopenshell.util.shape.get_bottom_elevation,

            # Unit conversions (from ifcopenshell.util.unit)
            'get_project_unit': ifcopenshell.util.unit.get_project_unit,
            'get_property_unit': ifcopenshell.util.unit.get_property_unit,
            'get_unit_name': ifcopenshell.util.unit.get_unit_name,
            'get_unit_symbol': ifcopenshell.util.unit.get_unit_symbol,
            'calculate_unit_scale': ifcopenshell.util.unit.calculate_unit_scale,
            'convert': ifcopenshell.util.unit.convert,
        }
        
        self.executor = SmolagentsExecutor(
            additional_authorized_imports=[
                # Core libraries
                'pytest', 'ifcopenshell', 'os', 'json', 'traceback', 'tempfile',
                # ifcopenshell modules
                'ifcopenshell.geom',
                # ifcopenshell.util modules - allowed for import statements
                # Note: Functions are still injected via additional_functions for sandbox access
                'ifcopenshell.util.element',
                'ifcopenshell.util.placement',
                'ifcopenshell.util.shape',
                'ifcopenshell.util.unit',
                # Standard library (essential for type hints)
                'typing', 'collections',
                # Custom modules - top level
                'ifc_tool_utils', 'utils',
                # Custom modules - submodules (explicit paths required by smolagents)
                'utils.ifc_file_manager',
                'ifc_tool_utils.ifcopenshell',
                'ifc_tool_utils.ifcopenshell.element_queries',
                'ifc_tool_utils.ifcopenshell.property_queries',
                'ifc_tool_utils.ifcopenshell.relationship_queries',
                'ifc_tool_utils.ifcopenshell.quantity_queries'
            ],
            additional_functions=additional_functions
        )
        # Initialize static_tools by calling send_tools (required for additional_functions to work)
        self.executor.send_tools({})
    
    def execute_code(self, code: str, test_inputs: Optional[Dict[str, Any]] = None) -> TestResult:
        """Execute code with given inputs and return results"""
        try:
            # Prepare code with test inputs if provided
            if test_inputs:
                # Add test inputs to the code as global variables
                inputs_code = "# Test inputs\n"
                for key, value in test_inputs.items():
                    inputs_code += f"{key} = {repr(value)}\n"
                code = inputs_code + "\n" + code

            # Execute using smolagents executor
            result = self.executor(code)

            # Handle smolagents CodeOutput result
            if hasattr(result, 'output'):
                success = True  # If no exception was raised, consider it successful
                output = str(result.output) if result.output is not None else ""
                error = ""
            else:
                # Fallback for other result types
                success = True
                output = str(result)
                error = ""

        except Exception as e:
            # Check if this is a ReturnException from smolagents (normal return, not an error)
            from smolagents.local_python_executor import ReturnException
            if isinstance(e, ReturnException):
                # This is a normal function return, extract the returned value
                success = True
                output = str(e.args[0]) if e.args else ""
                error = ""
            else:
                # This is an actual error
                success = False
                output = ""
                error = f"Execution error: {str(e)}"

        return TestResult(
            success=success,
            output=output,
            error=error
        )

    def execute_function_with_args(self, code: str, function_name: str,
                                   args: list = None, kwargs: dict = None) -> TestResult:
        """Execute a specific function with provided arguments"""
        import json

        args = args or []
        kwargs = kwargs or {}

        # Build parameter assignment code to avoid dynamic unpacking
        # This creates individual parameter assignments that the sandbox can validate
        param_setup = []
        if kwargs:
            for key, value in kwargs.items():
                # Use repr for safe serialization of values
                param_setup.append(f"_{key} = {repr(value)}")

        # Build function call with explicit parameter names (no * or ** unpacking)
        if kwargs:
            # Named parameters
            param_names = ', '.join([f"{key}=_{key}" for key in kwargs.keys()])
            call_code = f"{function_name}({param_names})"
        elif args:
            # Positional parameters (construct as explicit list)
            args_repr = ', '.join([repr(arg) for arg in args])
            call_code = f"{function_name}({args_repr})"
        else:
            call_code = f"{function_name}()"

        # Build complete test code
        # Note: smolagents should handle builtins via additional_functions parameter
        test_code = f"""{code}

# Parameter setup (explicit assignments, no unpacking)
{chr(10).join(param_setup)}

# Call function with explicit parameters (sandbox-safe)
_result = {call_code}
_result
"""
        return self.execute_code(test_code)
