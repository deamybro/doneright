import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.models.schemas import DocumentType, DocumentInfo


def extract_text_from_file(file_path: Path | str) -> str:
    """Safely extracts text content from PDF, markdown, txt, or JSON files."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in [".txt", ".md", ".json", ".csv"]:
        return path.read_text(encoding="utf-8", errors="ignore")
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            text_parts = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            return "\n".join(text_parts)
        except Exception as e:
            return f"[Error extracting PDF {path.name}: {e}]"
    else:
        # Fallback to plain text
        return path.read_text(encoding="utf-8", errors="ignore")


def detect_document_type(filename: str, content: str) -> DocumentType:
    """Infers document type based on filename and content markers."""
    lower_name = filename.lower()
    lower_content = content.lower()

    if any(k in lower_name for k in ["cv", "resume", "curriculum_vitae"]) or "curriculum vitae" in lower_content:
        return DocumentType.CV
    elif any(k in lower_name for k in ["transcript", "grades", "academic_record"]) or "cumulative gpa" in lower_content or "grade point average" in lower_content:
        return DocumentType.TRANSCRIPT
    elif any(k in lower_name for k in ["statement", "sop", "essay", "motivation", "personal_statement"]) or "statement of purpose" in lower_content:
        return DocumentType.PERSONAL_STATEMENT
    elif any(k in lower_name for k in ["recommendation", "lor", "reference_letter"]) or "letter of recommendation" in lower_content:
        return DocumentType.RECOMMENDATION_LETTER
    elif any(k in lower_name for k in ["portfolio", "projects"]):
        return DocumentType.PORTFOLIO
    return DocumentType.OTHER


def parse_document_metadata(name: str, content: str) -> DocumentInfo:
    """Extracts grounded metadata from document content without hallucinating."""
    doc_type = detect_document_type(name, content)
    info: Dict[str, Any] = {"raw_char_count": len(content), "doc_type": doc_type.value}
    warnings: List[str] = []

    # Grounded extraction of GPA
    gpa_match = re.search(r'(?:GPA|Grade Point Average)[\s:]+([0-4]\.\d{1,3})(?:[\s/]+4\.0)?', content, re.IGNORECASE)
    if gpa_match:
        info["gpa"] = float(gpa_match.group(1))

    # Grounded extraction of Name
    name_match = re.search(r'^[ \t]*(?:Candidate Name|Applicant Name|Name)[ \t]*:[ \t]*([A-Za-z]+[ \t]+[A-Za-z]+)', content, re.MULTILINE | re.IGNORECASE)
    if name_match:
        info["candidate_name"] = name_match.group(1).strip()
    else:
        # Fallback to headline if not matching document title
        headline_match = re.search(r'^#[ \t]+(?!\[?demo|\bcurriculum\b|\btranscript\b|\bresume\b)([A-Za-z]+[ \t]+[A-Za-z]+)', content.strip(), re.MULTILINE | re.IGNORECASE)
        if headline_match:
            info["candidate_name"] = headline_match.group(1).strip()

    # Grounded extraction of Institution / Degree
    degrees = []
    for deg in ["Bachelor", "Master", "B.S.", "M.S.", "B.A.", "Ph.D.", "Doctorate"]:
        if deg.lower() in content.lower():
            degrees.append(deg)
    if degrees:
        info["degrees_mentioned"] = list(set(degrees))

    # Grounded extraction of graduation date / dates
    date_matches = re.findall(r'\b(?:19|20)\d{2}\b', content)
    if date_matches:
        info["years_mentioned"] = sorted(list(set(date_matches)))

    return DocumentInfo(
        name=name,
        doc_type=doc_type,
        status="Found",
        extracted_information=info,
        matched_requirements=[],
        warnings=warnings
    )
