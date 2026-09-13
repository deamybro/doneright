import json
from pathlib import Path
from typing import Optional
from app.models.schemas import WorkflowState


STATE_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "workflow_store"


def ensure_storage_dir():
    STATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_workflow_state(state: WorkflowState) -> Path:
    """Serializes and persists workflow state to disk."""
    ensure_storage_dir()
    file_path = STATE_STORAGE_DIR / f"{state.workflow_id}.json"
    file_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return file_path


def load_workflow_state(workflow_id: str) -> Optional[WorkflowState]:
    """Loads a previously persisted workflow state by ID."""
    file_path = STATE_STORAGE_DIR / f"{workflow_id}.json"
    if not file_path.exists():
        return None
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return WorkflowState.model_validate(data)
