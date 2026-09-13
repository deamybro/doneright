from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowStage(str, Enum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    REQUIREMENTS_EXTRACTED = "REQUIREMENTS_EXTRACTED"
    DOCUMENTS_ANALYZING = "DOCUMENTS_ANALYZING"
    GENERATING = "GENERATING"
    VERIFYING = "VERIFYING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    RESUMING = "RESUMING"
    FINAL_VERIFICATION = "FINAL_VERIFICATION"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class RequirementCategory(str, Enum):
    ELIGIBILITY = "ELIGIBILITY"
    DOCUMENT = "DOCUMENT"
    ESSAY_OR_STATEMENT = "ESSAY_OR_STATEMENT"
    SUBMISSION_RULE = "SUBMISSION_RULE"
    REFERENCE = "REFERENCE"
    OTHER = "OTHER"


class RequirementStatus(str, Enum):
    SATISFIED = "SATISFIED"
    MISSING = "MISSING"
    PARTIAL = "PARTIAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DocumentType(str, Enum):
    CV = "CV"
    TRANSCRIPT = "TRANSCRIPT"
    PERSONAL_STATEMENT = "PERSONAL_STATEMENT"
    RECOMMENDATION_LETTER = "RECOMMENDATION_LETTER"
    PORTFOLIO = "PORTFOLIO"
    OTHER = "OTHER"


class VerificationCheckStatus(str, Enum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class Opportunity(BaseModel):
    name: str = Field(..., description="Name of the scholarship or opportunity")
    organization: str = Field(..., description="Host institution or organization")
    deadline: Optional[str] = Field(None, description="Application deadline date/time")
    award_amount: Optional[str] = Field(None, description="Monetary award or fellowship benefits")
    eligibility: List[str] = Field(default_factory=list, description="Eligibility rules")
    required_documents: List[str] = Field(default_factory=list, description="Required documents")
    optional_documents: List[str] = Field(default_factory=list, description="Optional documents")
    required_responses: List[str] = Field(default_factory=list, description="Prompts or essays required")
    submission_rules: List[str] = Field(default_factory=list, description="Format, deadline, and portal rules")
    ambiguities: List[str] = Field(default_factory=list, description="Potential ambiguities identified")
    source: str = Field(default="user_input", description="Input document or text reference")


class Requirement(BaseModel):
    id: str = Field(..., description="Unique requirement ID (e.g. REQ-01)")
    description: str = Field(..., description="Description of the requirement")
    category: RequirementCategory = Field(default=RequirementCategory.DOCUMENT)
    required: bool = Field(default=True)
    evidence_needed: str = Field(..., description="What constitutes proof of completion")
    status: RequirementStatus = Field(default=RequirementStatus.MISSING)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: Optional[str] = Field(None, description="Extracted evidence satisfying requirement")
    source: Optional[str] = Field(None, description="Source document or reference")
    action_needed: Optional[str] = Field(None, description="Recommended next action")


class DocumentInfo(BaseModel):
    name: str
    doc_type: DocumentType
    status: str = Field(default="Found")
    extracted_information: Dict[str, Any] = Field(default_factory=dict)
    matched_requirements: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class HumanDecisionOption(BaseModel):
    option_id: str
    label: str
    description: str
    action: str


class HumanDecision(BaseModel):
    decision_id: str
    requirement_id: Optional[str] = None
    reason: str
    context: str
    options: List[HumanDecisionOption]
    selected_option: Optional[str] = None
    user_note: Optional[str] = None
    timestamp: Optional[str] = None
    resolved: bool = False


class VerificationItem(BaseModel):
    check_id: str
    category: str
    description: str
    status: VerificationCheckStatus
    details: str


class VerificationResult(BaseModel):
    overall_status: str = Field(
        ...,
        description="READY, READY_WITH_HUMAN_DECISION, INCOMPLETE, CONFLICT_DETECTED"
    )
    checks: List[VerificationItem] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    requires_human_gate: bool = False
    gate_reason: Optional[str] = None


class GeneratedArtifact(BaseModel):
    artifact_id: str
    title: str
    artifact_type: str
    content: str
    grounded_facts: List[str] = Field(default_factory=list)
    status: str = "PREPARED"


class CompletionReceipt(BaseModel):
    receipt_id: str
    opportunity_name: str
    status: str = "READY FOR SUBMISSION"
    completion_percentage: int = 100
    total_requirements: int = 0
    satisfied_count: int = 0
    missing_count: int = 0
    waived_or_human_resolved_count: int = 0
    warnings_count: int = 0
    verified_items: List[str] = Field(default_factory=list)
    remaining_issues: List[str] = Field(default_factory=list)
    generated_artifacts: List[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary: str = "DoneRight completed the preparation."


class AgentActivityLog(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    agent_name: str
    action: str
    status: str
    output_summary: str


class WorkflowState(BaseModel):
    workflow_id: str
    current_stage: WorkflowStage = WorkflowStage.CREATED
    opportunity: Optional[Opportunity] = None
    requirements: List[Requirement] = Field(default_factory=list)
    documents: List[DocumentInfo] = Field(default_factory=list)
    generated_artifacts: List[GeneratedArtifact] = Field(default_factory=list)
    verification_result: Optional[VerificationResult] = None
    human_decisions: List[HumanDecision] = Field(default_factory=list)
    active_decision: Optional[HumanDecision] = None
    completion_receipt: Optional[CompletionReceipt] = None
    activity_logs: List[AgentActivityLog] = Field(default_factory=list)
    error: Optional[str] = None
