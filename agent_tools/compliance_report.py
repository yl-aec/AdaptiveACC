
from typing import List, Dict, Any
from models.common_models import (
    ComplianceEvaluationModel,
    AgentToolResult,
    CheckedComponent,
    SimpleCheckedComponent
)
from models.shared_context import SharedContext
from telemetry.tracing import trace_method


class ComplianceReport:
    """Generates structured compliance report from component decisions."""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()

    @trace_method("compliance_report_generation", log_result=True)
    def generate_compliance_report(
        self,
        component_decisions: List[Dict[str, Any]]
    ) -> AgentToolResult:
        """Generate structured compliance report from component compliance decisions.

        This tool validates component decisions, categorizes them by compliance status,
        and generates a complete compliance report with overall status determination.

        CRITICAL REQUIREMENT: Include ALL **regulation-relevant** components in component_decisions.
        - Regulation-relevant = components that the regulation actually applies to
        - Do NOT include components outside the regulation's scope (e.g., if checking habitable spaces, exclude mechanical rooms)
        - Do include compliant, non_compliant, and not_applicable regulation-relevant components

        TOKEN OPTIMIZATION: For compliant and not_applicable components, you can provide
        simplified format (only component_id + compliance_status) to save tokens.
        Full details are only required for non_compliant components.

        Args:
            component_decisions: List of component-level decisions for regulation-relevant components only.
                Include all relevant components (compliant, non_compliant, not_applicable), but exclude out-of-scope components.

                For NON_COMPLIANT components (FULL DETAILS REQUIRED):
                - component_id (str): IFC GUID or unique component identifier
                - component_type (str): IFC class (e.g., "IfcDoor", "IfcWall")
                - checked_rule (str): The regulation requirement being verified
                - data_used (dict): Dictionary of data used for checking (e.g., {"width": 900})
                - compliance_status (str): "non_compliant"
                - violation_reason (str): Reason for non-compliance
                - suggested_fix (str, optional): Suggestion to fix non-compliance

                For COMPLIANT and NOT_APPLICABLE components (SIMPLIFIED FORMAT):
                - component_id (str): IFC GUID or unique component identifier
                - compliance_status (str): "compliant" or "not_applicable"

        Returns:
            AgentToolResult with ComplianceEvaluationModel in result field containing:
            - compliant_components: Simplified list (IDs only) of components meeting requirements
            - non_compliant_components: Full details of components violating requirements
            - not_applicable_components: Simplified list (IDs only) of components where requirement doesn't apply
            - overall_status: "compliant", "non_compliant", or "not_applicable" based on three-way rules
            - component_summary: Statistics for verification
        """
        try:
            # Step 1: Validate and convert component_decisions (support both full and simplified formats)
            try:
                validated_components = []
                for comp in component_decisions:
                    # Check compliance_status to determine format requirement
                    status = comp.get('compliance_status')

                    if status in ['compliant', 'not_applicable']:
                        # Compliant/not_applicable can use simplified format
                        # Only extract component_id and compliance_status (ignore extra fields)
                        simple_comp = SimpleCheckedComponent(
                            component_id=comp['component_id'],
                            compliance_status=comp['compliance_status']
                        )
                        validated_components.append(simple_comp)
                    elif status == 'non_compliant':
                        # Non-compliant requires full details
                        full_comp = CheckedComponent(**comp)
                        validated_components.append(full_comp)
                    else:
                        raise ValueError(f"Invalid compliance_status: {status}. Must be one of: compliant, non_compliant, not_applicable")
            except Exception as e:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_compliance_report",
                    error=f"Invalid component_decisions schema: {e}. Non-compliant components must have full details (component_id, component_type, checked_rule, data_used, compliance_status, violation_reason). Compliant/not_applicable can use simplified format (component_id, compliance_status)."
                )

            if not validated_components:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="generate_compliance_report",
                    error="component_decisions cannot be empty. You must provide at least one component decision."
                )

            # Step 2: Categorize components by compliance status
            compliant_simple = []
            non_compliant = []
            not_applicable_simple = []

            for comp in validated_components:
                if comp.compliance_status == "compliant":
                    # If already simplified, use directly; otherwise convert
                    if isinstance(comp, SimpleCheckedComponent):
                        compliant_simple.append(comp)
                    else:
                        compliant_simple.append(SimpleCheckedComponent(
                            component_id=comp.component_id,
                            compliance_status=comp.compliance_status
                        ))
                elif comp.compliance_status == "non_compliant":
                    # Non-compliant must be full CheckedComponent
                    if isinstance(comp, SimpleCheckedComponent):
                        return AgentToolResult(
                            success=False,
                            agent_tool_name="generate_compliance_report",
                            error=f"Non-compliant component {comp.component_id} must include full details (component_type, checked_rule, data_used, violation_reason). Simplified format is only allowed for compliant/not_applicable components."
                        )
                    non_compliant.append(comp)
                else:  # not_applicable
                    # If already simplified, use directly; otherwise convert
                    if isinstance(comp, SimpleCheckedComponent):
                        not_applicable_simple.append(comp)
                    else:
                        not_applicable_simple.append(SimpleCheckedComponent(
                            component_id=comp.component_id,
                            compliance_status=comp.compliance_status
                        ))

            # Step 3: Calculate overall_status using three-way classification rules
            # Rule 1: If any component is non-compliant → overall is non_compliant
            # Rule 2: If all components are compliant (ignoring not_applicable) → overall is compliant
            # Rule 3: If all components are not_applicable → overall is not_applicable
            if non_compliant:
                overall_status = "non_compliant"
            elif compliant_simple:
                overall_status = "compliant"
            else:
                overall_status = "not_applicable"

            # Step 4: Build component summary for verification
            all_components_count = len(validated_components)
            component_summary = {
                "total_checked": all_components_count,
                "compliant_count": len(compliant_simple),
                "non_compliant_count": len(non_compliant),
                "not_applicable_count": len(not_applicable_simple)
            }

            # Step 5: Create final compliance evaluation model
            report = ComplianceEvaluationModel(
                overall_status=overall_status,
                compliant_components=compliant_simple,  # Simplified format (token savings)
                non_compliant_components=non_compliant,  # Full details for violations
                not_applicable_components=not_applicable_simple,  # Simplified format
                component_summary=component_summary  # For verification
            )

            print(f"ComplianceReport: Generated report - {overall_status}")
            print(f"  Total: {all_components_count}, Compliant: {len(compliant_simple)}, "
                  f"Non-compliant: {len(non_compliant)}, Not applicable: {len(not_applicable_simple)}")

            return AgentToolResult(
                success=True,
                agent_tool_name="generate_compliance_report",
                result=report
            )

        except Exception as e:
            print(f"ComplianceReport: Report generation failed: {e}")
            import traceback
            traceback.print_exc()
            return AgentToolResult(
                success=False,
                agent_tool_name="generate_compliance_report",
                error=f"Compliance report generation failed: {str(e)}"
            )
