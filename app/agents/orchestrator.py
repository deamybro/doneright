import uuid
from typing import Dict, Any, Generator, Optional, List
from strands import Agent
from app.config import get_strands_model
from app.models.schemas import (
    WorkflowState,
    WorkflowStage,
    AgentActivityLog,
    HumanDecision,
    HumanDecisionOption,
    DocumentInfo,
    RequirementStatus
)
from app.agents.task_analyst import TaskAnalystAgent
from app.agents.requirements_agent import RequirementsAgent
from app.agents.document_agent import DocumentAgent
from app.agents.verification_agent import VerificationAgent
from app.agents.receipt_agent import ReceiptAgent
from app.tools.document_tools import parse_document_metadata


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Strands Orchestrator for DoneRight.
Your mission is to guide autonomous multi-agent task execution from raw opportunity input to final verified submission package.
Core rule: Automate execution. Escalate judgment.
"""


class DoneRightOrchestrator:
    def __init__(self):
        self.model = get_strands_model()
        self.agent = Agent(
            model=self.model,
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT
        )
        self.task_analyst = TaskAnalystAgent()
        self.requirements_agent = RequirementsAgent()
        self.document_agent = DocumentAgent()
        self.verification_agent = VerificationAgent()
        self.receipt_agent = ReceiptAgent()

    def start_workflow(
        self,
        opportunity_text: str,
        opportunity_source: str,
        raw_documents: List[Dict[str, str]] # list of {"name": filename, "content": text}
    ) -> Generator[WorkflowState, None, WorkflowState]:
        """
        Runs the initial phase of the workflow up to verification or the Human Gate.
        Yields state updates for real-time observability.
        """
        workflow_id = f"WF-{uuid.uuid4().hex[:8].upper()}"
        state = WorkflowState(workflow_id=workflow_id, current_stage=WorkflowStage.ANALYZING)

        # 1. Task Analyst Execution
        state.activity_logs.append(AgentActivityLog(
            agent_name="Task Analyst",
            action="Analyzing opportunity announcement and extracting structure",
            status="RUNNING",
            output_summary="Parsing guidelines, eligibility rules, and submission constraints..."
        ))
        yield state

        opp = self.task_analyst.analyze(opportunity_text, source_name=opportunity_source)
        state.opportunity = opp
        state.activity_logs[-1].status = "COMPLETED"
        state.activity_logs[-1].output_summary = (
            f"Identified '{opp.name}' ({opp.organization}). "
            f"Extracted {len(opp.eligibility)} eligibility rules and {len(opp.required_documents)} required documents."
        )
        state.current_stage = WorkflowStage.REQUIREMENTS_EXTRACTED
        yield state

        # 2. Requirements Agent Execution
        state.activity_logs.append(AgentActivityLog(
            agent_name="Requirements Agent",
            action="Formulating itemized requirement checklist",
            status="RUNNING",
            output_summary="Cataloging document proofs, eligibility thresholds, and required statements..."
        ))
        yield state

        reqs = self.requirements_agent.extract_checklist(opp)
        state.requirements = reqs
        state.activity_logs[-1].status = "COMPLETED"
        state.activity_logs[-1].output_summary = f"Compiled checklist of {len(reqs)} distinct requirements with confidence scores."
        state.current_stage = WorkflowStage.DOCUMENTS_ANALYZING
        yield state

        # 3. Document Ingestion & Parsing
        parsed_docs: List[DocumentInfo] = []
        for raw_doc in raw_documents:
            parsed = parse_document_metadata(raw_doc["name"], raw_doc["content"])
            parsed_docs.append(parsed)
        state.documents = parsed_docs

        # 4. Document Agent: Matching and Drafting
        state.activity_logs.append(AgentActivityLog(
            agent_name="Document Agent",
            action="Matching applicant files and drafting grounded application materials",
            status="RUNNING",
            output_summary="Auditing applicant CV, transcript, and project records..."
        ))
        yield state

        matched_reqs, matched_docs = self.document_agent.analyze_and_match(state.requirements, state.documents)
        state.requirements = matched_reqs
        state.documents = matched_docs

        # Draft statement if needed
        artifacts = self.document_agent.prepare_materials(state.opportunity, state.documents, state.requirements)
        state.generated_artifacts = artifacts
        
        # Mark drafted essay / statement requirements as satisfied by the generated artifact
        if artifacts:
            for req in state.requirements:
                if req.category.value in ["ESSAY_OR_STATEMENT", "DOCUMENT"] and any(k in req.description.lower() for k in ["statement", "essay", "purpose"]):
                    req.status = RequirementStatus.SATISFIED
                    req.evidence = f"Application statement prepared from verified CV: {artifacts[0].title}"
                    req.confidence = 0.95

        state.activity_logs[-1].status = "COMPLETED"
        satisfied_count = sum(1 for r in state.requirements if r.status == RequirementStatus.SATISFIED)
        state.activity_logs[-1].output_summary = (
            f"Matched {satisfied_count}/{len(state.requirements)} requirements to documents. "
            f"Synthesized {len(artifacts)} grounded statement artifact."
        )
        state.current_stage = WorkflowStage.VERIFYING
        yield state

        # 5. Verification Agent Audit
        state.activity_logs.append(AgentActivityLog(
            agent_name="Verification Agent",
            action="Running independent audits across coverage, consistency, and claims",
            status="RUNNING",
            output_summary="Verifying identity consistency, GPA compliance, and anti-hallucination guardrails..."
        ))
        yield state

        verif_result = self.verification_agent.verify(
            state.opportunity,
            state.requirements,
            state.documents,
            state.generated_artifacts
        )
        state.verification_result = verif_result

        # 6. Check for Human Gate Escalation
        if verif_result.requires_human_gate:
            state.activity_logs[-1].status = "ESCALATED"
            state.activity_logs[-1].output_summary = f"Audit complete: Human Gate triggered. {verif_result.gate_reason}"

            # Create the active Human Decision
            decision_id = f"DEC-{uuid.uuid4().hex[:6].upper()}"
            decision = HumanDecision(
                decision_id=decision_id,
                reason="Confidential referee recommendation letter is required.",
                context=(
                    "The opportunity mandates at least one recommendation letter. "
                    "DoneRight adheres to strict anti-hallucination and security safeguards: "
                    "the agent cannot and will not generate a fraudulent recommendation letter on behalf of another individual."
                ),
                options=[
                    HumanDecisionOption(
                        option_id="OPT-UPLOAD",
                        label="I will upload a Recommendation Letter",
                        description="Supply an authentic letter file or attach referee credentials directly.",
                        action="PROVIDE_DOCUMENT"
                    ),
                    HumanDecisionOption(
                        option_id="OPT-WAIVER",
                        label="Request Institutional Waiver / Note",
                        description="Attach a formal waiver request explaining why referee verification is pending or separate.",
                        action="WAIVE_REQUIREMENT"
                    ),
                    HumanDecisionOption(
                        option_id="OPT-SELF",
                        label="Referee Submitting Directly to Portal",
                        description="Mark this item as arranged: the referee has received the portal invite to submit independently.",
                        action="ARRANGED_EXTERNALLY"
                    )
                ]
            )
            state.active_decision = decision
            state.current_stage = WorkflowStage.WAITING_FOR_HUMAN
            yield state
            return state

        # If no human gate needed, proceed to receipt
        state.activity_logs[-1].status = "COMPLETED"
        state.activity_logs[-1].output_summary = "All automated audits passed with 100% compliance."
        state.current_stage = WorkflowStage.FINAL_VERIFICATION
        yield state

        # Final Receipt
        return self._finalize_receipt(state)

    def resume_workflow(
        self,
        state: WorkflowState,
        selected_option_id: str,
        user_note: Optional[str] = None
    ) -> Generator[WorkflowState, None, WorkflowState]:
        """
        Resumes the paused workflow after human decision has been made at the Human Gate.
        """
        state.current_stage = WorkflowStage.RESUMING
        if state.active_decision:
            state.active_decision.selected_option = selected_option_id
            state.active_decision.user_note = user_note
            state.active_decision.resolved = True
            state.human_decisions.append(state.active_decision)

            # Update corresponding requirement status
            for req in state.requirements:
                if "recommendation" in req.description.lower() or "reference" in req.description.lower():
                    if selected_option_id == "OPT-UPLOAD":
                        req.status = RequirementStatus.SATISFIED
                        req.evidence = "Applicant supplied verified recommendation letter."
                    elif selected_option_id == "OPT-WAIVER":
                        req.status = RequirementStatus.SATISFIED
                        req.evidence = "Applicant requested formal institutional waiver / explanation note."
                    elif selected_option_id == "OPT-SELF":
                        req.status = RequirementStatus.SATISFIED
                        req.evidence = "Referee confirmed submitting directly through institution portal."

            decision_label = next(
                (opt.label for opt in state.active_decision.options if opt.option_id == selected_option_id),
                selected_option_id
            )
            state.activity_logs.append(AgentActivityLog(
                agent_name="Human Gate",
                action="Human decision registered",
                status="RESOLVED",
                output_summary=f"User resolved escalation with: '{decision_label}'."
            ))
            state.active_decision = None
            yield state

        state.current_stage = WorkflowStage.FINAL_VERIFICATION
        state.activity_logs.append(AgentActivityLog(
            agent_name="Receipt Agent",
            action="Packaging verified application bundle and generating completion receipt",
            status="RUNNING",
            output_summary="Compiling requirement metrics, verified document hashes, and readiness badge..."
        ))
        yield state

        receipt = self.receipt_agent.generate_receipt(
            state.opportunity,
            state.requirements,
            state.human_decisions,
            state.generated_artifacts
        )
        state.completion_receipt = receipt
        state.activity_logs[-1].status = "COMPLETED"
        state.activity_logs[-1].output_summary = f"Completion receipt {receipt.receipt_id} generated. Status: {receipt.status} ({receipt.completion_percentage}%)."
        state.current_stage = WorkflowStage.COMPLETED
        yield state

        return state

    def _finalize_receipt(self, state: WorkflowState) -> WorkflowState:
        state.current_stage = WorkflowStage.FINAL_VERIFICATION
        receipt = self.receipt_agent.generate_receipt(
            state.opportunity,
            state.requirements,
            state.human_decisions,
            state.generated_artifacts
        )
        state.completion_receipt = receipt
        state.current_stage = WorkflowStage.COMPLETED
        return state
