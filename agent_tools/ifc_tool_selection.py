import json
from typing import Dict, List, Any, Optional
from utils.llm_client import LLMClient
from models.common_models import AgentToolResult
from models.shared_context import SharedContext
from ifc_tools.ifc_tool_registry import IFCToolRegistry
from telemetry.tracing import trace_method
from opentelemetry import trace

class ToolSelection:
    """Skill to select the best tool for a given step using two-phase approach"""

    def __init__(self):
        self.tool_registry = IFCToolRegistry.get_instance()
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()
    
    # executor Interface
    @trace_method("select_ifc_tool")
    def select_ifc_tool(self, task_description: str) -> AgentToolResult:
        """Find the best existing IFC tool using semantic search + LLM reasoning.

        Args:
            task_description: Description of what needs to be done

        Returns:
            AgentToolResult: Success with selected tool info, or failure if no suitable tool found
        """

        span = trace.get_current_span()

        try:
            # Validate task description
            if not task_description:
                raise ValueError("No task description provided")

            # Record task information
            span.set_attribute("select_ifc_tool.task_description", task_description)
            print(f"ToolSelector: Starting IFC tool selection for '{task_description[:50]}...'")

            # Phase 1: Semantic search
            relevant_tools_metadata = self.semantic_search_tools(task_description, k=5)
            span.set_attribute("semantic_search.tools_found", len(relevant_tools_metadata))

            if not relevant_tools_metadata:
                print("No tools found in semantic search")
                span.set_attribute("select_ifc_tool.success", False)
                span.set_attribute("select_ifc_tool.error", "No tools found in semantic search")
                return AgentToolResult(
                    success=False,
                    agent_tool_name="select_ifc_tool",
                    error="No tools found in semantic search"
                )

            print(f"Phase 1 complete: {len(relevant_tools_metadata)} candidate tools")

            # Phase 2: LLM generative selection using metadata directly
            selected_tool = self.generative_tool_selection(task_description, relevant_tools_metadata)

            if selected_tool:
                tool_name = selected_tool.get('ifc_tool_name', 'unknown')
                print(f"Phase 2 complete: Selected '{tool_name}'")
                span.set_attribute("select_ifc_tool.success", True)
                span.set_attribute("select_ifc_tool.selected_tool_name", tool_name)
                span.set_attribute("select_ifc_tool.final_result", str(selected_tool))

                result = AgentToolResult(
                    success=True,
                    agent_tool_name="select_ifc_tool",
                    result=selected_tool
                )
                return result
            else:
                print("Phase 2 complete: No suitable tool selected")
                span.set_attribute("select_ifc_tool.success", False)
                span.set_attribute("select_ifc_tool.error", "No suitable tool found for the given step")
                return AgentToolResult(
                    success=False,
                    agent_tool_name="select_ifc_tool",
                    error="No suitable tool found for the given step"
                )

        except Exception as e:
            return AgentToolResult(
                success=False,
                agent_tool_name="select_ifc_tool",
                error=f"IFC tool selection failed: {str(e)}"
            )
 

    def semantic_search_tools(self, task_description: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant tools using semantic search.

        Args:
            task_description: Description of the task
            k: Number of results to return

        Returns:
            List of tool metadata dictionaries
        """
        try:
            # Get singleton vector database instance
            from utils.rag_tool import ToolVectorManager
            tool_vector_db = ToolVectorManager.get_instance()

            if not tool_vector_db.is_available():
                print("Warning: Tool vector database not available, returning empty list")
                return []

            # Execute semantic search
            # Use score_threshold=2.0 to be more permissive (allow more candidates for LLM selection phase)
            relevant_tools = tool_vector_db.search_tools(
                task_description,
                k=k,
                score_threshold=2.0
            )

            # Track if results were filtered by threshold
            threshold_filtered = len(relevant_tools) < k

            # Improved logging
            if len(relevant_tools) < k and threshold_filtered:
                print(f"Found {len(relevant_tools)} relevant tools (threshold filtered) for: '{task_description[:50]}...'")
            else:
                print(f"Found {len(relevant_tools)} relevant tools for: '{task_description[:50]}...'")

            return relevant_tools
        except Exception as e:
            print(f"Error in semantic tool search: {e}")
            return []
    
    
    def generative_tool_selection(self, task_description: str, candidate_tools: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use LLM to select the best tool from candidates based on task description.

        Args:
            task_description: Description of the task
            candidate_tools: List of candidate tool metadata

        Returns:
            Selected tool metadata dictionary, or None if no suitable tool
        """
        if not candidate_tools:
            return None

        # Build detailed prompt with tool information
        tools_info = self._format_tools_for_selection(candidate_tools)

        # System prompt: role and rules
        system_prompt = """You are an intelligent tool selection agent specialized in building compliance checking workflows.

        Your task is to select the most appropriate tool for executing a given task based on:
        1. **Relevance**: How well does the tool match the task requirements?
        2. **Parameters**: Does the tool have the right parameters for the task?
        3. **Output**: Will the tool produce the expected output?

        IMPORTANT: Return only the exact tool name from the available tools list. If no tool is suitable, return "null"."""

        # User prompt: specific data
        user_prompt = f"""
        ## Task to Execute
        {task_description}

        ## Available Tools
        {tools_info}

        Select the best tool:"""

        try:
            # Record LLM call context
            span = trace.get_current_span()
            span.set_attribute("llm_call.purpose", "select_ifc_tool")

            response = self.llm_client.generate_response(user_prompt, system_prompt=system_prompt)

            # Check if LLM returned None
            if response is None:
                print(f"LLM returned None when selecting IFC tool")
                span.set_attribute("llm_selection.failed_response", "None")
                return None

            # Record complete LLM response
            span.set_attribute("llm_response.full_content", str(response))

            # Clean and extract tool name
            selected_tool_name = response.strip().strip('"').strip()

            if selected_tool_name and selected_tool_name.lower() != "null":
                # Find the selected tool metadata
                for tool_metadata in candidate_tools:
                    if tool_metadata.get('ifc_tool_name') == selected_tool_name:
                        span.set_attribute("llm_selection.selected_tool", selected_tool_name)
                        return tool_metadata

            print(f"LLM could not select a suitable tool or returned: {selected_tool_name}")
            span.set_attribute("llm_selection.failed_response", selected_tool_name)
            return None

        except Exception as e:
            print(f"Error in generative tool selection: {e}")
            span.set_attribute("llm_selection.error", str(e))
            return None
    
   
    def _format_tools_for_selection(self, tools: List[Dict[str, Any]]) -> str:
        """Format tool metadata for LLM selection prompt"""
        formatted_tools = []

        for i, tool in enumerate(tools, 1):
            name = tool.get('ifc_tool_name', 'unknown')
            description = tool.get('description', 'No description')
            parameters = tool.get('parameters', '')

            # Format parameters (already a string from metadata)
            params_str = f"  Parameters: {parameters}" if parameters else "  No parameters"

            formatted_tools.append(f"""
                {i}. **{name}**
                Description: {description}
                {params_str}""")

        return "\n".join(formatted_tools)


