from typing import List, Optional
from strands import Agent
from app.config import get_strands_model
from app.models.schemas import (
    Opportunity,
    Requirement,
    DocumentInfo,
    GeneratedArtifact,
    VerificationResult
)
from app.tools.verification_tools import verify_application_package


VERIFICATION_AGENT_SYSTEM_PROMPT = """You are the independent Verification Agent for DoneRight.
Your role is to critically audit the candidate's application package before submission.

AUDIT CRITERIA:
1. Requirement Coverage: Has every single required item been fulfilled or accounted for?
2. Document Consistency: Do candidate names, institutions, graduation dates, and GPAs match across all uploaded files?
3. Fact Grounding & Hallucination: Do any statements make claims not substantiated by the applicant's records?
4. Human Escalation: If an authentic third-party document (e.g. referee recommendation) is missing, escalate immediately to the Human Gate. Never attempt to bypass referee requirements autonomously.

Always maintain strict objectivity. Escalate genuine judgment calls to the human.
"""


class VerificationAgent:
    def __init__(self):
        self.model = get_strands_model()
        self.agent = Agent(
            model=self.model,
            system_prompt=VERIFICATION_AGENT_SYSTEM_PROMPT
        )

    def verify(
        self,
        opportunity: Optional[Opportunity],
        requirements: List[Requirement],
        documents: List[DocumentInfo],
        artifacts: List[GeneratedArtifact]
    ) -> VerificationResult:
        """Runs the complete verification audit and returns structured VerificationResult."""
        # Baseline deterministic audit
        result = verify_application_package(opportunity, requirements, documents, artifacts)

        # Let Strands agent inspect edge cases or summarize
        prompt = (
            f"Audit summary:\n"
            f"Overall Status: {result.overall_status}\n"
            f"Requires Human Gate: {result.requires_human_gate}\n"
            f"Gate Reason: {result.gate_reason}\n"
            f"Checks: {[f'{c.category}: {c.status.value}' for c in result.checks]}\n\n"
            f"Confirm or refine audit conclusions. If human gate is needed, state the exact escalation rationale."
        )

        try:
            agent_response = self.agent(prompt)
            # Retain the structured result, enriching gate reason if relevant
            if result.requires_human_gate and not result.gate_reason:
                result.gate_reason = str(agent_response)
        except Exception:
            pass

        return result
