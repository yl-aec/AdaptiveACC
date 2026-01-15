
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# === Regulation Interpretation ===

class TermClarification(BaseModel):
    """Conceptual clarification for a technical term - NO IFC MAPPING"""
    term: str = Field(..., description="The term to clarify")
    meaning: str = Field(..., description="What this term means in the regulation context")
    notes: Optional[str] = Field(None, description="notes on its role within the regulation.")

class RequiredData(BaseModel):
    """Required data for compliance checking with IFC mapping certainty"""
    data_name: str = Field(..., description="Name of required data (e.g., 'Door egress status', 'Fire rating')")
    description: str = Field(..., description="What this data represents in regulation context")
    element_types: List[str] = Field(..., description="Applicable IFC element types (e.g., ['IfcDoor', 'IfcWall'])")
    source_candidates: List[str] = Field(..., description="Source candidates for this data (e.g., ['IfcPropertySet', 'IfcRelDefinesByProperties'])") 
    suggested_mapping: Optional[str] = Field(None, description="Primary/recommended IFC property mapping")
    derivation_hints: Optional[List[str]] = None


class EvaluationScope(BaseModel):
    """Defines the scope and granularity for compliance evaluation"""
    data_collection_elements: List[str] = Field(..., description="Element types from which to collect data (e.g., ['IfcSpace', 'IfcDoor'])")
    reporting_component_type: str = Field(..., description="Element type to use as component in compliance report (e.g., 'IfcBuildingStorey', 'IfcSpace', 'IfcDoor')")
    grouping_rationale: str = Field(..., description="Explanation of why this grouping is used (e.g., 'Regulation checks consistency across spaces within each storey, so each storey is evaluated as one component')")


class RegulationInterpretation(BaseModel):
    """Human-readable interpretation of a regulation with disambiguated semantics"""
    plain_language: str = Field(..., description="Simple explanation of the regulation in everyday language (2-3 sentences)")
    evaluation_scope: Optional[EvaluationScope] = Field(None, description="Defines what elements to collect data from vs. what granularity to report compliance at. Required when data collection and reporting happen at different levels (e.g., collect from spaces but report per storey)")
    term_clarifications: List[TermClarification] = Field(default_factory=list, description="Clarifications for technical terms and concepts (concept only, no IFC mapping)")
    implicit_requirements: List[str] = Field(default_factory=list, description="Contextual assumptions needed to interpret the rule")
    common_misunderstandings: List[str] = Field(default_factory=list, description="Common mistakes or misinterpretations to avoid when implementing this check")
    required_data: List[RequiredData] = Field(default_factory=list, description="All data required for compliance checking with IFC mapping and certainty flags")


# === Checker ===

class SimpleCheckedComponent(BaseModel):
    """Simplified model for compliant/not_applicable components (minimal token usage)"""
    component_id: str = Field(..., description="IFC GUID or unique component identifier")
    compliance_status: str = Field(..., description="one of: compliant, not_applicable")


class CheckedComponent(BaseModel):
    """Model for individual IFC component compliance check result (full details for violations)"""
    component_id: str = Field(..., description="IFC GUID or unique component identifier")
    component_type: str = Field(..., description="IFC class or category, e.g., IfcDoor, IfcWall")
    data_used: Dict[str, Any] = Field(..., description="Key-value data used for compliance checking (values can be strings, numbers, booleans, etc.)")
    compliance_status: str = Field(..., description="one of: compliant, non_compliant, not_applicable")
    violation_reason: Optional[str] = Field(None, description="Reason for non-compliance or not-applicability")
    suggested_fix: Optional[str] = Field(None, description="Optional suggestion to fix non-compliance")


class ComplianceEvaluationModel(BaseModel):
    """Model for compliance evaluation results with optimized token usage"""
    overall_status: str = Field(..., description="One of: 'compliant' (all evaluated components are compliant, not_applicable ignored), 'non_compliant' (at least one component is non-compliant), or 'not_applicable' (all components are not_applicable or no relevant components found).")
    compliant_components: List[SimpleCheckedComponent] = Field(..., description="REQUIRED: List of all compliant components (simplified format with ID and status only). Must include ALL components checked and found compliant. Empty list only if no compliant components exist.")
    non_compliant_components: List[CheckedComponent] = Field(..., description="REQUIRED: List of non-compliant components with full details (ID, type, rule, data, violation reason, suggested fix). Must include ALL violations found.")
    not_applicable_components: List[SimpleCheckedComponent] = Field(..., description="REQUIRED: List of components where requirement is not applicable (simplified format). Must include ALL components where data is missing or requirement doesn't apply.")
    component_summary: Optional[Dict[str, int]] = Field(None, description="Summary statistics. Contains: total_checked, compliant_count, non_compliant_count, not_applicable_count. Use this to verify all checked components are listed.")


# === Agent Tools ===

class ReActIterationOutput(BaseModel):
    """ReAct iteration output structure for structured LLM response"""
    thought: str = Field(
        ...,
        description="Your reasoning about the current situation and what to do next. Explain your thinking step by step."
    )
    action: str = Field(
        ...,
        description="The agent tool to call. Must be one of the available tools: generate_subgoals, review_and_update_subgoals, select_ifc_tool, create_ifc_tool, execute_ifc_tool, fix_ifc_tool, store_ifc_tool, make_compliance_judgment, generate_report"
    )
    action_input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool as a dictionary. Empty dict if no parameters needed."
    )


class AgentToolResult(BaseModel):
    """Standardized result model for agent tool execution"""
    success: bool = Field(..., description="Whether the execution was successful")
    agent_tool_name: str = Field(..., description="Name of the agent tool executed")
    result: Optional[Any] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


# === Tool Creation ===

class RetrievedDocument(BaseModel):
    """Retrieved document from RAG system"""
    content: str = Field(..., description="Content of the retrieved document")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    relevance_score: float = Field(..., description="Relevance score for the document")


class ToolParam(BaseModel):
    """Function parameter definition"""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type, e.g., 'str', 'int', 'float', 'dict'")
    description: Optional[str] = Field(None, description="Parameter description")
    required: bool = Field(..., description="Is this parameter required?")
    default: Optional[str] = Field(None, description="Default value for the parameter (as a string)")


class ToolMetadata(BaseModel):
    """Metadata for the created tool"""
    ifc_tool_name: str = Field(..., description="Tool name, unique identifier")
    description: str = Field(..., description="Short description of the tool")
    parameters: List[ToolParam] = Field(..., description="Function parameters")
    return_type: Optional[str] = Field(None, description="Function return type")
    category: str = Field(default="IfcOpenShell", description="Tool category for organization")
    tags: List[str] = Field(default_factory=list, description="Keywords for retrieval")


class ToolCreatorOutput(BaseModel):
    """Output model for tool creation and fixing"""
    ifc_tool_name: str = Field(..., description="Tool name, unique identifier")
    code: str = Field(..., description="Python function code as a string")
    metadata: ToolMetadata = Field(..., description="Tool metadata")

    # Optional fields for fix_ifc_tool tracking (None for newly created tools)
    modification_summary: Optional[str] = Field(None, description="Summary of modifications made (only for fixed tools)")
    modification_requirement: Optional[str] = Field(None, description="Original modification requirement (only for fixed tools)")


# === IFC Tool Execution and Fixing ===

class IFCToolResult(BaseModel):
    """Result model for IFC tool execution (syntax and runtime)"""
    success: bool = Field(..., description="Whether the code passed the check")
    ifc_tool_name: str = Field(..., description="IFC tool name")
    result: Optional[Any] = Field(None, description="Result of code execution if successful")
    parameters_used: Dict[str, Any] = Field(default_factory=dict, description="Parameters used")
    tool_source: Optional[str] = Field(None, description="Tool origin: 'created' (current session) or 'existing' (pre-existing)")

    # Error-related fields (only present when success=False)
    error_message: Optional[str] = Field(None, description="Error message")
    exception_type: Optional[str] = Field(None, description="Exception type, e.g., SyntaxError, RuntimeError")
    traceback: Optional[str] = Field(None, description="Complete stack trace")
    line_number: Optional[int] = Field(None, description="Line number where the error occurred")


class FixedCodeOutput(BaseModel):
    """Output model for fixed/modified code"""
    code: str = Field(..., description="Fixed/modified Python code")
    summary: str = Field(..., description="Brief explanation of what was changed and why (1-2 sentences)")


# === Sandbox Executor ===

class TestResult(BaseModel):
    """Test execution result"""
    success: bool = Field(..., description="Whether the test was successful")
    output: str = Field(..., description="Test output message")
    error: str = Field(..., description="Error message if test failed")


# === ComplianceAgent ===

class SubgoalModel(BaseModel):
    """Subgoal model - replaces StepModel"""
    id: int = Field(..., description="Subgoal ID")
    description: str = Field(..., min_length=1, description="Goal description (WHAT to achieve, not HOW)")
    status: Literal["pending", "in_progress", "completed"] = Field(default="pending", description="Subgoal status")
    rationale: Optional[str] = Field(None, description="Why this subgoal is needed")


class SubgoalSetModel(BaseModel):
    """Subgoal collection - replaces PlanModel
    Note: subgoals can be empty initially in ReAct architecture, as the agent may generate them dynamically during execution.
    """
    subgoals: List[SubgoalModel] = Field(default_factory=list, description="List of subgoals (can be empty initially)")


class AgentResult(BaseModel):
    """ReAct agent execution result"""
    status: Literal["success", "timeout", "failed"] = Field(..., description="Execution status")
    iterations_used: int = Field(..., description="Number of ReAct iterations used")
    agent_history: List[Dict[str, Any]] = Field(default_factory=list, description="Complete ReAct history")
    compliance_result: Optional[ComplianceEvaluationModel] = Field(None, description="Final compliance evaluation result")
    error: Optional[str] = Field(None, description="Error message if failed")
    span_id: Optional[str] = Field(None, description="Phoenix trace span ID for evaluation annotation linking")


