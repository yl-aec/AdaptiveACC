from typing import List
from models.common_models import AgentToolResult, IFCToolResult, ToolCreatorOutput, RetrievedDocument
from models.shared_context import SharedContext
from utils.rag_doc import DocumentRetriever
from utils.llm_client import LLMClient
from telemetry.tracing import trace_method
from opentelemetry import trace


class ToolCreation:
    """Meta tool to create new tools based on task description"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.llm_client = LLMClient()
        self.document_retriever = DocumentRetriever.get_instance()
        self.max_static_iterations = 3
        
    # Executor Interface
    @trace_method("create_ifc_tool")
    def create_ifc_tool(self, task_description: str) -> AgentToolResult:
        """Create a new IFC tool when none exists for the task.

        Retrieves relevant documentation, generates code directly from task description,
        and performs static checking to create a new IFC tool.

        Args:
            task_description: Description of what the tool should accomplish

        Returns:
            AgentToolResult: Success with created tool info, or failure if creation failed
        """

        span = trace.get_current_span()
        print(f"=== Creating IFC tool ===")
        print(f"Task description: {task_description}")

        try:
            # Record task information
            span.set_attribute("create_ifc_tool.task_description", task_description)

            # Step 1: Retrieve relevant documentation
            print("\n[Step 1] Retrieving relevant documentation...")
            relevant_docs = self.document_retriever.retrieve_relevant_docs(
                task_description, k=5
            )
            print(f"Retrieved {len(relevant_docs)} relevant documents")
            span.set_attribute("create_ifc_tool.docs_retrieved", len(relevant_docs))

            # Step 2: Generate tool code with structured output
            print("\n[Step 2] Generating tool code...")
            tool_output = self.generate_code(task_description, relevant_docs)
            print("\n[Step 2] Tool Code Generated")
            
            if not tool_output:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="create_ifc_tool",
                    error="Failed to generate tool output"
                )

            # Step 3: Static checking with retry on generated code
            print("\n[Step 3] Static code analysis...")
            current_code = tool_output.code

            for iteration in range(1, self.max_static_iterations + 1):
                check_result = self._check_syntax(current_code, tool_output.ifc_tool_name)

                if check_result.success:
                    print(f"Static analysis PASSED after {iteration} iterations")
                    # Update tool_output with validated code if it was modified
                    if current_code != tool_output.code:
                        tool_output.code = current_code
                    break

                if iteration < self.max_static_iterations:
                    print(f"Found syntax issues, attempting to fix...")
                    # Use fix_code method for syntax fixes
                    fixed_output = self._fix_code_for_syntax(
                        code=current_code,
                        check_result=check_result,
                        tool_name=tool_output.ifc_tool_name
                    )
                    current_code = fixed_output.code if fixed_output else current_code
                else:
                    return AgentToolResult(
                        success=False,
                        agent_tool_name="create_ifc_tool",
                        error=f"Static check failed: {check_result.error_message or 'Unknown syntax error'}"
                    )

            # Step 4: Output final tool
            print(f"\n[Step 4] IFC tool '{tool_output.ifc_tool_name}' created successfully")

            # Record successful creation
            span.set_attribute("create_ifc_tool.success", True)
            span.set_attribute("create_ifc_tool.final_tool_name", tool_output.ifc_tool_name)
            span.set_attribute("create_ifc_tool.generated_code", tool_output.code[:500] + "..." if len(tool_output.code) > 500 else tool_output.code)

            # Create result with ToolCreatorOutput
            result = AgentToolResult(
                success=True,
                agent_tool_name="create_ifc_tool",
                result=tool_output  # ToolCreatorOutput object
            )

            return result

        except Exception as e:
            print(f"\n=== IFC tool creation FAILED with exception ===")
            print(f"Error: {str(e)}")

            span.set_attribute("create_ifc_tool.success", False)
            span.set_attribute("create_ifc_tool.error", str(e))

            return AgentToolResult(
                success=False,
                agent_tool_name="create_ifc_tool",
                error=f"Unexpected error: {str(e)}"
            )
    

    def _check_syntax(self, code: str, tool_name: str = "unknown") -> IFCToolResult:
        """Enhanced syntax and structure checking"""
        try:
            # Step 1: Basic syntax check
            compile(code, '<string>', 'exec')

            # Step 2: Check function definition exists
            import ast
            tree = ast.parse(code)

            # Find all function definitions
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            if not functions:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    error_message="No function definition found in code",
                    exception_type="ValidationError"
                )

            # Step 3: Check if function name matches tool_name
            function_names = [f.name for f in functions]
            if tool_name != "unknown" and tool_name not in function_names:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    error_message=f"Function name mismatch. Expected '{tool_name}', found: {function_names}",
                    exception_type="ValidationError"
                )

            # Step 4: Check for required imports (IFCFileManager is commonly needed)
            import_names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    import_names.append(node.module)
                elif isinstance(node, ast.Import):
                    import_names.extend([alias.name for alias in node.names])

            # Validation passed
            return IFCToolResult(
                success=True,
                ifc_tool_name=tool_name
            )

        except SyntaxError as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                error_message=f"Syntax error at line {e.lineno}: {e.msg}",
                exception_type="SyntaxError",
                line_number=e.lineno
            )
        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                error_message=f"Code analysis error: {e}",
                exception_type=type(e).__name__
            )

    def generate_code(self, task_description: str, relevant_docs: List[RetrievedDocument]) -> ToolCreatorOutput:
        """Generate complete tool with structured output directly from task description"""

        system_prompt = """
        You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to generate **complete, production-ready Python functions** based on task descriptions.
        ───────────────────────────────────────
        ## 1. CORE RESPONSIBILITIES
        - Implement complete and runnable Python functions
        - Use correct IFC processing practices
        - Follow strict error-handling rules (see below)
        - Produce accurate metadata
        ────────────────────────────────────────
        ## 2. TOOL DESIGN PRINCIPLES (from task description)

        ### 2.1 Single-Purpose Tools
        The tool must perform **one specific action** on **one well-defined data scope**.
        Examples:
        - "Identify element IDs" → return ONLY IDs
        - "Extract property X" → return ONLY that property
        Do NOT create multi-purpose tools that do multiple unrelated things.

        ### 2.2 Function Naming Convention
        Use: **{action}_{target}_{attribute}**
        - **action** (required): extract / get / find / calculate / validate / check / list
        - **target** (required): wall / door / window / space / element
        - **attribute** (optional but recommended): thickness / width / area / fire_rating

        Examples:
        - extract_wall_thickness
        - get_door_fire_rating
        - calculate_space_area
        - find_spaces_by_function

        ### 2.3 Parameter Design
        - Always include: `ifc_file_path: str` as first parameter
        - Use explicit, typed parameters (e.g., `element_ids: List[str]`, `property_name: str`)
        - Each parameter must have a clear meaning and expected input
        - Keep parameters simple and focused

        ### 2.4 Return Type Constraints
        Choose the simplest correct structure:
        - Single value → `str`, `int`, `float`, `bool`
        - Collections → `List[str]`, `Dict[str, Any]`, `List[Dict[str, Any]]`
        Use `Dict[str, Any]` for structured results keyed by element ID.

        ### 2.5 Code Style Requirements
        - Full type hints required
        - Follow PEP 8 standards
        - Include a Google-style docstring with Args / Returns / Example
        ────────────────────────────────────────
        ## 4. ERROR HANDLING POLICY (CRITICAL)

        ### DO NOT use:
        -  `try: ... except Exception:`
        -  bare `except:`
        -  wrapping the entire function in try/except

        This breaks sandbox execution, causing tools to return nothing.

        ### DO:
        - Prefer **no try/except** inside the function body
        - Only catch **specific exceptions** when absolutely necessary

          Example:
          ```python
          try:
              ifc_file = ifcopenshell.open(ifc_file_path)
          except FileNotFoundError:
              raise ValueError(f"IFC file not found: {ifc_file_path}")

        For missing data, return safe defaults:

        element not found → None or []
        missing property → None
        empty relationships → []
        ────────────────────────────────────────
        ## 5. STRUCTURED OUTPUT FORMAT

        Return a JSON object with:

        - tool_name: must match the function name
        - code: the complete Python function
        - metadata:
          - ifc_tool_name: same as function name
          - description: human-readable summary
          - parameters: each with name, type, description, required/default
          - return_type: exact schema
          - category: one of:
            * "step1_identification"
            * "step2_data_collection"
            * "step3_analysis"
            * "step4_verification"
            * "others" (use sparingly)
          - tags: keywords for search/discovery
        ────────────────────────────────────────
        ## AVAILABLE UTILITY FUNCTIONS (Import Required)

        ### File
        - ifcopenshell.open(path) → load IFC file

        ### Element Queries  (from ifc_tool_utils.ifcopenshell.element_queries)
        - get_element_by_id(ifc, id) → element | None   # fetch one element by GlobalId
        - get_elements_by_type(ifc, type) → List[element]   # all elements of IFC class
        - get_elements_by_ids(ifc, ids) → List[element]   # filter by GlobalId list
        - get_elements_by_property_value(ifc, type, prop, value, pset=None) → List[element]   # filter by attribute or pset
        - get_elements_by_predefined_type(ifc, type, predefined_type) → List[element]   # filter by PredefinedType attribute

        ### Property Queries  (from ifc_tool_utils.ifcopenshell.property_queries)
        - get_direct_attribute(el, attr_name) → Any | None   # direct IFC attribute (e.g., OverallHeight, OverallWidth)
        - find_all_psets(el) → List[IfcPropertySet]   # list all property set objects
        - get_pset_property(el, pset_name, prop_name) → Dict{"value": Any, "unit": str} | None   # extract property with unit from specific Pset

        ### Quantity Queries  (from ifc_tool_utils.ifcopenshell.quantity_queries)
        - find_all_quantities(el) → List[IfcElementQuantity]   # list all quantity set objects
        - get_quantity_value(el, qto_name, qty_name) → Dict{"value": float, "unit": str} | None   # extract quantity with unit from specific Qto

        ### Relationship Queries  (from ifc_tool_utils.ifcopenshell.relationship_queries)
        - get_host_element(filling) → element | None   # wall hosting door/window
        - get_filling_elements(host) → List[element]   # doors/windows hosted by wall
        - get_space_boundaries(ifc, space=None, type=None) → List[boundary]   # IfcRelSpaceBoundary
        - get_space_boundary_info(boundary) → Dict[str, Any]   # parsed boundary info
        - find_adjacent_spaces_via_boundaries(ifc, space) → List[element]   # spaces sharing INTERNAL boundaries
        ────────────────────────────────────────
        ## 6. EXAMPLE (Reference Only)

        ```python
        import ifcopenshell
        import ifcopenshell.util.element
        from typing import List, Dict, Any
        from ifc_tool_utils.ifcopenshell.element_queries import get_elements_by_type

        def analyze_wall_materials(ifc_file_path: str) -> List[Dict[str, Any]]:
            '''Analyze wall materials and their spatial location.

            Args:
                ifc_file_path: Path to the IFC file.

            Returns:
                List of dicts containing wall ID, material, and storey.
            '''
            ifc_file = ifcopenshell.open(ifc_file_path)

            # Get all walls using utility function
            walls = get_elements_by_type(ifc_file, "IfcWall")

            results = []
            for wall in walls:
                # Use ifcopenshell.util.element functions (must import!)
                material = ifcopenshell.util.element.get_material(wall)
                container = ifcopenshell.util.element.get_container(wall)

                results.append({
                    "wall_id": wall.GlobalId,
                    "material": material.Name if material else None,
                    "storey": container.Name if container else None
                })

            return results
        ```
        """

        # Process relevant documentation
        docs_context = ""
        if relevant_docs:
            docs_context = "RELEVANT DOCUMENTATION:\n"
            for i, doc in enumerate(relevant_docs, 1):
                docs_context += f"Document {i} (relevance: {doc.relevance_score:.3f}):\n"
                docs_context += f"{doc.content}...\n\n"

        prompt = f"""
        {docs_context}

        TASK DESCRIPTION:
        {task_description}

        Generate a complete Python tool that accomplishes the task described above.

        Follow all design principles:
        - Use clear, descriptive function naming (action_target_attribute pattern)
        - Design single-purpose tools with focused functionality
        - Include ifc_file_path: str as first parameter
        - Use appropriate return types (simple types for single values, collections for multiple items)
        - Add comprehensive docstrings with Args/Returns/Example sections
        - Use ifcopenshell as the primary library
        - Import utility functions from ifc_tool_utils.ifcopenshell when needed
        - Follow error handling policy (no broad except blocks)

        """

        try:
            tool_output = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                response_model=ToolCreatorOutput,
                max_retries=3
            )
            return tool_output

        except Exception as e:
            print(f"LLM structured tool generation failed: {e}")
            return None

    def _fix_code_for_syntax(self, code: str, check_result: IFCToolResult, tool_name: str):
        """Simplified fix_code for syntax errors during tool creation"""
        from models.common_models import FixedCodeOutput

        system_prompt = """You are an expert Python developer. Fix the syntax error in the code provided.

        Return JSON with:
        - code: the fixed Python function
        - summary: brief explanation of the fix
        """

        error_type = check_result.exception_type or "Unknown"
        error_msg = check_result.error_message or "No error message"

        prompt = f"""
        ERROR TYPE: {error_type}
        ERROR MESSAGE: {error_msg}

        CURRENT CODE:
        {code}

        Fix the syntax error and return the corrected code.
        """

        try:
            fixed_output = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                response_model=FixedCodeOutput,
                max_retries=2
            )

            if fixed_output is None:
                print(f"LLM returned None when attempting to fix syntax")
                return FixedCodeOutput(code=code, summary="Fix failed: LLM returned None")

            return fixed_output
        except Exception as e:
            print(f"Failed to fix syntax: {e}")
            return FixedCodeOutput(code=code, summary=f"Fix failed: {str(e)}")
