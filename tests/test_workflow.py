from pathlib import Path
from app.agents.orchestrator import DoneRightOrchestrator
from app.models.schemas import WorkflowStage
from app.tools.document_tools import extract_text_from_file


def test_end_to_end_orchestrator_human_gate_and_resume():
    root = Path(__file__).resolve().parent.parent
    opp_text = extract_text_from_file(root / "demo" / "opportunity" / "fellowship_announcement.md")
    cv_text = extract_text_from_file(root / "demo" / "documents" / "cv_alex_rivera.md")
    tr_text = extract_text_from_file(root / "demo" / "documents" / "transcript_alex_rivera.md")

    raw_docs = [
        {"name": "cv_alex_rivera.md", "content": cv_text},
        {"name": "transcript_alex_rivera.md", "content": tr_text}
    ]

    orchestrator = DoneRightOrchestrator()

    # Step 1: Start workflow up to Human Gate
    state_generator = orchestrator.start_workflow(
        opportunity_text=opp_text,
        opportunity_source="demo_fellowship",
        raw_documents=raw_docs
    )

    final_paused_state = None
    for state in state_generator:
        final_paused_state = state

    # Assert that the workflow correctly paused at Human Gate
    assert final_paused_state is not None
    assert final_paused_state.current_stage == WorkflowStage.WAITING_FOR_HUMAN
    assert final_paused_state.active_decision is not None
    assert len(final_paused_state.active_decision.options) == 3

    # Step 2: Resume workflow with human decision
    resume_generator = orchestrator.resume_workflow(
        state=final_paused_state,
        selected_option_id="OPT-SELF",
        user_note="Referee has confirmed submission via direct institutional portal."
    )

    completed_state = None
    for state in resume_generator:
        completed_state = state

    # Assert that workflow completed and receipt was generated
    assert completed_state is not None
    assert completed_state.current_stage == WorkflowStage.COMPLETED
    assert completed_state.completion_receipt is not None
    assert completed_state.completion_receipt.completion_percentage >= 70
    assert len(completed_state.completion_receipt.verified_items) > 0
