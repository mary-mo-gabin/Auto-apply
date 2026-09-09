import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

VAULT_DIR = Path(os.getenv("VAULT_DIR", Path.home() / ".auto-apply"))
MASTER_RESUME_PATH = VAULT_DIR / "master_resume.docx"
JOBS_FILE = VAULT_DIR / "jobs.json"