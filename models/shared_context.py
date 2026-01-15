
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field
from utils.base_classes import Singleton
from models.common_models import AgentToolResult, IFCToolResult, ComplianceEvaluationModel, RegulationInterpretation

class SharedContext(Singleton, BaseModel):
    """Singleton shared context for multi-agent collaboration (ReAct architecture)"""

    # Core session information (immutable during execution)
    session_info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Core session information: session_id, regulation_text, ifc_file_path, interpretation, etc."
    )

    subgoals: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Current subgoals being worked on"
    )

    # ReAct iteration history (includes thoughts, actions, results, and active_subgoal_id)
    agent_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Complete ReAct iteration history from ComplianceAgent"
    )

    # Compliance evaluation result (final assessment)
    compliance_result: Optional[ComplianceEvaluationModel] = Field(
        None,
        description="Final compliance evaluation result from Checker"
    )


    def _initialize(self):
        """Initialize SharedContext singleton instance"""
        # Initialize Pydantic BaseModel with default values
        super(BaseModel, self).__init__()
        BaseModel.__init__(self)
        print("SharedContext: Singleton instance initialized")

    def initialize_session(self, session_id: str, regulation_text: str, ifc_file_path: str) -> None:
        """Initialize session information and reset state for new session"""
        self.session_info = {
            "session_id": session_id,
            "regulation_text": regulation_text,
            "ifc_file_path": ifc_file_path,
        }
        # Reset session state
        self.subgoals = []
        self.agent_history = []
        self.compliance_result = None

    # === agent_history filtering and query methods ===

    def get_successful_ifc_tool_executions(self) -> List[Dict[str, Any]]:
        """Get all successful IFC tool execution entries from agent_history."""
        return [
            entry for entry in self.agent_history
            if (entry.get('action') == 'execute_ifc_tool' and
                entry.get('action_result', {}).get('success'))
        ]

    def get_tool_by_name(self, tool_name: str) -> Any:
        """Get the most recent successful tool creation or fix result by tool name.

        Args:
            tool_name: Name of the IFC tool to find

        Returns:
            ToolCreatorOutput object (or dict representation) if found, None otherwise.
            Both create_ifc_tool and fix_ifc_tool return ToolCreatorOutput for consistency.
        """
        # Traverse agent_history in reverse (most recent first)
        for entry in reversed(self.agent_history):
            action = entry.get('action')
            action_result = entry.get('action_result', {})

            # Check if this is a successful create_ifc_tool or fix_ifc_tool action
            if (action in ['create_ifc_tool', 'fix_ifc_tool'] and
                action_result.get('success')):

                result = action_result.get('result')
                if result and result.get('ifc_tool_name') == tool_name:
                    return result

        return None

    def get_error_info_from_context(self, tool_name: str = "") -> Optional[IFCToolResult]:
        """Get error information from agent_history for failed IFC tool executions.

        Args:
            tool_name: Name of the IFC tool to find error for (optional)

        Returns:
            IFCToolResult with error information if found, None otherwise
        """
        try:
            # Traverse agent_history in reverse (most recent first)
            for entry in reversed(self.agent_history):
                action = entry.get('action')
                action_result = entry.get('action_result', {})

                # Check if this is a failed execute_ifc_tool action
                if (action == 'execute_ifc_tool' and
                    not action_result.get('success')):

                    result = action_result.get('result', {})

                    # Match tool name if specified
                    if not tool_name or result.get('ifc_tool_name') == tool_name:
                        return result

            # No matching failure found
            msg = f"No failed execution found for tool '{tool_name}'" if tool_name \
                else "No failed tool executions found"
            print(msg)
            return None

        except Exception as e:
            print(f"Error getting error info from context: {e}")
            return None

    # === Formatting methods for LLM consumption ===

    def format_successful_executions_summary(self, max_per_subgoal: int = 2) -> str:
        """Format successful IFC tool executions grouped by subgoal.

        Args:
            max_per_subgoal: Maximum number of executions to show per subgoal

        Returns:
            Formatted string suitable for LLM consumption
        """
        successful_executions = self.get_successful_ifc_tool_executions()

        if not successful_executions:
            return "## Data Collected: None yet"

        # Group by subgoal
        evidence_by_subgoal = {}
        for entry in successful_executions:
            subgoal_id = entry.get('active_subgoal_id', 'unassigned')
            if subgoal_id not in evidence_by_subgoal:
                evidence_by_subgoal[subgoal_id] = []
            evidence_by_subgoal[subgoal_id].append(entry)

        # Format output
        lines = ["## Data Collected by Subgoal"]
        for subgoal_id, entries in evidence_by_subgoal.items():
            lines.append(f"\nSubgoal {subgoal_id}: {len(entries)} successful executions")
            for entry in entries[:max_per_subgoal]:
                result = entry['action_result'].get('result', {})
                tool_name = result.get('ifc_tool_name', 'unknown')
                iter_num = entry.get('iteration')
                lines.append(f"  - Iter {iter_num}: {tool_name}")

            if len(entries) > max_per_subgoal:
                lines.append(f"  ... and {len(entries) - max_per_subgoal} more")

        return "\n".join(lines)

    def format_complete_history(self) -> str:
        """Format complete agent_history without filtering or truncation.

        Returns:
            Formatted string with all iteration history including full thoughts, actions, and results
        """
        if not self.agent_history:
            return "## Complete History: No actions yet"

        lines = ["## Complete Agent History"]

        for entry in self.agent_history:
            iter_num = entry.get('iteration')
            thought = entry.get('thought', '')
            action = entry.get('action', '')
            action_input = entry.get('action_input')
            action_result = entry.get('action_result', {})
            active_subgoal_id = entry.get('active_subgoal_id')

            status_icon = "✓" if action_result.get('success') else "✗"

            # Build iteration header
            subgoal_info = f" [Subgoal {active_subgoal_id}]" if active_subgoal_id is not None else ""
            lines.append(f"\n### Iteration {iter_num}{subgoal_info}")

            # Add full thought if present
            if thought:
                lines.append(f"Thought: {thought}")

            # Add action and status
            lines.append(f"{status_icon} Action: {action}")

            # Add full action input - use JSON for dicts, str for others
            if action_input:
                if isinstance(action_input, dict):
                    try:
                        input_json = json.dumps(action_input, indent=2, ensure_ascii=False)
                        lines.append(f"  Input:")
                        for line in input_json.split('\n'):
                            lines.append(f"    {line}")
                    except:
                        lines.append(f"  Input: {str(action_input)}")
                else:
                    lines.append(f"  Input: {str(action_input)}")

            # Add full action_result - show complete JSON for complete transparency
            # This ensures LLM sees ALL information without any filtering or summarization
            try:
                result_json = json.dumps(action_result, indent=2, ensure_ascii=False)
                lines.append(f"  Action Result:")
                for line in result_json.split('\n'):
                    lines.append(f"    {line}")
            except:
                # Fallback to str if JSON serialization fails
                lines.append(f"  Action Result: {str(action_result)}")

        return "\n".join(lines)


# === Shared formatter for regulation interpretation ===

def format_interpretation(interpretation: RegulationInterpretation) -> Dict[str, str]:
    """Return formatted interpretation and required-data sections for prompts."""
    term_clarifications_text = ""
    for tc in interpretation.term_clarifications:
        examples = ", ".join(tc.examples) if getattr(tc, "examples", None) else ""
        notes = getattr(tc, "notes", None)
        reasoning = getattr(tc, "reasoning_approach", None)  # Optional field

        term_clarifications_text += f"  - {tc.term}: {tc.meaning}\n"
        if examples:
            term_clarifications_text += f"    • Examples: {examples}\n"
        if notes:
            term_clarifications_text += f"    • Notes: {notes}\n"
        if reasoning:
            term_clarifications_text += f"    • Reasoning: {reasoning}\n"

    implicit_requirements_text = "\n".join(
        [f"  - {item}" for item in interpretation.implicit_requirements]
    )
    misunderstandings_text = "\n".join(
        [f"  - {m}" for m in interpretation.common_misunderstandings]
    )

    required_data_text = ""
    if interpretation.required_data:
        required_data_text = "\n## Required Data for Compliance Checking:\n"
        for data in interpretation.required_data:
            required_data_text += f"\n**{data.data_name}** ({', '.join(data.element_types)})\n"
            required_data_text += f"  - Description: {data.description}\n"
            sources = ", ".join(getattr(data, "source_candidates", []) or [])
            required_data_text += f"  - Source candidates: {sources if sources else 'n/a'}\n"
            required_data_text += f"  - Suggested mapping: {data.suggested_mapping}\n"
            if getattr(data, "derivation_hints", None):
                required_data_text += f"  - Derivation hints: {', '.join(data.derivation_hints)}\n"

    interpretation_section = f"""
## Regulation Interpretation:
Plain Language:
{interpretation.plain_language}

Key Terms:
{term_clarifications_text if term_clarifications_text else "  (none)"}

Implicit Requirements:
{implicit_requirements_text if implicit_requirements_text else "  (none)"}

Common Misunderstandings to Avoid:
{misunderstandings_text if misunderstandings_text else "  (none)"}
"""

    return {
        "interpretation_section": interpretation_section,
        "required_data_section": required_data_text,
    }
