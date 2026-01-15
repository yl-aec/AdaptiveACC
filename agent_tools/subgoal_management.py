
import json
from typing import Dict, List, Any
from utils.llm_client import LLMClient
from models.common_models import SubgoalSetModel, AgentToolResult
from models.shared_context import SharedContext, format_interpretation
from telemetry.tracing import trace_method
from agent_tools.regulation_interpretation import RegulationInterpretationTool

class SubgoalManagement:

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    @trace_method("subgoal_generation")
    def generate_subgoals(self) -> AgentToolResult:
        """Generate initial subgoals for compliance checking workflow.

        This method should ONLY be called once at the beginning of the workflow
        to create the initial set of subgoals. For all subsequent modifications
        (including major re-planning), use review_and_update_subgoals instead.

        Automatically generates regulation interpretation before creating subgoals.

        Returns:
            AgentToolResult with SubgoalSetModel in result field
        """
        try:
            regulation_text = self.shared_context.session_info.get("regulation_text")

            # generate interpretation
            print("\n[SubgoalManagement] Generating regulation interpretation...")
            
            interpretation_tool = RegulationInterpretationTool()
            interp_result = interpretation_tool.generate_interpretation()

            if interp_result.success:
                interpretation = interp_result.result
                print(f"[SubgoalManagement] Interpretation generated with {len(interpretation.term_clarifications)} term clarifications")
                # Interpretation already stored by RegulationInterpretationTool in session_info["interpretation"]
            else:
                raise RuntimeError(f"Interpretation generation failed: {interp_result.error}")

            # Build system prompt
            system_prompt = """
            You are a **building compliance planning expert**.  

            ## Your Task
            Generate **high-level, atomic subgoals** for the compliance checking process.
            The generated subgoals should describe **WHAT** must be achieved (never HOW).  
            Each subgoal must correspond to **one atomic action** and be part of one of the four action types below.
            ──────────────────────────────────────────────────────────
            ## The Four Sequential Steps
            Each subgoal must belong to exactly one of these steps.

            ### **1. Identification [Step1]**
            **Intent:** Define the initial scope of relevant elements.
            **Action:** Filter by type, classification, or static properties.

            **Goal Patterns:**
            - "Identify element IDs for all [element type]."
            - "Identify element IDs for all [element type] that meet [condition]."
            **Output:** A list of element IDs.

            ### **2. Data Collection [Step2]**
            **Intent:** Fetch raw model data for a known list of element IDs.
            **Action:** Retrieve necessary raw IFC data for compliance verification.
            **Goal Patterns:**
            - "Obtain the [property] for the elements in [ID list]."
            - "Collect [relationship] data for the elements in [ID list]."
            **Output:** Raw data keyed by element ID.

            ### **3. Analysis & Calculation [Step3]**
            **Intent:** Derive or transform information **using already collected data**.
            **Action:** Compute a metric, filter, aggregate, map, or join datasets.
            **Goal Patterns:**
            - "Calculate [derived metric] for each element."
            - "Analyze [dataset] to find [result]."
            **Output:** Derived results or transformed datasets.

            ### **4. Verification & Comparison [Step4]**
            **Intent:** Mark WHAT needs to be verified against regulatory requirements.
            **Action:** Describe the verification requirement (not the execution method).
            **Goal Patterns:**
            - "Verify that [value] is [comparison] [requirement]."
            - "Check whether [condition] holds for each element."
            **Output:** Verification requirement specification.
            ──────────────────────────────────────────────────────────
            ## Dynamic Dependency Graph (Not a Fixed Sequence)
            The subgoal sequence does **not** have to follow Step1 -> Step2 -> Step3 -> Step4 strictly.
            Any subgoal may depend on the output of **any** earlier subgoal.

            **IMPORTANT CONSTRAINT: Filtering Priority**
            - Step1 filtering: Use for subset identification based on **intrinsic properties** (type, attributes, property sets that exist in the model)
            - Step3 filtering: Only for **derived conditions** (calculations, spatial relationships, complex logic that requires prior data collection)
            - **Never defer simple property-based filtering to Step3** if it can be done in Step1
            ──────────────────────────────────────────────────────────
            ## Subgoal Requirements
            Each subgoal must be a JSON object with:
            - `"description"` — WHAT needs to be done
            - `"rationale"` — WHY this step is necessary and how it supports compliance checking

            ### Rationale Examples
            - "To define the primary scope of elements"
            - "To obtain property data required for later calculation."
            - "To derive a filtered list of relevant wall IDs."

            ### Additional Requirements
            - Subgoals must be **atomic** (only one action type per subgoal).
            - Focus on *intent*, not tool usage or implementation details.
            ──────────────────────────────────────────────────────────
            ## Step1 Scope Identification (CRITICAL)
            **Core principle:** Filter early. Step1 scope should match regulation's intended scope.

            **Ask: Does regulation apply to ALL elements of a type, or a SUBSET?**
            - If regulation describes elements by ROLE/FUNCTION/DESIGNATION → likely a subset
            - Check regulation interpretation's `required_data` for distinguishing properties

            **Action:**
            Use available tools to filter in Step1:
            - `get_element_ids_by_type` - All elements of IFC type
            - `get_elements_by_predefined_type` - By PredefinedType attribute
            - `get_elements_by_property` - By property value (for subset identification)
            - `find_spaces_by_function` - By space function keywords
            """

            # Build interpretation and required data sections with shared formatter
            formatted_sections = format_interpretation(interpretation)
            interpretation_section = formatted_sections["interpretation_section"]
            required_data_section = formatted_sections["required_data_section"]

            prompt = f"""
            ## Regulation:
            "{regulation_text}"
            {interpretation_section}
            {required_data_section}

            Based on all available information, generate initial subgoals for compliance checking.
            Remember: Focus on WHAT to achieve, not HOW.
            """

            # Call LLM to generate subgoals

            subgoals = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=SubgoalSetModel
            )

            # Check if LLM call failed
            if subgoals is None:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_subgoals",
                    error="LLM failed to generate subgoals (returned None)"
                )

            print(f"SubgoalManagement: Generated {len(subgoals.subgoals)} initial subgoals")

            # Automatically set the first subgoal to in_progress to signal the agent to start execution
            if subgoals.subgoals:
                subgoals.subgoals[0].status = "in_progress"
                print(f"SubgoalManagement: Set subgoal {subgoals.subgoals[0].id} to 'in_progress'")

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_subgoals",
                result=subgoals
            )

        except Exception as e:
            print(f"SubgoalManagement: Failed to generate subgoals: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_subgoals",
                error=f"Subgoal generation failed: {str(e)}"
            )


    @trace_method("subgoal_review")
    def review_and_update_subgoals(self, current_progress: str, suggested_completed_ids: List[int],) -> AgentToolResult:
        """Review and update all subgoals (handles ALL modifications after initial generation).

        This is the PRIMARY method for all subgoal modifications after initial generation, including:
        - Marking completed subgoals
        - Adjusting existing subgoal descriptions
        - Adding new subgoals when discovering new requirements
        - Removing or consolidating obsolete subgoals
        - Complete re-planning if the entire approach is wrong

        Verifies completion status and adjusts remaining subgoals based on Agent's progress report
        and tool execution history from SharedContext.

        Args:
            current_progress: Agent's description of current progress and any new discoveries
            suggested_completed_ids: Subgoal IDs that Agent believes are completed

        Returns:
            AgentToolResult with SubgoalSetModel in result field
        """
        try:
            regulation_text = self.shared_context.session_info.get("regulation_text", "")
            current_subgoals = self.shared_context.subgoals

            # Use SharedContext formatting method for evidence summary
            evidence_text = self.shared_context.format_successful_executions_summary(max_per_subgoal=3)

            # Build system prompt
            system_prompt = """
            You are a **task management expert** for building compliance checking.
            Your role is to **review the Agent’s progress** and **update all subgoals** based on the latest execution history.

            ──────────────────────────────────────────────────────────
            ## Your Task
            You may perform **any necessary modification** to maintain an accurate and coherent subgoal plan:

            1. **Verify completions**: Confirm which subgoals are truly completed based on execution evidence.
            2. **Adjust existing subgoals**: Revise descriptions or rationale if new insights or model discoveries require it.
            3. **Add new subgoals**: When new data dependencies, overlooked requirements, or missing steps are discovered.
            4. **Remove or consolidate subgoals**: When tasks become irrelevant, redundant, or logically mergeable.
            5. **Full re-planning**: If the Agent reports that the current strategy is flawed, replace all subgoals with a new coherent plan.

            ──────────────────────────────────────────────────────────
            ## Verification Principles (Critical)
            A subgoal is “completed” **only when all of the following are true**:

            1. **execute_ifc_tool was called for this subgoal’s purpose**  
            2. The execution returned **success=true**  
            3. The returned data **fully satisfies the information required** by that subgoal  
            4. No missing or failed data extraction remains

            You must NOT mark a subgoal as completed in these cases:
            - Only planning tools were used (`generate_subgoals`, `review_and_update_subgoals`)  
            - `select_ifc_tool` or `create_ifc_tool` was called without actual execution  
            - Any execution attempt failed (success=false)  
            - Only partial results were obtained  
            - The Agent claims completion without evidence

            **When in doubt: mark the subgoal as pending or in_progress.  
            Be conservative.**

            ──────────────────────────────────────────────────────────
            ## Update Principles
            - **Goal-oriented**: Subgoals always describe WHAT must be achieved, never HOW.
            - **Independence**: Keep subgoals as independent as possible unless dependencies are unavoidable.
            - **Adaptability**: If the Agent uncovers missing steps, introduce new subgoals immediately.
            - **Coherence**: If the approach is fundamentally incorrect, perform a full re-plan.
            - **Evidence-based**: All decisions must be grounded in actual `agent_history` and tool outputs stored in SharedContext.
            - **Knowledge propagation**: When investigation discovers concrete data sources (specific property names, relationships, or geometric methods), update subsequent subgoal descriptions to reference these findings. This helps the Agent avoid repeating investigations.

            ──────────────────────────────────────────────────────────
            ## Subgoal Ordering Principles 

            When modifying the subgoal list, maintain logical **execution order**:

            1. **New subgoals must be inserted at the appropriate position**, not appended to the end.
            2. Order subgoals by execution dependencies:
               - Data identification before data collection
               - Data collection before analysis
               - Analysis before verification
            3. **Do NOT move completed subgoals** - they should remain in their original positions.
            4. **Assign sequential IDs** - Number subgoals sequentially starting from 1 (1, 2, 3, ...).

            **Example:**
            - Current: [1. Identify doors (completed), 2. Verify height (pending), 3. Check width (pending)]
            - Need to add: "Extract door properties"
            - ✓ CORRECT: [1. Identify doors (completed), 2. Extract door properties (pending), 3. Verify height (pending), 4. Check width (pending)]
            - ✗ WRONG: [1. Identify doors (completed), 2. Verify height (pending), 3. Check width (pending), 4. Extract door properties (pending)]

            ──────────────────────────────────────────────────────────
            ## Output Format
            Return a complete `SubgoalSetModel`, reflecting your updated subgoal list.  
            Every subgoal must include:
            - `id`
            - `description` (WHAT must be achieved)
            - `status` (pending / in_progress / completed)
            - `rationale` (WHY this step is necessary, linked to the compliance requirement)
            """

            # Build user prompt
            prompt = f"""
            ## Regulation Context
            "{regulation_text}"

            ## Current Subgoals
            {json.dumps(current_subgoals, indent=2)}

            {evidence_text}

            ## Agent Progress Report
            {current_progress}

            ## Agent's Suggested Completed Subgoal IDs
            {suggested_completed_ids}

            Review and update the subgoals based on the evidence above.
            Return the complete updated SubgoalSetModel."""

            # 5. Call LLM
            updated_subgoals = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=SubgoalSetModel
            )

            # Check if LLM call failed
            if updated_subgoals is None:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="review_and_update_subgoals",
                    error="LLM failed to update subgoals (returned None)"
                )

            print(f"SubgoalManagement: Reviewed and updated subgoals - {len(updated_subgoals.subgoals)} total")
            completed_count = sum(1 for sg in updated_subgoals.subgoals if sg.status == "completed")
            print(f"SubgoalManagement: {completed_count} completed, {len(updated_subgoals.subgoals) - completed_count} pending")

            return AgentToolResult(
                success=True,
                agent_tool_name="review_and_update_subgoals",
                result=updated_subgoals
            )

        except Exception as e:
            print(f"SubgoalManagement: Failed to review subgoals: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="review_and_update_subgoals",
                error=f"Subgoal review failed: {str(e)}"
            )
