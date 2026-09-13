from pathlib import Path
from app.models.schemas import (
    Opportunity,
    RequirementStatus,
    DocumentType,
    VerificationCheckStatus
)
from app.tools.document_tools import parse_document_metadata
from app.tools.requirement_tools import (
    generate_initial_requirements_from_opportunity,
    match_documents_to_requirements
)
from app.tools.verification_tools import verify_application_package
from app.tools.artifact_tools import compile_completion_receipt, draft_personal_statement_grounded


def test_document_metadata_parsing():
    sample_cv = """# Curriculum Vitae
Name: Alex Rivera
Email: alex@example.com
Education: Bachelor of Science in Computer Science
Cumulative GPA: 3.82 / 4.00
Experience: 2024 - 2025 Sensor Mesh Lead
"""
    doc_info = parse_document_metadata("cv_alex.md", sample_cv)
    assert doc_info.doc_type == DocumentType.CV
    assert doc_info.extracted_information.get("candidate_name") == "Alex Rivera"
    assert doc_info.extracted_information.get("gpa") == 3.82


def test_requirement_generation_and_matching():
    opp = Opportunity(
        name="Test Fellowship",
        organization="Test Org",
        deadline="2026-12-01",
        eligibility=["Minimum GPA of 3.5 on 4.0 scale"],
        required_documents=["Curriculum Vitae (CV)", "Official Transcript", "Letter of Recommendation"],
        source="test"
    )

    reqs = generate_initial_requirements_from_opportunity(opp)
    assert len(reqs) == 4 # 1 eligibility + 3 required docs

    # Create dummy documents
    cv_info = parse_document_metadata("cv.md", "Name: Alex Rivera\nCurriculum Vitae\nExperience in Python")
    tr_info = parse_document_metadata("transcript.md", "Candidate Name: Alex Rivera\nTranscript\nCumulative GPA: 3.82")

    matched_reqs, matched_docs = match_documents_to_requirements(reqs, [cv_info, tr_info])

    # Check that CV & Transcript are satisfied, but Recommendation is MISSING
    cv_req = next(r for r in matched_reqs if "cv" in r.description.lower())
    tr_req = next(r for r in matched_reqs if "transcript" in r.description.lower())
    rec_req = next(r for r in matched_reqs if "recommendation" in r.description.lower())

    assert cv_req.status == RequirementStatus.SATISFIED
    assert tr_req.status == RequirementStatus.SATISFIED
    assert rec_req.status == RequirementStatus.MISSING


def test_verification_agent_human_gate_trigger():
    opp = Opportunity(
        name="Test Fellowship",
        organization="Test Org",
        deadline="2026-12-01",
        eligibility=["Minimum GPA 3.5"],
        required_documents=["Curriculum Vitae", "Recommendation Letter"]
    )
    reqs = generate_initial_requirements_from_opportunity(opp)
    cv_info = parse_document_metadata("cv.md", "Name: Alex Rivera\nCurriculum Vitae")
    matched_reqs, matched_docs = match_documents_to_requirements(reqs, [cv_info])

    result = verify_application_package(opp, matched_reqs, matched_docs, [])

    # Must flag that a human gate is required due to missing recommendation letter
    assert result.requires_human_gate is True
    assert result.overall_status == "READY_WITH_HUMAN_DECISION"
    assert "Recommendation Letter" in result.gate_reason


def test_artifact_grounding_and_receipt():
    statement = draft_personal_statement_grounded(
        candidate_name="Alex Rivera",
        target_opportunity="Test Fellowship",
        key_achievements=["Led 24-node sensor project"],
        research_interests=["Distributed Systems"]
    )
    assert "Alex Rivera" in statement.content
    assert "Led 24-node sensor project" in statement.content

    receipt = compile_completion_receipt(None, [], [], [statement])
    assert receipt.completion_percentage == 100
    assert "ART-SOP" in statement.artifact_id or "ART-" in statement.artifact_id
