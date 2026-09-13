from typing import List, Optional
from strands import Agent
from app.config import get_strands_model
from app.models.schemas import (
    Opportunity,
    Requirement,
    HumanDecision,
    GeneratedArtifact,
    CompletionReceipt
)
from app.tools.artifact_tools import compile_completion_receipt


RECEIPT_AGENT_SYSTEM_PROMPT = """You are the Action / Receipt Agent for DoneRight.
Your purpose is to compile the official Completion Receipt for the opportunity preparation task.

The receipt must clearly reflect:
1. Exact preparation status (READY FOR SUBMISSION, READY WITH WAIVER, etc.)
2. Readiness score / completion percentage
3. Verified checklist items
4. Human decisions that were escalated and resolved
5. Any remaining actions the human applicant must take manually

Maintain an authoritative, transparent, and encouraging tone.
"""


class ReceiptAgent:
    def __init__(self):
        self.model = get_strands_model()
        self.agent = Agent(
            model=self.model,
            system_prompt=RECEIPT_AGENT_SYSTEM_PROMPT
        )

    def generate_receipt(
        self,
        opportunity: Optional[Opportunity],
        requirements: List[Requirement],
        human_decisions: List[HumanDecision],
        artifacts: List[GeneratedArtifact]
    ) -> CompletionReceipt:
        """Constructs the official DoneRight completion receipt."""
        receipt = compile_completion_receipt(opportunity, requirements, human_decisions, artifacts)

        prompt = (
            f"Generate an executive summary for this completed task:\n"
            f"Opportunity: {receipt.opportunity_name}\n"
            f"Completion Score: {receipt.completion_percentage}%\n"
            f"Verified Items: {len(receipt.verified_items)}\n"
            f"Human Decisions Resolved: {receipt.waived_or_human_resolved_count}\n"
            f"Status: {receipt.status}\n\n"
            f"Provide a concise, 2-sentence executive summary for the completion receipt."
        )

        try:
            summary = str(self.agent(prompt)).strip()
            if summary and len(summary) > 20:
                receipt.summary = summary
        except Exception:
            pass

        return receipt
