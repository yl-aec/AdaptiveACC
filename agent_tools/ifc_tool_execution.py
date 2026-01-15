import json
import uuid
import traceback
from typing import Dict, List, Any, Optional
from models.common_models import AgentToolResult, IFCToolResult
from models.shared_context import SharedContext
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from utils.sandbox_executor import LocalPythonExecutor
from telemetry.tracing import trace_method
from opentelemetry import trace

class ToolExecution:
    """Skill to execute IFC tools with parameter preparation"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.tool_registry = IFCToolRegistry.get_instance()

    # Executor Interface
    @trace_method("execute_ifc_tool")
    def execute_ifc_tool(self, ifc_tool_name: str, parameters: str, execution_mode: str) -> AgentToolResult:
        """Execute an IFC tool with given parameters and mode.

        Args:
            ifc_tool_name: Name of the IFC tool to execute
            parameters: JSON string of parameters for the tool
            execution_mode: Execution mode - 'safe' for existing tools, 'sandbox' for newly created tools

        Returns:
            AgentToolResult: Success with execution results, or failure if execution failed
        """

        span = trace.get_current_span()

        try:
            # Parse LLM-provided parameters (no modification)
            try:
                params = json.loads(parameters) if parameters else {}
            except:
                params = {}

            # Record execution details
            span.set_attribute("execute_ifc_tool.tool_name", ifc_tool_name)
            span.set_attribute("execute_ifc_tool.execution_mode", execution_mode)
            span.set_attribute("execute_ifc_tool.parameters", parameters)

            print(f"ToolExecutor: Executing IFC tool '{ifc_tool_name}' in {execution_mode} mode with {len(params)} parameters")

            # Execute based on mode
            if execution_mode == "sandbox":
                execution_result = self.execute_in_sandbox(ifc_tool_name, params)
            else:
                execution_result = self.execute_in_tool_registry(ifc_tool_name, params)

            # Record execution result
            span.set_attribute("execute_ifc_tool.success", execution_result.success)
            span.set_attribute("execute_ifc_tool.result", str(execution_result))

            result = AgentToolResult(
                success=execution_result.success,
                agent_tool_name="execute_ifc_tool",
                result=execution_result  # Directly embed IFCToolResult
            )

            return result

        except Exception as e:
            span.set_attribute("execute_ifc_tool.success", False)
            span.set_attribute("execute_ifc_tool.error", str(e))
            result = AgentToolResult(
                success=False,
                agent_tool_name="execute_ifc_tool",
                error=f"IFC tool execution failed: {str(e)}"
            )
            return result


    def execute_in_tool_registry(self, tool_name: str, parameters: Dict[str, Any]) -> IFCToolResult:

        try:
            # Auto-inject ifc_file_path if missing
            if "ifc_file_path" not in parameters:
                ifc_file_path = self.shared_context.session_info.get("ifc_file_path")
                if ifc_file_path:
                    parameters["ifc_file_path"] = ifc_file_path
                    print(f"[Auto-inject] Added ifc_file_path: {ifc_file_path}")

            # Check if tool exists
            if tool_name not in self.tool_registry.get_available_tools():
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' not found in tool registry",
                    tool_source="existing"
                )

            # Construct standard tool call format for DomainToolRegistry
            tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
            tool_call = {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(parameters)
                }
            }

            # Execute using DomainToolRegistry's native execute_tool_calls method
            print(f"Executing tool '{tool_name}' with parameters: {list(parameters.keys())}")
            tool_responses = self.tool_registry.execute_tool_calls([tool_call])

            if tool_call_id in tool_responses:
                result = tool_responses[tool_call_id]

                return IFCToolResult(
                    success=True,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    result=result,
                    tool_source="existing"  # Tool from registry = pre-existing
                )
            else:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool execution returned no result for '{tool_name}'",
                    tool_source="existing"
                )

        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Tool execution failed: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc(),
                tool_source="existing"
            )

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any], metadata: Dict) -> tuple[bool, str]:
        """
        Validate parameters against tool metadata.
        Returns (is_valid, error_message)
        """
        if not metadata or not isinstance(metadata, dict):
            # No metadata available, skip validation
            return True, ""

        param_specs = metadata.get('parameters', [])
        if not param_specs:
            # No parameter specifications, skip validation
            return True, ""

        # Build a map of parameter specs
        spec_map = {}
        for spec in param_specs:
            param_name = spec.get('name')
            if param_name:
                spec_map[param_name] = spec

        # Check for missing required parameters
        missing_params = []
        for param_name, spec in spec_map.items():
            if spec.get('required', True) and param_name not in parameters:
                missing_params.append(f"{param_name} ({spec.get('type', 'Any')})")

        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"

        # Check for unexpected parameters (warning only, not an error)
        unexpected_params = [p for p in parameters.keys() if p not in spec_map]
        if unexpected_params:
            print(f"Warning: Unexpected parameters for tool '{tool_name}': {', '.join(unexpected_params)}")

        return True, ""

    def execute_in_sandbox(self, tool_name: str, parameters: Dict[str, Any]) -> IFCToolResult:
        """Execute tool in sandbox environment for newly created tools"""
        try:
            # Auto-inject ifc_file_path if missing
            if "ifc_file_path" not in parameters:
                ifc_file_path = self.shared_context.session_info.get("ifc_file_path")
                if ifc_file_path:
                    parameters["ifc_file_path"] = ifc_file_path
                    print(f"[Auto-inject] Added ifc_file_path: {ifc_file_path}")

            # Get tool code from SharedContext
            shared_context = SharedContext.get_instance()
            tool_result = shared_context.get_tool_by_name(tool_name)

            if not tool_result:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' source code not found in SharedContext",
                    tool_source="created"
                )

            # Handle both dict and object formats (tool_result may be serialized as dict)
            if isinstance(tool_result, dict):
                code = tool_result.get('code')
                metadata = tool_result.get('metadata', {})
            else:
                code = tool_result.code
                metadata = tool_result.metadata

            if not code:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Tool '{tool_name}' has no code in SharedContext",
                    tool_source="created"
                )

            # Validate parameters against metadata
            is_valid, error_msg = self._validate_parameters(tool_name, parameters, metadata)
            if not is_valid:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Parameter validation failed: {error_msg}",
                    tool_source="created"
                )

            # Create sandbox executor and execute directly
            sandbox = LocalPythonExecutor()
            result = sandbox.execute_function_with_args(
                code=code,
                function_name=tool_name,
                kwargs=parameters
            )

            if result.success:
                # Parse the output to extract the actual return value
                try:
                    import ast
                    parsed_result = ast.literal_eval(result.output.strip())
                except:
                    parsed_result = result.output.strip()

                return IFCToolResult(
                    success=True,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    result=parsed_result,
                    tool_source="created"  # Tool from sandbox = created in current session
                )
            else:
                return IFCToolResult(
                    success=False,
                    ifc_tool_name=tool_name,
                    parameters_used=parameters,
                    error_message=f"Sandbox execution failed: {result.error}",
                    tool_source="created"
                )

        except Exception as e:
            return IFCToolResult(
                success=False,
                ifc_tool_name=tool_name,
                parameters_used=parameters,
                error_message=f"Sandbox execution error: {str(e)}",
                exception_type=type(e).__name__,
                traceback=traceback.format_exc(),
                tool_source="created"
            )
