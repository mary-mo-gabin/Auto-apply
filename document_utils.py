from docx import Document
from config import MASTER_RESUME_PATH

def get_master_resume_text() -> str:
    """Extracts text from the master .docx file."""
    if not MASTER_RESUME_PATH.exists():
        raise FileNotFoundError("❌ Master resume not found in vault! Please run 'setup' first.")
    doc = Document(MASTER_RESUME_PATH)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
