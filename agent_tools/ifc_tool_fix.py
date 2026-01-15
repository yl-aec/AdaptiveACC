import json
import traceback
from typing import Dict, Any, Optional, List
from models.common_models import AgentToolResult, IFCToolResult, ToolCreatorOutput, ToolMetadata, FixedCodeOutput
from models.shared_context import SharedContext
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from utils.llm_client import LLMClient
from telemetry.tracing import trace_method
from opentelemetry import trace

class ToolFix:
    """Skill to fix existing tools with various types of errors"""

    def __init__(self):
        self.tool_registry = IFCToolRegistry.get_instance()
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    # Executor Interface
    @trace_method("fix_ifc_tool")
    def fix_ifc_tool(self, ifc_tool_name: str, modification_requirement: str) -> AgentToolResult:
        """Fix or modify an IFC tool based on specific requirements.

        IMPORTANT: This tool can ONLY modify tools created in the current session.
        For existing/pre-existing tools, use create_ifc_tool to generate a new tool instead.

        This tool supports various modification types:
        - Error fixing: Fix runtime errors, exceptions, or bugs
        - Performance optimization: Improve efficiency, reduce loops, use batch operations
        - Output format adjustment: Add/modify return value structure, add units
        - Feature enhancement: Add parameters, filtering capabilities
        - Code quality improvement: Add validation, error handling

        Args:
            ifc_tool_name: Name of the IFC tool to fix/modify (must be from current session)
            modification_requirement: (REQUIRED) Clear description of what needs to be changed.
                Examples:
                - "Fix the runtime error from last execution"
                - "Add unit information to the return values"
                - "Optimize performance by using batch operations"
                - "Add filtering parameter to support material-based selection"
                - "Improve error handling and input validation"

        Returns:
            AgentToolResult: Success with fixed/modified tool info, or failure if unsuccessful
        """

        span = trace.get_current_span()

        try:
            # Record tool being fixed and modification requirement
            span.set_attribute("fix_ifc_tool.target_ifc_tool_name", ifc_tool_name)
            span.set_attribute("fix_ifc_tool.modification_requirement", modification_requirement)

            # Step 1: Validate tool was created in current session (not an existing tool)
            original_tool_info = self._get_tool_info(ifc_tool_name)
            if not original_tool_info:
                span.set_attribute("fix_ifc_tool.success", False)
                span.set_attribute("fix_ifc_tool.error", f"Tool '{ifc_tool_name}' not found in current session")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="fix_ifc_tool",
                    error=f"Tool '{ifc_tool_name}' not found in SharedContext. Only tools created in the current session (via create_ifc_tool or fix_ifc_tool) can be fixed. For existing/pre-existing tools, use create_ifc_tool to generate a new tool instead."
                )
                return result

            original_metadata_dict = original_tool_info["metadata"]
            code = original_tool_info["code"]

            # Convert metadata dict to ToolMetadata object
            original_metadata = ToolMetadata(**original_metadata_dict)

            # Step 2: Get error information from SharedContext (optional - may not have errors)
            error_info = self.shared_context.get_error_info_from_context(ifc_tool_name)
            check_result_obj = None
            if error_info:
                # Convert error dict to IFCToolResult object
                check_result_obj = IFCToolResult(**error_info)
                span.set_attribute("fix_ifc_tool.error_type", error_info.get('exception_type') or "unknown")
                span.set_attribute("fix_ifc_tool.error_message", error_info.get('error_message') or "")
                span.set_attribute("fix_ifc_tool.had_error", True)
            else:
                span.set_attribute("fix_ifc_tool.had_error", False)

            # Step 3: Get previous modifications from agent_history
            previous_modifications = self._get_previous_modifications(ifc_tool_name)
            if previous_modifications:
                span.set_attribute("fix_ifc_tool.previous_modifications_count", len(previous_modifications))

            # Step 4: Fix the code using fix_code method
            span.set_attribute("llm_call.purpose", "ifc_tool_code_fix")
            fixed_code_output = self.fix_code(
                code=code,
                modification_requirement=modification_requirement,
                check_result=check_result_obj,
                metadata=original_metadata,
                previous_modifications=previous_modifications
            )

            if not fixed_code_output or not fixed_code_output.code:
                span.set_attribute("fix_ifc_tool.success", False)
                span.set_attribute("fix_ifc_tool.error", f"Failed to fix code for IFC tool '{ifc_tool_name}'")
                result = AgentToolResult(
                    success=False,
                    agent_tool_name="fix_ifc_tool",
                    error=f"Failed to fix code for IFC tool '{ifc_tool_name}'"
                )
                return result

            # Step 5: Create ToolCreatorOutput with fixed code, preserved metadata, and modification tracking
            fixed_tool_output = ToolCreatorOutput(
                ifc_tool_name=ifc_tool_name,
                code=fixed_code_output.code,
                metadata=original_metadata,
                modification_summary=fixed_code_output.summary,
                modification_requirement=modification_requirement
            )

            # Record successful fix
            span.set_attribute("fix_ifc_tool.success", True)
            span.set_attribute("fix_ifc_tool.fixed_ifc_tool_name", ifc_tool_name)
            span.set_attribute("fix_ifc_tool.modification_summary", fixed_code_output.summary)
            span.set_attribute("fix_ifc_tool.fixed_code", fixed_code_output.code[:500] + "..." if len(fixed_code_output.code) > 500 else fixed_code_output.code)

            # Return ToolCreatorOutput directly (consistent with create_ifc_tool)
            result = AgentToolResult(
                success=True,
                agent_tool_name="fix_ifc_tool",
                result=fixed_tool_output  # ToolCreatorOutput object
            )
            print(f"ToolFix: Successfully modified IFC tool '{ifc_tool_name}' - {fixed_code_output.summary}")

            return result

        except Exception as e:
            print(f"ToolFix: IFC tool fix failed with exception - {str(e)}")
            span.set_attribute("fix_ifc_tool.success", False)
            span.set_attribute("fix_ifc_tool.error", str(e))
            result = AgentToolResult(
                success=False,
                agent_tool_name="fix_ifc_tool",
                error=f"IFC tool fix failed: {str(e)}"
            )
            return result



    def _get_tool_info(self, ifc_tool_name: str) -> Optional[Dict[str, Any]]:
        """Get original tool information, prioritizing SharedContext"""
        try:
            # First, try to get from SharedContext (recent tool creations/fixes)
            shared_context = SharedContext.get_instance()
            tool_creation_data = shared_context.get_tool_by_name(ifc_tool_name)

            if tool_creation_data:
                print(f"Found tool '{ifc_tool_name}' in SharedContext meta_tool_trace")
                # tool_creation_data is a dict from agent_history
                return {
                    "name": tool_creation_data.get('ifc_tool_name'),
                    "code": tool_creation_data.get('code'),
                    "metadata": tool_creation_data.get('metadata')
                }

        except Exception as e:
            print(f"Failed to get tool info for '{ifc_tool_name}': {e}")
            return None

    def _get_previous_modifications(self, tool_name: str) -> List[str]:
        """Extract previous modification summaries from agent_history.

        Args:
            tool_name: Name of the tool to get modification history for

        Returns:
            List of modification summaries from previous fix_ifc_tool calls
        """
        previous_mods = []

        try:
            shared_context = SharedContext.get_instance()

            for entry in shared_context.agent_history:
                # Check if this is a fix_ifc_tool action for this tool
                if (entry.get("action") == "fix_ifc_tool" and
                    entry.get("action_input", {}).get("ifc_tool_name") == tool_name):

                    # Extract summary from the result
                    result = entry.get("action_result", {})
                    if isinstance(result, dict):
                        summary = result.get("summary")
                        if summary:
                            previous_mods.append(summary)

            if previous_mods:
                print(f"Found {len(previous_mods)} previous modifications for tool '{tool_name}'")

        except Exception as e:
            print(f"Warning: Failed to get modification history for '{tool_name}': {e}")

        return previous_mods

    def fix_code(
        self,
        code: str,
        modification_requirement: str,
        check_result: Optional[IFCToolResult] = None,
        metadata: Optional[ToolMetadata] = None,
        previous_modifications: Optional[List[str]] = None
    ) -> FixedCodeOutput:
        """Fix or modify code based on specific requirements.

        Args:
            code: Current code to modify
            modification_requirement: Clear description of what needs to be changed
            check_result: Optional error information (if fixing errors)
            metadata: Tool metadata
            previous_modifications: List of previous modification summaries

        Returns:
            FixedCodeOutput with modified code and summary
        """

        system_prompt = """
        You are an expert Python developer specializing in IFC file processing and building compliance checking.
        Your task is to modify an existing Python tool based on specific requirements.

        ## MODIFICATION TYPES SUPPORTED

        1. **Error Fixing** - Fix runtime errors, exceptions, or bugs
        2. **Performance Optimization** - Improve efficiency, reduce loops, use batch operations
        3. **Output Format Adjustment** - Add/modify return value structure, add units
        4. **Feature Enhancement** - Add parameters, filtering capabilities
        5. **Code Quality Improvement** - Add validation, error handling

        ## CORE RESPONSIBILITIES
        - Implement the modification requirement exactly as described
        - If error information is provided, ensure the error is also fixed
        - Preserve existing functionality unless explicitly asked to change
        - Do NOT repeat previous modifications (check modification history)
        - Apply IFC processing best practices using ifcopenshell and utility functions

        ## CODE QUALITY REQUIREMENTS
        - Use proper imports and full type hints
        - **CRITICAL**: Do NOT import `ifcopenshell.util.*` modules - functions are pre-injected
        - Use injected ifcopenshell.util functions directly (e.g., get_psets, get_material, get_container)
        - For custom logic, import from `ifc_tool_utils.ifcopenshell`
        - Follow PEP 8 coding conventions
        - Add/maintain clear Google-style docstrings (Args / Returns / Example)
        - Validate inputs and handle edge cases gracefully
        - Write concise, readable, production-ready code in English

        ## CRITICAL EXCEPTION HANDLING POLICY
        - DO NOT use `except Exception:` or bare `except:` — these break sandbox execution
        - Do NOT wrap the entire function body in try/except
        - Only catch *specific* exceptions when absolutely necessary (e.g., `FileNotFoundError`)
        - Prefer no try/except around the main logic; let outer layers manage unexpected errors
        - When data is missing (property not found, element missing), return safe defaults (None, [], {})

        ## OUTPUT FORMAT
        Return a JSON object containing:
        - `code`: the modified Python function (complete and executable)
        - `summary`: a brief explanation of what was changed and why (1-2 sentences)"""

        # Build user prompt with all context
        user_prompt_parts = []

        # Primary modification requirement
        user_prompt_parts.append(f"""MODIFICATION REQUIREMENT (Primary Goal):
        {modification_requirement}
        """)

        # Error information (if present)
        if check_result:
            error_context = self._build_error_context(check_result)
            user_prompt_parts.append(f"""
            ERROR INFORMATION (Secondary - Also Fix This):
            - Tool Name: {check_result.ifc_tool_name}
            - Error Type: {check_result.exception_type or 'Unknown'}
            - Error Message: {check_result.error_message or 'No error message'}

            {error_context}
            """)

        # Previous modifications (to avoid repetition)
        if previous_modifications:
            mods_list = "\n".join(f"- {mod}" for mod in previous_modifications)
            user_prompt_parts.append(f"""
            PREVIOUS MODIFICATIONS (Avoid Repeating):
            {mods_list}
            """)

        # Current code
        user_prompt_parts.append(f"""
            CURRENT CODE:
            {code}
            """)

        # Tool metadata
        if metadata:
            user_prompt_parts.append(f"""
            TOOL METADATA:
            - Function Name: {metadata.ifc_tool_name}
            - Description: {metadata.description}
            - Parameters: {[param.model_dump() for param in metadata.parameters]}
            - Return Type: {metadata.return_type}
            - Category: {metadata.category}
            """)

        user_prompt = "\n".join(user_prompt_parts)

        try:
            fixed_output = self.llm_client.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_model=FixedCodeOutput,
                max_retries=3
            )

            if fixed_output is None:
                print(f"LLM returned None when attempting to fix code")
                return FixedCodeOutput(
                    code=code,
                    summary="Failed to modify code: LLM returned None"
                )

            return fixed_output

        except Exception as e:
            print(f"LLM code fixing failed: {e}")
            # Return FixedCodeOutput with original code and error summary
            return FixedCodeOutput(
                code=code,
                summary=f"Failed to modify code: {str(e)}"
            )

    def _build_error_context(self, check_result: IFCToolResult) -> str:
        """Build error-specific context for fixing"""

        context_map = {
            # Syntax errors
            "SyntaxError": "SYNTAX ERROR: Check for missing parentheses, brackets, quotes, or incorrect indentation.",
            "IndentationError": "INDENTATION ERROR: Fix inconsistent indentation, mixing tabs and spaces.",
            "TabError": "TAB ERROR: Ensure consistent use of tabs or spaces for indentation.",

            # Import errors
            "ImportError": "IMPORT ERROR: Fix import statements, check module names, or add missing dependencies.",
            "ModuleNotFoundError": "MODULE ERROR: The required module is not installed or the import path is incorrect. Consider alternative imports or add proper imports.",

            # Runtime errors
            "NameError": "NAME ERROR: The variable or function name is not defined. Check for typos or missing imports.",
            "TypeError": "TYPE ERROR: Fix type mismatches, incorrect argument types, or missing/extra arguments.",
            "AttributeError": "ATTRIBUTE ERROR: The object doesn't have the specified attribute or method. Check object type and available methods.",
            "ValueError": "VALUE ERROR: Fix invalid argument values or data conversion issues.",
            "RuntimeError": "RUNTIME ERROR: General runtime issue, check logic flow and error conditions.",

            # Logic errors
            "KeyError": "KEY ERROR: Dictionary key doesn't exist. Add key existence checks or use .get() method.",
            "IndexError": "INDEX ERROR: List/array index is out of range. Add bounds checking.",
            "AssertionError": "ASSERTION ERROR: An assertion failed. Check the assertion condition and fix the logic.",
        }

        error_type = check_result.exception_type or "Unknown"
        context = context_map.get(error_type, f"UNKNOWN ERROR ({error_type}): Analyze the error message and fix accordingly.")

        # Add traceback context if available
        if check_result.traceback:
            context += f"\n\nTRACEBACK ANALYSIS:\n{check_result.traceback[:500]}..."

        return context