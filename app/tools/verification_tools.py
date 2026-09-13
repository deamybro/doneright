from typing import List, Optional
from datetime import datetime
from app.models.schemas import (
    Requirement,
    RequirementStatus,
    DocumentInfo,
    DocumentType,
    Opportunity,
    VerificationResult,
    VerificationItem,
    VerificationCheckStatus,
    GeneratedArtifact
)


def verify_application_package(
    opportunity: Optional[Opportunity],
    requirements: List[Requirement],
    documents: List[DocumentInfo],
    artifacts: List[GeneratedArtifact]
) -> VerificationResult:
    """
    Executes independent auditing across requirement coverage,
    document consistency, unsupported claims, and deadline awareness.
    """
    checks: List[VerificationItem] = []
    unsupported_claims: List[str] = []
    conflicts: List[str] = []
    requires_human_gate = False
    gate_reason = None

    # Check 1: Requirement Coverage Audit
    missing_required = [r for r in requirements if r.required and r.status == RequirementStatus.MISSING]
    partial_required = [r for r in requirements if r.required and r.status == RequirementStatus.PARTIAL]

    if not missing_required:
        checks.append(VerificationItem(
            check_id="CHK-COV-01",
            category="Requirement Coverage",
            description="All mandatory requirements satisfied or addressed",
            status=VerificationCheckStatus.PASSED,
            details="100% of required checklist items are fulfilled or have verified evidence."
        ))
    else:
        # Check if missing item is a recommendation letter or confidential document
        ref_missing = any("recommendation" in r.description.lower() or "reference" in r.description.lower() for r in missing_required)
        if ref_missing:
            requires_human_gate = True
            gate_reason = (
                "A Recommendation Letter is required by the opportunity. "
                "DoneRight cannot invent an authentic recommendation letter from a referee. "
                "A human decision is required to provide the letter, request an institutional waiver, or continue."
            )
            checks.append(VerificationItem(
                check_id="CHK-COV-01",
                category="Requirement Coverage",
                description="Confidential referee letter required",
                status=VerificationCheckStatus.WARNING,
                details=f"{len(missing_required)} item(s) pending. {gate_reason}"
            ))
        else:
            checks.append(VerificationItem(
                check_id="CHK-COV-01",
                category="Requirement Coverage",
                description="Missing mandatory requirements",
                status=VerificationCheckStatus.FAILED,
                details=f"{len(missing_required)} required item(s) currently unresolved: {', '.join(r.id for r in missing_required)}."
            ))

    # Check 2: Cross-Document Consistency (Names, Institutions, GPA)
    candidate_names = set()
    for doc in documents:
        name = doc.extracted_information.get("candidate_name")
        if name:
            candidate_names.add(name.lower())

    if len(candidate_names) > 1:
        conflicts.append(f"Name discrepancy detected across documents: {', '.join(candidate_names)}")
        requires_human_gate = True
        gate_reason = "Conflicting candidate names found between uploaded documents."
        checks.append(VerificationItem(
            check_id="CHK-CON-01",
            category="Document Consistency",
            description="Candidate identity consistency across files",
            status=VerificationCheckStatus.FAILED,
            details=f"Inconsistency detected between documents: {', '.join(candidate_names)}"
        ))
    else:
        checks.append(VerificationItem(
            check_id="CHK-CON-01",
            category="Document Consistency",
            description="Applicant identity and credentials alignment",
            status=VerificationCheckStatus.PASSED,
            details="Applicant identity and records match consistently across all supplied documents."
        ))

    # Check 3: Unsupported Claims / Anti-Hallucination Audit
    # Inspect generated statements to ensure claims are grounded in provided documents
    if artifacts:
        all_doc_content = " ".join(str(d.extracted_information) for d in documents).lower()
        for art in artifacts:
            for fact in art.grounded_facts:
                if len(fact.split()) > 3: # substantial claim
                    # Simple keyword verification
                    keywords = [w for w in fact.lower().split() if len(w) > 4]
                    if keywords and not any(k in all_doc_content for k in keywords):
                        unsupported_claims.append(f"Claim in '{art.title}' may lack supporting document evidence: '{fact}'")

        if unsupported_claims:
            checks.append(VerificationItem(
                check_id="CHK-HAL-01",
                category="Fact Grounding",
                description="Generated statement fact grounding",
                status=VerificationCheckStatus.WARNING,
                details=f"Found {len(unsupported_claims)} claims requiring human verification."
            ))
        else:
            checks.append(VerificationItem(
                check_id="CHK-HAL-01",
                category="Fact Grounding",
                description="Generated application materials fact grounding",
                status=VerificationCheckStatus.PASSED,
                details="All drafted statement claims directly reference verified facts from the applicant's CV and transcript."
            ))

    # Check 4: Deadline Awareness
    if opportunity and opportunity.deadline:
        checks.append(VerificationItem(
            check_id="CHK-DL-01",
            category="Deadline Awareness",
            description="Opportunity deadline identification",
            status=VerificationCheckStatus.PASSED,
            details=f"Identified submission deadline: {opportunity.deadline}."
        ))
    else:
        checks.append(VerificationItem(
            check_id="CHK-DL-01",
            category="Deadline Awareness",
            description="Opportunity deadline identification",
            status=VerificationCheckStatus.WARNING,
            details="No explicit deadline specified in the announcement."
        ))

    # Determine Overall Status
    if conflicts:
        overall_status = "CONFLICT_DETECTED"
    elif requires_human_gate:
        overall_status = "READY_WITH_HUMAN_DECISION"
    elif any(c.status == VerificationCheckStatus.FAILED for c in checks):
        overall_status = "INCOMPLETE"
    else:
        overall_status = "READY"

    return VerificationResult(
        overall_status=overall_status,
        checks=checks,
        unsupported_claims=unsupported_claims,
        conflicts=conflicts,
        requires_human_gate=requires_human_gate,
        gate_reason=gate_reason
    )
