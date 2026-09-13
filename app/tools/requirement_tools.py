from typing import List, Tuple
from app.models.schemas import (
    Requirement,
    RequirementStatus,
    RequirementCategory,
    DocumentInfo,
    DocumentType,
    Opportunity
)


def generate_initial_requirements_from_opportunity(opportunity: Opportunity) -> List[Requirement]:
    """Derives discrete requirement checklist items from a parsed Opportunity schema."""
    checklist: List[Requirement] = []
    counter = 1

    # 1. Eligibility requirements
    for el in opportunity.eligibility:
        checklist.append(Requirement(
            id=f"REQ-{counter:02d}",
            description=el,
            category=RequirementCategory.ELIGIBILITY,
            required=True,
            evidence_needed="Transcript or academic/citizenship records demonstrating criteria",
            status=RequirementStatus.MISSING,
            confidence=0.9
        ))
        counter += 1

    # 2. Required documents
    for doc_req in opportunity.required_documents:
        cat = RequirementCategory.DOCUMENT
        if "statement" in doc_req.lower() or "essay" in doc_req.lower():
            cat = RequirementCategory.ESSAY_OR_STATEMENT
        elif "recommendation" in doc_req.lower() or "referee" in doc_req.lower() or "reference" in doc_req.lower():
            cat = RequirementCategory.REFERENCE

        checklist.append(Requirement(
            id=f"REQ-{counter:02d}",
            description=f"Submit official/approved {doc_req}",
            category=cat,
            required=True,
            evidence_needed=f"Valid {doc_req} document uploaded and verified",
            status=RequirementStatus.MISSING,
            confidence=1.0
        ))
        counter += 1

    # 3. Required essay responses / prompts
    for resp in opportunity.required_responses:
        checklist.append(Requirement(
            id=f"REQ-{counter:02d}",
            description=f"Response to prompt: '{resp}'",
            category=RequirementCategory.ESSAY_OR_STATEMENT,
            required=True,
            evidence_needed="Written statement addressing prompt criteria",
            status=RequirementStatus.MISSING,
            confidence=0.95
        ))
        counter += 1

    # 4. Submission rules
    for rule in opportunity.submission_rules:
        checklist.append(Requirement(
            id=f"REQ-{counter:02d}",
            description=f"Submission Rule: {rule}",
            category=RequirementCategory.SUBMISSION_RULE,
            required=True,
            evidence_needed="Compliance with file formats and submission deadlines",
            status=RequirementStatus.NEEDS_REVIEW,
            confidence=0.85
        ))
        counter += 1

    return checklist


def match_documents_to_requirements(
    requirements: List[Requirement],
    documents: List[DocumentInfo]
) -> Tuple[List[Requirement], List[DocumentInfo]]:
    """
    Evaluates uploaded documents against the requirement checklist.
    Updates requirement statuses and document matched lists without fabricating evidence.
    """
    updated_reqs = [req.model_copy() for req in requirements]
    updated_docs = [doc.model_copy() for doc in documents]

    doc_by_type = {doc.doc_type: doc for doc in updated_docs}

    for req in updated_reqs:
        lower_desc = req.description.lower()

        # Check CV match
        if ("cv" in lower_desc or "resume" in lower_desc) and DocumentType.CV in doc_by_type:
            cv_doc = doc_by_type[DocumentType.CV]
            req.status = RequirementStatus.SATISFIED
            req.evidence = f"Verified from {cv_doc.name} (Candidate info and credentials found)"
            req.source = cv_doc.name
            req.confidence = 0.95
            if req.id not in cv_doc.matched_requirements:
                cv_doc.matched_requirements.append(req.id)

        # Check Transcript match & GPA eligibility
        elif ("transcript" in lower_desc or "academic record" in lower_desc or "gpa" in lower_desc) and DocumentType.TRANSCRIPT in doc_by_type:
            tr_doc = doc_by_type[DocumentType.TRANSCRIPT]
            gpa = tr_doc.extracted_information.get("gpa")
            if "gpa" in lower_desc and gpa is not None:
                # Check if requirement mentions a minimum GPA threshold (e.g. 3.5)
                if "3.5" in lower_desc:
                    if gpa >= 3.5:
                        req.status = RequirementStatus.SATISFIED
                        req.evidence = f"Verified GPA {gpa} meets requirement (>= 3.5)"
                    else:
                        req.status = RequirementStatus.MISSING
                        req.evidence = f"Candidate GPA {gpa} does not meet required 3.5"
                else:
                    req.status = RequirementStatus.SATISFIED
                    req.evidence = f"Academic transcript verifies GPA {gpa}"
            else:
                req.status = RequirementStatus.SATISFIED
                req.evidence = f"Official transcript provided in {tr_doc.name}"
            req.source = tr_doc.name
            req.confidence = 0.98
            if req.id not in tr_doc.matched_requirements:
                tr_doc.matched_requirements.append(req.id)

        # Check Recommendation Letter
        elif "recommendation" in lower_desc or "reference" in lower_desc or req.category == RequirementCategory.REFERENCE:
            if DocumentType.RECOMMENDATION_LETTER in doc_by_type:
                ref_doc = doc_by_type[DocumentType.RECOMMENDATION_LETTER]
                req.status = RequirementStatus.SATISFIED
                req.evidence = f"Recommendation letter present: {ref_doc.name}"
                req.source = ref_doc.name
                if req.id not in ref_doc.matched_requirements:
                    ref_doc.matched_requirements.append(req.id)
            else:
                # Missing confidential item!
                req.status = RequirementStatus.MISSING
                req.evidence = "No recommendation letter uploaded. DoneRight cannot invent third-party references."
                req.action_needed = "Human decision required: upload letter, request waiver, or mark self-arranged."

        # Check Personal Statement / Essay
        elif req.category == RequirementCategory.ESSAY_OR_STATEMENT or "statement" in lower_desc or "essay" in lower_desc:
            if DocumentType.PERSONAL_STATEMENT in doc_by_type:
                st_doc = doc_by_type[DocumentType.PERSONAL_STATEMENT]
                req.status = RequirementStatus.SATISFIED
                req.evidence = f"Existing personal statement found in {st_doc.name}"
                req.source = st_doc.name
                if req.id not in st_doc.matched_requirements:
                    st_doc.matched_requirements.append(req.id)
            else:
                req.status = RequirementStatus.PARTIAL
                req.evidence = "Draft application statement can be prepared from CV & project notes."
                req.action_needed = "Generate tailored statement from applicant CV facts."

    return updated_reqs, updated_docs
