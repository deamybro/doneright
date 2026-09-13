import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import time
from typing import List, Dict

from app.models.schemas import WorkflowStage, WorkflowState, RequirementStatus
from app.agents.orchestrator import DoneRightOrchestrator
from app.tools.document_tools import extract_text_from_file

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="DoneRight — Autonomous Task-Completion Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling: Executive Obsidian & Champagne Bronze Aesthetic
EXECUTIVE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #E2E8F0;
}

/* Background */
.stApp {
    background-color: #0B0D11;
}

/* Top App Header */
.doneright-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem 1.5rem;
    background: #11141B;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 2rem;
}
.doneright-logo {
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: #FFFFFF;
}
.doneright-tagline {
    font-size: 0.875rem;
    color: #94A3B8;
    margin-top: 0.2rem;
}
.status-pill {
    padding: 0.35rem 0.9rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.pill-active {
    background: rgba(212, 175, 55, 0.15);
    color: #E5C07B;
    border: 1px solid rgba(212, 175, 55, 0.4);
}
.pill-waiting {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.4);
}
.pill-done {
    background: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.4);
}

/* Cards */
.executive-card {
    background: #12151D;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}
.telemetry-card {
    background: #12151D;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}
.card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #F8FAFC;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.card-subtitle {
    font-size: 0.85rem;
    color: #94A3B8;
    margin-bottom: 1rem;
}

/* Human Gate Escalation Card */
.human-gate-card {
    background: linear-gradient(180deg, #17161A 0%, #13141A 100%);
    border: 1px solid #D4AF37;
    border-radius: 14px;
    padding: 1.75rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 0 25px rgba(212, 175, 55, 0.08);
}
.human-gate-tag {
    color: #E5C07B;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
.human-gate-title {
    font-size: 1.35rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 0.75rem;
}
.human-gate-body {
    font-size: 0.92rem;
    line-height: 1.5;
    color: #CBD5E1;
    margin-bottom: 1.25rem;
}

/* Custom Scrollbar for Containers */
div[data-testid="stVerticalBlock"] > div[style*="overflow"]::-webkit-scrollbar {
    width: 6px;
}
div[data-testid="stVerticalBlock"] > div[style*="overflow"]::-webkit-scrollbar-track {
    background: #0B0D11;
}
div[data-testid="stVerticalBlock"] > div[style*="overflow"]::-webkit-scrollbar-thumb {
    background: rgba(212, 175, 55, 0.35);
    border-radius: 4px;
}
div[data-testid="stVerticalBlock"] > div[style*="overflow"]::-webkit-scrollbar-thumb:hover {
    background: rgba(212, 175, 55, 0.7);
}

/* Receipt Card */
.receipt-header {
    text-align: center;
    border-bottom: 1px dashed rgba(255, 255, 255, 0.15);
    padding-bottom: 1rem;
    margin-bottom: 1.25rem;
}
.receipt-title {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #FFFFFF;
}
.receipt-meta {
    font-size: 0.8rem;
    color: #94A3B8;
}
.gauge-box {
    text-align: center;
    padding: 1rem;
    background: #0D1017;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    margin-bottom: 1.25rem;
}
.gauge-score {
    font-size: 2.5rem;
    font-weight: 800;
    color: #E5C07B;
}
.gauge-label {
    font-size: 0.8rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Checkmarks */
.verified-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0;
    font-size: 0.9rem;
    color: #E2E8F0;
}
.check-icon {
    color: #34D399;
    font-weight: bold;
}
</style>
"""
st.markdown(EXECUTIVE_CSS, unsafe_allow_html=True)

# Initialize Session State
if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = None
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = DoneRightOrchestrator()
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = False
if "opportunity_input" not in st.session_state:
    st.session_state.opportunity_input = ""
if "raw_docs" not in st.session_state:
    st.session_state.raw_docs = []

# Header Component
state_label = "Ready to Start"
state_class = "pill-active"
if st.session_state.workflow_state:
    curr = st.session_state.workflow_state.current_stage
    if curr == WorkflowStage.WAITING_FOR_HUMAN:
        state_label = "Waiting for Human Decision"
        state_class = "pill-waiting"
    elif curr == WorkflowStage.COMPLETED:
        state_label = "Verified & Completed"
        state_class = "pill-done"
    else:
        state_label = f"Working: {curr.value}"
        state_class = "pill-active"

st.markdown(f"""
<div class="doneright-header">
    <div>
        <div class="doneright-logo">DoneRight</div>
        <div class="doneright-tagline">Give it the task. DoneRight gets it done.</div>
    </div>
    <div>
        <span class="status-pill {state_class}">{state_label}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Load Demo Preset Helper
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
def load_demo_scenario():
    opp_path = ROOT_DIR / "demo" / "opportunity" / "fellowship_announcement.md"
    cv_path = ROOT_DIR / "demo" / "documents" / "cv_alex_rivera.md"
    tr_path = ROOT_DIR / "demo" / "documents" / "transcript_alex_rivera.md"
    proj_path = ROOT_DIR / "demo" / "documents" / "project_summary.md"

    st.session_state.opportunity_input = extract_text_from_file(opp_path)
    st.session_state.raw_docs = [
        {"name": "cv_alex_rivera.md", "content": extract_text_from_file(cv_path)},
        {"name": "transcript_alex_rivera.md", "content": extract_text_from_file(tr_path)},
        {"name": "project_summary.md", "content": extract_text_from_file(proj_path)}
    ]
    st.session_state.demo_loaded = True
    st.session_state.workflow_state = None

# -------------------------------------------------------------
# SCREEN 1: Input & Configuration (If not running or completed)
# -------------------------------------------------------------
if st.session_state.workflow_state is None:
    st.markdown("### 1. Task & Materials Intake")
    col_demo, col_custom = st.columns([1, 1], gap="large")

    with col_demo:
        st.markdown("""
        <div class="executive-card">
            <div class="card-title">⚡ 1-Click Benchmark Demo</div>
            <div class="card-subtitle">Load the pre-packaged Meridian Global Impact Fellowship scenario ($35,000 award, GPA 3.5+ eligibility, CV, transcript, and missing referee letter).</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Load Meridian Fellowship Preset", type="primary", use_container_width=True):
            load_demo_scenario()
            st.success("Loaded Meridian Fellowship call and Alex Rivera's applicant files!")

    with col_custom:
        st.markdown("""
        <div class="executive-card">
            <div class="card-title">📁 Custom Application Intake</div>
            <div class="card-subtitle">Paste your own opportunity guidelines or upload custom applicant documents.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### Opportunity Announcement")
    opp_text = st.text_area(
        "Opportunity Text / Guidelines",
        value=st.session_state.opportunity_input,
        height=200,
        placeholder="Paste scholarship announcement, fellowship instructions, or grant RFP..."
    )

    st.markdown("#### Supporting Documents")
    uploaded_files = st.file_uploader(
        "Upload Applicant Documents (PDF, MD, TXT)",
        accept_multiple_files=True,
        type=["pdf", "md", "txt"]
    )
    if uploaded_files:
        for f in uploaded_files:
            content = f.read().decode("utf-8", errors="ignore")
            st.session_state.raw_docs.append({"name": f.name, "content": content})

    if st.session_state.raw_docs:
        st.markdown("**Attached Files:**")
        cols = st.columns(len(st.session_state.raw_docs))
        for idx, doc in enumerate(st.session_state.raw_docs):
            with cols[idx]:
                st.caption(f"📄 {doc['name']}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Start DoneRight", type="primary", use_container_width=True):
        if not opp_text.strip():
            st.error("Please provide opportunity guidelines or click 'Load Meridian Fellowship Preset'.")
        elif not st.session_state.raw_docs:
            st.error("Please upload or attach at least one applicant document (e.g. CV or transcript).")
        else:
            with st.spinner("Initializing Strands Agents Orchestrator..."):
                gen = st.session_state.orchestrator.start_workflow(
                    opportunity_text=opp_text,
                    opportunity_source="user_submission",
                    raw_documents=st.session_state.raw_docs
                )
                for state in gen:
                    st.session_state.workflow_state = state
                st.rerun()

# -------------------------------------------------------------
# SCREEN 2, 3, 4: Active Workflow / Human Gate / Completion Receipt
# -------------------------------------------------------------
else:
    state = st.session_state.workflow_state
    col_left, col_center, col_right = st.columns([1.1, 1.2, 1.1], gap="medium")

    # LEFT COLUMN: Autonomous Multi-Agent Activity
    with col_left:
        st.markdown("#### Strands Multi-Agent Telemetry")
        agent_names = ["Task Analyst", "Requirements Agent", "Document Agent", "Verification Agent"]
        for name in agent_names:
            matching_logs = [l for l in state.activity_logs if l.agent_name == name]
            last_log = matching_logs[-1] if matching_logs else None
            status = last_log.status if last_log else "QUEUED"
            summary = last_log.output_summary if last_log else "Waiting for workflow pipeline..."

            badge_color = "#94A3B8"
            if status == "COMPLETED":
                badge_color = "#34D399"
            elif status in ["RUNNING", "WORKING"]:
                badge_color = "#E5C07B"
            elif status == "ESCALATED":
                badge_color = "#F59E0B"

            st.markdown(f"""
            <div class="telemetry-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; color: #FFFFFF;">{name}</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: {badge_color};">{status}</span>
                </div>
                <div style="font-size: 0.82rem; color: #CBD5E1; margin-top: 0.4rem; line-height: 1.4;">
                    {summary}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # CENTER COLUMN: Human Gate / Decision Queue OR Requirements Checklist
    with col_center:
        if state.current_stage == WorkflowStage.WAITING_FOR_HUMAN and state.active_decision:
            dec = state.active_decision
            st.markdown("#### Executive Gate Escalation")
            st.markdown(f"""
            <div class="human-gate-card">
                <div class="human-gate-tag">⚠ Human Decision Required</div>
                <div class="human-gate-title">{dec.reason}</div>
                <div class="human-gate-body">
                    {dec.context}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("**Choose Resolution Path:**")
            selected_opt = st.radio(
                "Options",
                options=[opt.option_id for opt in dec.options],
                format_func=lambda x: next(opt.label for opt in dec.options if opt.option_id == x),
                label_visibility="collapsed"
            )

            user_note = st.text_input(
                "Optional Note / Referee Reference Details",
                placeholder="e.g. Prof. Alan Turing, Turing Lab (alan@example.edu)"
            )

            if st.button("Resume Workflow", type="primary", use_container_width=True):
                with st.spinner("Resuming Strands workflow and executing final audit..."):
                    gen = st.session_state.orchestrator.resume_workflow(
                        state=state,
                        selected_option_id=selected_opt,
                        user_note=user_note
                    )
                    for updated in gen:
                        st.session_state.workflow_state = updated
                    st.rerun()

        else:
            if state.generated_artifacts:
                tab_check, tab_statement = st.tabs(["📋 Requirement Checklist", "📄 Prepared Statement"])
                with tab_check:
                    with st.container(height=430):
                        for req in state.requirements:
                            icon = "✓" if req.status == RequirementStatus.SATISFIED else ("⚠" if req.status == RequirementStatus.MISSING else "●")
                            color = "#34D399" if req.status == RequirementStatus.SATISFIED else ("#F59E0B" if req.status == RequirementStatus.MISSING else "#94A3B8")
                            st.markdown(f"""
                            <div style="padding: 0.45rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                                    <span style="font-weight: 500; color: #FFFFFF; font-size: 0.88rem;">{req.id}: {req.description}</span>
                                    <span style="font-size: 0.72rem; font-weight: 700; color: {color}; text-transform: uppercase;">{req.status.value}</span>
                                </div>
                                <div style="font-size: 0.76rem; color: #94A3B8; margin-top: 0.2rem;">
                                    Evidence: {req.evidence or req.evidence_needed}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                with tab_statement:
                    with st.container(height=430):
                        st.markdown(state.generated_artifacts[0].content)
            else:
                st.markdown("#### Itemized Requirement Checklist")
                with st.container(height=430):
                    for req in state.requirements:
                        icon = "✓" if req.status == RequirementStatus.SATISFIED else ("⚠" if req.status == RequirementStatus.MISSING else "●")
                        color = "#34D399" if req.status == RequirementStatus.SATISFIED else ("#F59E0B" if req.status == RequirementStatus.MISSING else "#94A3B8")
                        st.markdown(f"""
                        <div style="padding: 0.45rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                                <span style="font-weight: 500; color: #FFFFFF; font-size: 0.88rem;">{req.id}: {req.description}</span>
                                <span style="font-size: 0.72rem; font-weight: 700; color: {color}; text-transform: uppercase;">{req.status.value}</span>
                            </div>
                            <div style="font-size: 0.76rem; color: #94A3B8; margin-top: 0.2rem;">
                                Evidence: {req.evidence or req.evidence_needed}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    # RIGHT COLUMN: Completion Receipt
    with col_right:
        st.markdown("#### DoneRight Completion Receipt")
        if state.completion_receipt:
            receipt = state.completion_receipt
            score = receipt.completion_percentage
            badge_text = receipt.status

            st.markdown(f"""
            <div class="executive-card" style="border: 1px solid rgba(212, 175, 55, 0.3); margin-bottom: 0.75rem;">
                <div class="receipt-header">
                    <div class="receipt-title">COMPLETION RECEIPT</div>
                    <div class="receipt-meta">{receipt.opportunity_name} • {receipt.receipt_id}</div>
                </div>
                <div class="gauge-box">
                    <div class="gauge-score">{score}%</div>
                    <div class="gauge-label">Readiness Score</div>
                    <div style="margin-top: 0.4rem; font-size: 0.85rem; font-weight: 700; color: #34D399;">{badge_text}</div>
                </div>
                <div style="margin-bottom: 0.75rem;">
                    <div style="font-size: 0.8rem; font-weight: 600; color: #94A3B8; text-transform: uppercase;">Verified Audit Checks</div>
                    <div class="verified-row"><span class="check-icon">✓</span> Academic Eligibility Validated</div>
                    <div class="verified-row"><span class="check-icon">✓</span> CV & Transcript Matched</div>
                    <div class="verified-row"><span class="check-icon">✓</span> Statement of Purpose Grounded</div>
                    <div class="verified-row"><span class="check-icon">✓</span> Human Gate Decision Resolved</div>
                </div>
                <div style="font-size: 0.8rem; color: #CBD5E1; line-height: 1.4; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 0.6rem;">
                    {receipt.summary}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Clean action buttons below receipt without pushing layout out of place
            if state.generated_artifacts:
                st.download_button(
                    label="📥 Download Statement of Purpose (.md)",
                    data=state.generated_artifacts[0].content,
                    file_name="Statement_of_Purpose_Alex_Rivera.md",
                    mime="text/markdown",
                    use_container_width=True
                )

            if st.button("Start New Opportunity", use_container_width=True):
                st.session_state.workflow_state = None
                st.session_state.demo_loaded = False
                st.rerun()
        else:
            st.markdown("""
            <div class="executive-card">
                <div class="card-title">Receipt Pending</div>
                <div class="card-subtitle">The official DoneRight Completion Receipt will be compiled upon verification and resolution of all human decisions.</div>
            </div>
            """, unsafe_allow_html=True)
