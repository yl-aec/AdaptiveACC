
import uuid
import threading
from typing import Dict, List, Any, Optional, Callable
from config import Config
from utils.llm_client import LLMClient
from agent_tools.agent_tool_registry import AgentToolRegistry
from agent_tools.ifc_tool_selection import ToolSelection
from agent_tools.ifc_tool_execution import ToolExecution
from agent_tools.ifc_tool_storage import ToolStorage
from agent_tools.ifc_tool_fix import ToolFix
from agent_tools.ifc_tool_creation import ToolCreation
from agent_tools.subgoal_management import SubgoalManagement
from agent_tools.compliance_report import ComplianceReport
from models.common_models import (
    AgentResult,
    AgentToolResult,
    SubgoalModel,
    SubgoalSetModel,
    ComplianceEvaluationModel,
    ReActIterationOutput
)
from models.shared_context import SharedContext, format_interpretation
from telemetry.tracing import trace_method


class ComplianceAgent:
    """Main agent for compliance checking using ReAct framework with 8 agent tools"""

    def __init__(
        self,
        iteration_callback: Optional[Callable] = None,
        api_key: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None
    ):
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.llm_client = LLMClient(api_key=self.api_key)
        self.shared_context = SharedContext.get_instance()
        self.agent_tool_registry = AgentToolRegistry.get_instance()
        self.iteration_callback = iteration_callback
        self.cancel_event = cancel_event

        # Register agent tools
        self._register_required_tools()
        print(f"ComplianceAgent: Initialized with {len(self.agent_tool_registry.get_available_tools())} agent tools")
        print(f"ComplianceAgent: Using {Config.OPENAI_MODEL_NAME} for ReAct reasoning (Pydantic structured output)")

    def _register_required_tools(self):
        """Register all 8 agent tools for compliance checking workflow"""
        subgoal_management = SubgoalManagement()
        compliance_report = ComplianceReport()

        tools_to_register = [
            # Core 5 agent tools for IFC tool lifecycle
            ToolSelection().select_ifc_tool,
            ToolCreation().create_ifc_tool,
            ToolExecution().execute_ifc_tool,
            ToolStorage().store_ifc_tool,
            ToolFix().fix_ifc_tool,
            # Subgoal management (2 tools)
            subgoal_management.generate_subgoals,
            subgoal_management.review_and_update_subgoals,
            # Compliance report generation (1 tool) - merged judgment + report in one call
            compliance_report.generate_compliance_report,
        ]

        for tool_func in tools_to_register:
            try:
                self.agent_tool_registry.register(tool_func)
            except Exception as e:
                print(f"Failed to register agent tool {tool_func.__name__}: {e}")


    # === Main Interface ===

    def _extract_span_id(self) -> Optional[str]:
        """Extract current Phoenix trace span ID"""
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                return format(span.get_span_context().span_id, '016x')
        except Exception as e:
            print(f"[WARNING] Failed to extract span_id: {e}")
        return None

    @trace_method("compliance_check")
    def execute_compliance_check(
        self,
        regulation_text: str,
        ifc_file_path: str,
        max_iterations: int = 50,
        sample_id: Optional[str] = None,
        regulation_id: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> AgentResult:
        """Execute complete compliance checking using ReAct framework

        Args:
            regulation_text: Building regulation to check
            ifc_file_path: Path to IFC file
            max_iterations: Maximum ReAct iterations
            sample_id: Optional sample identifier for tracing
            regulation_id: Optional regulation identifier for tracing
            model_id: Optional model identifier for tracing

        Returns:
            AgentResult with compliance report
        """

        # 1. Initialize session (also resets subgoals and agent_history)
        session_id = str(uuid.uuid4())[:8]
        print(f"\nComplianceAgent: Session {session_id} initialized")
        self.shared_context.initialize_session(session_id, regulation_text, ifc_file_path)
        if self.api_key:
            self.shared_context.session_info["api_key_override"] = self.api_key
        else:
            self.shared_context.session_info.pop("api_key_override", None)
        self.shared_context.session_info.pop("last_llm_error", None)
        self.shared_context.session_info.pop("last_llm_error_is_quota", None)
        if self._is_cancelled():
            return AgentResult(
                status="cancelled",
                iterations_used=0,
                agent_history=self.shared_context.agent_history,
                error="Cancelled by user",
                span_id=self._extract_span_id()
            )

        # Store sample metadata in SharedContext for potential use
        if sample_id:
            self.shared_context.session_info['sample_id'] = sample_id
        if regulation_id:
            self.shared_context.session_info['regulation_id'] = regulation_id
        if model_id:
            self.shared_context.session_info['model_id'] = model_id

        # Add Phoenix span attributes and input for tracing
        if sample_id or regulation_id or model_id:
            try:
                from opentelemetry import trace
                from openinference.semconv.trace import SpanAttributes

                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    # Set span attributes
                    if sample_id:
                        span.set_attribute("sample.id", sample_id)
                    if regulation_id:
                        span.set_attribute("sample.regulation_id", regulation_id)
                    if model_id:
                        span.set_attribute("sample.model_id", model_id)

                    # Set input value (only sample_id for Phoenix UI)
                    if sample_id:
                        span.set_attribute(SpanAttributes.INPUT_VALUE, sample_id)
                        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")
                        print(f"[Phoenix] Set span input: {sample_id}")

                    print(f"[Phoenix] Set span attributes: sample_id={sample_id}, regulation_id={regulation_id}, model_id={model_id}")
            except Exception as e:
                print(f"[WARNING] Failed to set Phoenix span attributes/input: {e}")

        # 2. Run ReAct loop (state managed in SharedContext)
        print(f"\nStarting ReAct loop (max {max_iterations} valid iterations)...")
        iteration = 0
        retry_count = 0
        max_empty_retries = 10  

        while iteration < max_iterations:
            if self._is_cancelled():
                return AgentResult(
                    status="cancelled",
                    iterations_used=iteration,
                    agent_history=self.shared_context.agent_history,
                    error="Cancelled by user",
                    span_id=self._extract_span_id()
                )
            print(f"\n{'='*60}")
            print(f"ReAct Iteration {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")

            result = self._run_react_iteration(iteration)

            # Check if this was an empty iteration (no tool calls)
            if result == "empty_iteration":
                retry_count += 1
                print(f"[WARNING] Empty iteration detected (retry {retry_count}/{max_empty_retries})")

                if retry_count >= max_empty_retries:
                    print(f"[ERROR] {max_empty_retries} consecutive empty iterations - failing")
                    last_llm_error = self.shared_context.session_info.get("last_llm_error")
                    error_message = last_llm_error or f"LLM stopped calling tools after {max_empty_retries} attempts"
                    quota_error = self.shared_context.session_info.get("last_llm_error_is_quota")
                    api_key_override = self.shared_context.session_info.get("api_key_override")
                    if quota_error and not api_key_override:
                        error_message = (
                            "System API credits are insufficient. Please enable 'Use my API key' and try again."
                        )
                        if last_llm_error:
                            error_message = f"{error_message} Details: {last_llm_error}"
                    return AgentResult(
                        status="failed",
                        iterations_used=iteration,
                        agent_history=self.shared_context.agent_history,
                        error=error_message,
                        span_id=self._extract_span_id()
                    )
                continue  # Retry without incrementing iteration

            # Reset retry count on successful iteration
            retry_count = 0
            iteration += 1

            if result:  # Task completed or failed
                return result

            if self._is_cancelled():
                return AgentResult(
                    status="cancelled",
                    iterations_used=iteration,
                    agent_history=self.shared_context.agent_history,
                    error="Cancelled by user",
                    span_id=self._extract_span_id()
                )

        # 3. Handle timeout
        print(f"\n[WARNING] Exceeded maximum iterations ({max_iterations})")
        return AgentResult(
            status="timeout",
            iterations_used=max_iterations,
            agent_history=self.shared_context.agent_history,
            error=f"Exceeded maximum iterations ({max_iterations})",
            span_id=self._extract_span_id()
        )

    def _is_cancelled(self) -> bool:
        return bool(self.cancel_event and self.cancel_event.is_set())


    # === Core ReAct Logic ===

    def _run_react_iteration(self, iteration: int) -> Optional[AgentResult]:
        """Run a single ReAct iteration"""

        # Get LLM's structured response (Pydantic model)
        react_output = self._get_react_response()

        # Check if response is None (LLM failure)
        if react_output is None:
            print(f"[ERROR] LLM returned None response")
            return "empty_iteration"

        # Extract fields from Pydantic model
        thought_content = react_output.thought
        action_name = react_output.action
        action_input = react_output.action_input

        # Validate action is not empty
        if not action_name or not action_name.strip():
            print(f"[WARNING] LLM returned empty action")
            return "empty_iteration"

        # Get current active subgoal ID
        active_subgoal_id = None
        if self.shared_context.subgoals:
            for sg_dict in self.shared_context.subgoals:
                if sg_dict.get('status') == "in_progress":
                    active_subgoal_id = sg_dict.get('id')
                    break

        # Send iteration start update (before executing action)
        if self.iteration_callback:
            try:
                self.iteration_callback({
                    "type": "iteration_started",
                    "iteration": iteration + 1,
                    "active_subgoal_id": active_subgoal_id,
                    "thought": thought_content,
                    "action": action_name,
                    "action_input": action_input
                })
            except Exception as e:
                print(f"[WARNING] Iteration start callback failed: {e}")

        # Execute action
        action_result = self._execute_action(action_name, action_input)

        # Record complete iteration entry to history
        iteration_entry = {
            "iteration": iteration + 1,
            "active_subgoal_id": active_subgoal_id,
            "thought": thought_content,
            "action": action_name,
            "action_input": action_input,
            "action_result": action_result.model_dump()
        }
        self.shared_context.agent_history.append(iteration_entry)

        # Send iteration completed update (after executing action)
        if self.iteration_callback:
            try:
                self.iteration_callback({
                    "type": "iteration_completed",
                    "iteration": iteration + 1,
                    "action_result": action_result.model_dump()
                })
            except Exception as e:
                print(f"[WARNING] Iteration completed callback failed: {e}")

        print(iteration_entry)

        # Check if agent called generate_compliance_report (signals completion)
        if action_result.agent_tool_name == 'generate_compliance_report':
            num_executions = len(self.shared_context.get_successful_ifc_tool_executions())
            print(f"\n[OK] Agent called generate_compliance_report - {num_executions} successful IFC tool executions")

            if action_result.success and action_result.result:
                print(f"[OK] Compliance report generated - {action_result.result.overall_status}")
                return AgentResult(
                    status="success",
                    iterations_used=iteration + 1,
                    agent_history=self.shared_context.agent_history,
                    compliance_result=action_result.result,
                    span_id=self._extract_span_id()
                )
            else:
                error_msg = action_result.error or 'Unknown error'
                print(f"[ERROR] Compliance report generation failed: {error_msg}")
                return AgentResult(
                    status="failed",
                    iterations_used=iteration + 1,
                    agent_history=self.shared_context.agent_history,
                    error=f"Compliance report generation failed: {error_msg}",
                    span_id=self._extract_span_id()
                )

        # Special handling for subgoal management tools
        if action_result.success and action_name in ["generate_subgoals", "review_and_update_subgoals"]:
            # Update SharedContext with new subgoals
            updated_subgoals = action_result.result
            if isinstance(updated_subgoals, SubgoalSetModel):
                # Store as list of dicts for easy access by agent tools
                self.shared_context.subgoals = [sg.model_dump() for sg in updated_subgoals.subgoals]

                # Send real-time subgoal update via callback (for WebSocket)
                if self.iteration_callback:
                    try:
                        self.iteration_callback({
                            "type": "subgoal_update",
                            "subgoals": self.shared_context.subgoals
                        })
                    except Exception as e:
                        print(f"[WARNING] Subgoal callback failed: {e}")

                print(f"[SUBGOALS UPDATED] {len(updated_subgoals.subgoals)} subgoals")
                for sg in updated_subgoals.subgoals:
                    print(f"  {sg.id}. [{sg.status}] {sg.description}")

        # Continue to next iteration
        return None

    def _format_tools_for_prompt(self, tools_schema: list) -> str:
        """Format tool schemas into human-readable text for system prompt

        Args:
            tools_schema: List of tool schemas in OpenAI function calling format

        Returns:
            Formatted string describing all tools and their parameters
        """
        if not tools_schema:
            return "No tools available"

        lines = []
        for tool in tools_schema:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            description = func.get("description", "No description")
            params = func.get("parameters", {})
            properties = params.get("properties", {})
            required = params.get("required", [])

            lines.append(f"### {name}")
            lines.append(f"{description}")

            # Format parameters
            if properties:
                lines.append("Parameters:")
                for param_name, param_info in properties.items():
                    param_type = param_info.get("type", "any")
                    param_desc = param_info.get("description", "")
                    is_required = "required" if param_name in required else "optional"
                    lines.append(f"  - {param_name} ({param_type}, {is_required}): {param_desc}")
            else:
                lines.append("Parameters: none")

            lines.append("")  # Empty line between tools

        return "\n".join(lines)

    def _get_react_response(self) -> ReActIterationOutput:
        """Get LLM's ReAct response for current iteration"""

        # Get regulation context (always needed)
        regulation_text = self.shared_context.session_info.get("regulation_text", "")
        ifc_file_path = self.shared_context.session_info.get("ifc_file_path", "")

        # Get regulation interpretation if available (generated during generate_subgoals)
        regulation_interpretation = self.shared_context.session_info.get("interpretation")

        # Format interpretation if available
        interpretation_section = ""
        if regulation_interpretation:
            # Key terms (condensed: term=meaning only)
            key_terms_text = ""
            if regulation_interpretation.term_clarifications:
                terms = [f"{tc.term}={tc.meaning}" for tc in regulation_interpretation.term_clarifications]
                key_terms_text = f"\nKey Terms: {'; '.join(terms)}"

            # Evaluation scope (if specified)
            eval_scope_text = ""
            if hasattr(regulation_interpretation, 'evaluation_scope') and regulation_interpretation.evaluation_scope:
                scope = regulation_interpretation.evaluation_scope
                eval_scope_text = f"\nEvaluation Scope:\n"
                eval_scope_text += f"  - Collect data from: {', '.join(scope.data_collection_elements)}\n"
                eval_scope_text += f"  - Report components at: {scope.reporting_component_type}\n"
                eval_scope_text += f"  - Rationale: {scope.grouping_rationale}\n"

            # Implicit requirements
            implicit_req_text = ""
            if regulation_interpretation.implicit_requirements:
                implicit_req_text = "\nImplicit Requirements:\n" + "\n".join(
                    [f"  - {item}" for item in regulation_interpretation.implicit_requirements]
                )

            # Required data (full version with description and derivation_hints)
            required_data_text = ""
            if regulation_interpretation.required_data:
                required_data_text = "\nRequired Data:\n"
                for data in regulation_interpretation.required_data:
                    required_data_text += f"  - **{data.data_name}** ({', '.join(data.element_types)})\n"
                    required_data_text += f"    Description: {data.description}\n"
                    sources = ", ".join(getattr(data, "source_candidates", []) or [])
                    required_data_text += f"    Sources: {sources if sources else 'n/a'}\n"
                    mapping = data.suggested_mapping or "n/a"
                    required_data_text += f"    Mapping: {mapping}\n"
                    if getattr(data, "derivation_hints", None):
                        hints = "; ".join(data.derivation_hints)
                        required_data_text += f"    Hints: {hints}\n"

            interpretation_section = f"""
        ## Regulation Interpretation:
        {regulation_interpretation.plain_language}
        {eval_scope_text}
        {key_terms_text}
        {implicit_req_text}
        {required_data_text}
        """

        # Get current subgoals for display
        current_subgoals = self.shared_context.subgoals

        # Format subgoals section if available
        subgoals_section = ""
        if current_subgoals:
            subgoal_lines = []
            for sg in current_subgoals:
                subgoal_lines.append(f"  {sg['id']}. [{sg['status']}] {sg['description']}")

            subgoals_section = f"""
        ## Current Subgoals:
        {chr(10).join(subgoal_lines)}
        """

        # Using complete unfiltered history
        complete_history = self.shared_context.format_complete_history()

        # Get and format agent tool schemas for LLM
        tools_schema = self.agent_tool_registry.get_tools_json()
        tools_description = self._format_tools_for_prompt(tools_schema)

        system_prompt = f"""
        You are an intelligent building compliance checker operating under the ReAct (Reasoning and Acting) framework.  
        Your purpose is to determine whether an IFC model complies with a regulation by iteratively reasoning, collecting evidence, and evaluating results.
        ───────────────────────────────────────────────────────────
        ## ReAct Framework Process
        For each iteration, return a structured response with three fields:

        1. **thought**  
        Your reasoning about the current situation. Analyze based on:  
        - Regulation requirements  
        - Current and pending subgoals  
        - Recent results and context  
        - Missing information  
        Explain *why* this action is needed and *what data* you intend to obtain.

        2. **action**  
        The name of the agent tool to call (must be one of the available tools).

        3. **action_input**  
        A dictionary of parameters for the selected tool (use `{{}}` if none).
        ───────────────────────────────────────────────────────────
        ## Available Agent Tools
        {tools_description}
        ───────────────────────────────────────────────────────────
        ## GLOBAL WORKFLOW

        The compliance-checking process consists of **three phases**:

        ### Phase 1 — Planning
        Call `generate_subgoals` once to create a plan consisting of four subgoal categories:

        1. Step1 — Identification  
        2. Step2 — Data Collection  
        3. Step3 — Analysis  
        4. Step4 — Verification  

        Subgoals created here must be executed sequentially during Phase 2.

        ### Phase 2 — Executing Subgoals ()
        #### Step1-Step3: the agent performs reasoning and uses tools to collect and analyze IFC data.

        Allowed tools include:
        - IFC tool lifecycle tools (`select_ifc_tool`, `create_ifc_tool`, `execute_ifc_tool`, `fix_ifc_tool`, `store_ifc_tool`)
        - Subgoal management tools (`review_and_update_subgoals`)

        #### Step4: Verification
        When all necessary evidence has been collected:
        1. In the **thought**, perform final reasoning over all in-scope components.
        2. Call **`generate_compliance_report` once** with a complete list of component-level decisions.

        ───────────────────────────────────────────────────────────
        ## HARD RULES SUMMARY (ALWAYS FOLLOW)

        ### 1. Tool Selection Priority
        1) Always use `select_ifc_tool` **before** creating new tools.  
        2) If no suitable stored tool exists → use `create_ifc_tool`.  
        3) NEVER modify an existing selected tool; new tools must be created.

        ### 2. Tool Fixing Rules
        Use **`fix_ifc_tool` only if ALL are true**:
        - Tool was created in this session.
        - Error is clear and simple.
        - No complex IFC domain reasoning required.
        - Fix attempts ≤ 2.

        Otherwise → **use `create_ifc_tool`**.
        After any `fix_ifc_tool`, you MUST re-run `execute_ifc_tool` to verify success.

        ### 3. Mandatory Tool Persistence
        After a newly created tool executes successfully:
        - You MUST call `store_ifc_tool` immediately.
        - DO NOT execute another tool.
        - DO NOT continue to the next subgoal.
        - Stored tools become available to `select_ifc_tool` in future sessions.
        Fix success alone is NOT enough. Only store after `execute_ifc_tool` succeeds.

        ### 4. Subgoal Progress Management
        You MUST call `review_and_update_subgoals` when:
        - The current in-progress subgoal is complete, OR
        - You determine the plan must change (e.g., missing data, wrong assumptions, new insights).

        Never move to another subgoal without calling this tool.

        ### 5. Investigation Rules
        During Step2 (Data Collection):

        Investigate when:
        - Suggested mapping returns null/empty.
        - The attribute/property name is unclear.
        - Model uses different naming conventions.
        - You need to verify where data is actually stored.

        Do NOT investigate when:
        - Data extraction is already correct and complete.
        - You already investigated and confirmed the correct mapping.

        ### 6. Step4 Verification Rules
        - Step2 collects raw data. Step3 computes derived values. Step4 only reasons.
        - In Step4 THOUGHT:
        - Evaluate every in-scope component.
        - Then call `generate_compliance_report` **once**.
        - Output format for component decisions:
        - Non-compliant → full detail required.
        - Compliant / Not-applicable → simplified format allowed.

        ───────────────────────────────────────────────────────────
        ## DETAILED EXECUTION GUIDELINES

        ### Step1-3: Tool Usage Workflow
        Follow this workflow strictly:

        1. **Reuse First**  
        Call `select_ifc_tool` with a clear `task_description`.  
        If a tool is found → go to Step 3.

        2. **Create Only When Needed**  
        If `select_ifc_tool` fails → call `create_ifc_tool`.

        3. **Execute Tool**  
        Call `execute_ifc_tool` with the selected or newly created tool.

        4. **Validate Output**  
        - If incorrect / incomplete → follow Hard Rules for fix/create.
        - If correct → proceed.

        5. **MANDATORY STORE CHECKPOINT**  
        If the tool was created in this session and validated by a successful `execute_ifc_tool`:
        - Call `store_ifc_tool`
        - Then stop; next iteration will continue from the stored tool.

        **If you used `fix_ifc_tool`, return to Step 3 (Execute Tool) and validate before storing.**

        6. **MANDATORY SUBGOAL UPDATE CHECKPOINT**  
        If the subgoal is complete or impossible:
        - Call `review_and_update_subgoals`
        - Then continue to next subgoal.

        ### Step2: Investigation Details
        **When suggested property mapping returns empty/null → investigate immediately:**
        1. Pick 1-2 sample elements from target set
        2. Use `inspect_element_properties` or `inspect_element_relationships`
        3. Find alternative data sources from actual model structure
        4. Adjust extraction and re-run

        ───────────────────────────────────────────────────────────
        ## Step4: Compliance Decision and Reporting

        ### In THOUGHT:
        - Identify **regulation-relevant components** (components the regulation applies to).
        - **Check Evaluation Scope**: If the interpretation specifies evaluation_scope, pay attention to reporting_component_type.
          This means you should group/aggregate data and report compliance at that level, not at the data collection level.
        - Apply regulation rule(s) to each relevant component.
        - For each relevant component, conclude:
            - compliant
            - non_compliant
            - not_applicable

        ### Then call:
        `generate_compliance_report` with decisions for **regulation-relevant components only**.

        **CRITICAL: Do NOT include components that are outside the regulation's scope.**
        - Example: If regulation applies to "habitable spaces", do NOT include mechanical rooms, corridors, or other non-habitable spaces.

        **Component Granularity:**
        - If evaluation_scope is specified: use reporting_component_type (e.g., IfcBuildingStorey) as component_type and its GlobalId as component_id
        - If not specified: use the element type you collected data from (e.g., IfcDoor, IfcSpace)

        **Formats:**

        Non-compliant example:
        {{
        "component_id": "Door_12",
        "component_type": "IfcDoor",
        "data_used": {{"width_mm": 700}},
        "compliance_status": "non_compliant",
        "violation_reason": "Width 700mm < required 800mm",
        "suggested_fix": "Increase width to at least 800mm"
        }}

        Compliant example:
        {{"component_id": "Door_02", "compliance_status": "compliant"}}

        Not applicable example:
        {{"component_id": "Door_07", "compliance_status": "not_applicable"}}

        ───────────────────────────────────────────────────────────
        ## Interpretation Rules
        You will receive a “Regulation Interpretation” section.  
        Use it only as **initial guidance**, not strict truth.

        If actual IFC structure differs:
        - Trust the IFC model.
        - Investigate.
        - Update subgoals accordingly.

        ───────────────────────────────────────────────────────────
        ## Remember
        - Maintain strict discipline: THOUGHT → ACTION → ACTION_INPUT.
        - Always justify in THOUGHT.
        - Always follow Hard Rules.
        - The goal is to collect evidence, then decide compliance.
        - Deviate from rules only if you explicitly justify why.
        """

        # Build final prompt based on phase
        prompt = f"""
        ## You will now receive:
        - Regulation text: 
        "{regulation_text}"

        - Regulation interpretation:
        {interpretation_section}

        - IFC file path  
        {ifc_file_path}

        - Subgoals  
        {subgoals_section}

        - Agent history  
        {complete_history}
        
        Based on this context, determine the next action.
        Think step by step, reason clearly, and follow the workflow.
        """

        try:
            response = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                response_model=ReActIterationOutput
            )
            return response
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            raise RuntimeError(f"ReAct LLM call failed: {e}") from e


    def _execute_action(self, action_name: str, action_input: Dict[str, Any]) -> AgentToolResult:
        """Execute the selected agent tool"""

        try:
            # Get the callable tool function
            tool_func = self.agent_tool_registry.get_callable(action_name)

            if tool_func is None:
                return AgentToolResult(
                    success=False,
                    agent_tool_name=action_name,
                    error=f"Agent tool '{action_name}' not found in registry"
                )

            # Execute tool with provided parameters
            result = tool_func(**action_input)

            # All agent tools should return AgentToolResult
            if not isinstance(result, AgentToolResult):
                return AgentToolResult(
                    success=False,
                    agent_tool_name=action_name,
                    error=f"Agent tool '{action_name}' returned unexpected type: {type(result)}"
                )

            return result

        except Exception as e:
            return AgentToolResult(
                success=False,
                agent_tool_name=action_name,
                error=f"Agent tool execution failed: {str(e)}"
            )
