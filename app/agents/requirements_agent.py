import json
import re
from typing import List
from strands import Agent
from app.config import get_strands_model
from app.models.schemas import Opportunity, Requirement, RequirementStatus, RequirementCategory
from app.tools.requirement_tools import generate_initial_requirements_from_opportunity


REQUIREMENTS_AGENT_SYSTEM_PROMPT = """You are the Requirements Agent for DoneRight.
Your purpose is to turn an application opportunity into a rigorous, itemized checklist.
For each requirement, evaluate:
- id: e.g. REQ-01, REQ-02
- description: clear, actionable requirement description
- category: ELIGIBILITY, DOCUMENT, ESSAY_OR_STATEMENT, SUBMISSION_RULE, REFERENCE, or OTHER
- required: boolean (true for mandatory, false for optional)
- evidence_needed: what concrete document or verification proves fulfillment
- status: SATISFIED, MISSING, PARTIAL, NEEDS_REVIEW, or NOT_APPLICABLE
- confidence: float 0.0 to 1.0

Rules:
- Separate items cleanly.
- Flag confidential third-party items (such as recommendation letters) with category REFERENCE.
- Distinguish between what can be verified automatically vs. what requires human input or generation.
"""


class RequirementsAgent:
    def __init__(self):
        self.model = get_strands_model()
        self.agent = Agent(
            model=self.model,
            system_prompt=REQUIREMENTS_AGENT_SYSTEM_PROMPT
        )

    def extract_checklist(self, opportunity: Opportunity) -> List[Requirement]:
        """Derives and refines the complete requirements checklist for an opportunity."""
        # Baseline deterministic extraction
        base_checklist = generate_initial_requirements_from_opportunity(opportunity)

        # Call Strands agent to refine checklist descriptions and required evidence
        prompt = (
            f"Review this parsed opportunity and enhance the checklist items for completeness:\n"
            f"Opportunity: {opportunity.name}\n"
            f"Organization: {opportunity.organization}\n"
            f"Eligibility: {opportunity.eligibility}\n"
            f"Required Documents: {opportunity.required_documents}\n"
            f"Essays: {opportunity.required_responses}\n\n"
            f"Provide any additional granular requirements if needed in JSON format, or return 'CHECKLIST_CONFIRMED'."
        )

        try:
            response = self.agent(prompt)
            text = str(response)
            if "CHECKLIST_CONFIRMED" not in text:
                json_match = re.search(r'\[.*\]', text, re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group(0))
                    refined = []
                    for idx, item in enumerate(items, 1):
                        refined.append(Requirement(
                            id=item.get("id", f"REQ-{idx:02d}"),
                            description=item.get("description", ""),
                            category=RequirementCategory(item.get("category", "DOCUMENT")),
                            required=item.get("required", True),
                            evidence_needed=item.get("evidence_needed", "Documentation"),
                            status=RequirementStatus(item.get("status", "MISSING")),
                            confidence=float(item.get("confidence", 0.95))
                        ))
                    if refined:
                        return refined
        except Exception:
            pass

        return base_checklist
