import pytest
from app.models.schemas import (
    WorkflowState,
    WorkflowStage,
    Opportunity,
    Requirement,
    RequirementCategory,
    RequirementStatus,
    DocumentInfo,
    DocumentType,
    HumanDecision,
    HumanDecisionOption,
    CompletionReceipt
)


def test_opportunity_schema():
    opp = Opportunity(
        name="Global Fellowship",
        organization="Global Science Foundation",
        deadline="2026-11-15",
        eligibility=["Must have B.S."],
        required_documents=["CV", "Transcript"],
        source="demo"
    )
    assert opp.name == "Global Fellowship"
    assert len(opp.eligibility) == 1
    assert opp.required_documents == ["CV", "Transcript"]


def test_requirement_and_state_serialization():
    req = Requirement(
        id="REQ-01",
        description="Submit official transcript",
        category=RequirementCategory.DOCUMENT,
        required=True,
        evidence_needed="Transcript with GPA",
        status=RequirementStatus.SATISFIED,
        confidence=0.98,
        evidence="Transcript uploaded"
    )
    state = WorkflowState(
        workflow_id="WF-TEST-001",
        current_stage=WorkflowStage.ANALYZING,
        requirements=[req]
    )

    json_str = state.model_dump_json()
    reloaded = WorkflowState.model_validate_json(json_str)
    assert reloaded.workflow_id == "WF-TEST-001"
    assert len(reloaded.requirements) == 1
    assert reloaded.requirements[0].id == "REQ-01"
    assert reloaded.requirements[0].status == RequirementStatus.SATISFIED


def test_human_decision_schema():
    decision = HumanDecision(
        decision_id="DEC-01",
        reason="Recommendation letter missing",
        context="Referee letter is mandatory",
        options=[
            HumanDecisionOption(
                option_id="OPT-1",
                label="I will upload it",
                description="Upload letter",
                action="PROVIDE_DOCUMENT"
            )
        ]
    )
    assert decision.resolved is False
    assert len(decision.options) == 1
