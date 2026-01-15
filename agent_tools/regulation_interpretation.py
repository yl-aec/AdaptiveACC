
from utils.llm_client import LLMClient
from models.common_models import (
    RegulationInterpretation,
    AgentToolResult
)
from models.shared_context import SharedContext
from telemetry.tracing import trace_method

from typing import List, Dict, Any


class RegulationInterpretationTool:
    """Agent tool for generating regulation interpretations"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.shared_context = SharedContext.get_instance()

    @trace_method("regulation_interpretation")
    def generate_interpretation(self) -> AgentToolResult:
        """
        Generate human-readable interpretation of a building regulation.

        This tool disambiguates technical terms, maps them to IFC entities/properties,
        and clarifies common misunderstandings. Automatically incorporates context from
        web searches stored in SharedContext.

        Returns:
            AgentToolResult with RegulationInterpretation in result field
        """
        try:
            # Get regulation text and IFC file path from SharedContext
            regulation_text = self.shared_context.session_info.get("regulation_text", "")

            # Build system prompt
            system_prompt = """
            You are a **building code interpretation expert**.
            Your task is to generate a `RegulationInterpretation` for a building code clause.
            ────────────────────────────────────
            ## OUTPUT FORMAT 

            ### 1. plain_language
            A clear 2-3 sentence summary of the regulation's intent.

            ### 2. evaluation_scope (optional)
            Define this when regulation checks consistency/aggregation across grouped elements.
            - data_collection_elements: what to collect data from
            - reporting_component_type: what level to report compliance at
            - grouping_rationale: explain the grouping logic
            If not set, reporting defaults to same level as data collection.

            ### 3. term_clarifications
            Clarify important terms appearing in the regulation:
            - term  
            - meaning  
            - notes (optional)

            ### 4. implicit_requirements
            Unstated assumptions required to interpret or implement the rule.
            Examples: measurement conventions, grouping assumptions, contextual scope.

            ### 5. common_misunderstandings
            Typical errors practitioners make when interpreting the regulation.

            ### 6. required_data
            A list of data elements needed to evaluate compliance.
            For each item, output a `RequiredData` object with:

            - data_name  
            - description  
            - element_types  (candidate IFC entities)
            - source_candidates (list of likely data sources)
            - suggested_mapping  (null if not confident)
            - derivation_hints  (for derived/uncertain data)

            You must include *all* data items necessary to check the rule.
            ────────────────────────────────────
            ## HOW TO DECIDE `source_candidates`
            Choose ANY number of the following that reasonably apply based on the regulation meaning (it's a list):

            ### DIRECT sources 
            when the IFC model already contains the needed information explicitly.

            1. **"pset_property"**
            - Use when the concept corresponds to a standard property stored in a Pset.
            - Examples: FireRating, IsExternal, OperationType

            2. **"quantity"**
            - Use when the value is normally stored as a Qto_ quantity.
            - Examples: ClearWidth, GrossFloorArea, Height, Length, Area

            3. **"entity_attribute"**
            - Use when the data is available as a core IFC attribute.
            - Examples: OverallHeight, PredefinedType, CompositionType

            4. "spatial_relation"
            - Use when the needed information comes **directly from IFC relationship objects (IfcRel\*)**.
            - Examples:
                - A wall bounds a space (RelSpaceBoundary)
                - An element belongs to a storey (RelContainedInSpatialStructure)
            
            ## DERIVED sources
            Use these when the model does NOT contain a direct field for the concept.

            5. "classification_or_naming"
            - Functional roles inferred from name, ObjectType, or classification.
            - Examples: identifying circulation spaces, service rooms.

            6. "geometry"
            - Values derived from geometric representation:
            - vertical extent
            - elevation differences
            - bounding dimensions
            - orientation or alignment

            7. "hybrid"
            - Concepts whose meaning cannot be captured literally and must be inferred
            by synthesizing multiple IFC signals and reasoning about functional intent.
            ────────────────────────────────────
            ## HOW TO SET `suggested_mapping`
            - Provide suggested_mapping only when you are highly confident that a well-known standard property (e.g., FireRating, IsExternal) applies.
            - Otherwise set suggested_mapping = null.
            ────────────────────────────────────
            ## HOW TO GENERATE `derivation_hints`
            Interpretation should give:
            - fallback strategies
            - alternative ways to find data
            - geometric or relational inference paths 

            - Examples:
                - "Identify connected spaces via RelConnects or RelSpaceBoundary."
                - "Evaluate vertical or horizontal extents using geometric representation."
                - "Use naming patterns to identify functional categories."
                - "Identify the door's associated storey via RelContainedInSpatialStructure, then read the story's properties."
                - "Find all walls bounding a space through space boundaries, then read those walls’ properties."         
            ────────────────────────────────────
            ## Building Code Semantic Patterns (for reference)
            - **Threshold** (“minimum”, “at least”) → scalar comparison  
            - **Counting** (“at least N”) → cardinality checks  
            - **Consistency** (“same”, “equal”) → pairwise comparison  
            - **Spatial** (“adjacent”, “connected”, “across”, “on each side”) → relational checks  
            - **Filtering** (“required”, “fire-rated”) → subset identification  
            ────────────────────────────────────
            ## Constraints You MUST Follow
            - Do NOT invent Psets or properties.
            - Do NOT assume schema knowledge.
            """

            prompt = f"""Interpret this building regulation:
            "{regulation_text}"
            Provide a structured interpretation focusing on its precise meaning, technical terms, and IFC mappings.
            """

            # Call LLM to generate interpretation
            interpretation = self.llm_client.generate_response(
                prompt,
                system_prompt,
                response_model=RegulationInterpretation
            )

            # Check if LLM call failed
            if interpretation is None:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_interpretation",
                    error="LLM failed to generate regulation interpretation (returned None)"
                )

            if isinstance(interpretation, str):
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_interpretation",
                    error=f"LLM call failed: {interpretation}"
                )

            print(f"RegulationInterpretation: Generated interpretation with {len(interpretation.term_clarifications)} term clarifications")

            # Store in SharedContext for future use (keep as Pydantic object)
            self.shared_context.session_info["interpretation"] = interpretation

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_interpretation",
                result=interpretation
            )

        except Exception as e:
            print(f"RegulationInterpretation: Failed to generate interpretation: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_interpretation",
                error=f"Interpretation generation failed: {str(e)}"
            )
