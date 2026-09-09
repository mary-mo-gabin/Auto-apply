import os
import argparse
import shutil
from pathlib import Path
from docx import Document

from job_search import fetch_recent_jobs
from evaluator import score_jobs, tailor_jobs

# The hidden vault directory
from config import VAULT_DIR, MASTER_RESUME_PATH

def setup(resume_file: str):
    """Create the vault and store the master resume."""
    file_path = Path(resume_file)
    
    if not file_path.exists():
        print(f"❌ Error: Could not find the file '{resume_file}'")
        return
    
    if file_path.suffix.lower() != '.docx':
        print(f"❌ Error: The master resume must be a .docx file. Provided file has extension '{file_path.suffix}'")
        return
    
    # Create hidden vault directory if it doesn't exist
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Copy the master resume into the vault
    shutil.copy(file_path, MASTER_RESUME_PATH)
    print(f"✅ Success! Master resume securely stored at '{MASTER_RESUME_PATH}'")
    
def read_vault():
    """Read the stored resume to verify python-docx is working."""
    
    if not MASTER_RESUME_PATH.exists():
        print("❌ Error: No master resume found. Please run 'setup' first.")
        return
    
    doc = Document(MASTER_RESUME_PATH)
    # Extract text from all paragraphs
    full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    
    print("✅ Successfully parsed your Master Resume!")
    print(f"📄 Total extracted characters: {len(full_text)}")
    print(f"[Preview] \n{full_text[:100]}...\n")
    
def main():
    parser = argparse.ArgumentParser(description=
                                     "Auto-apply CLI: Job Application Automation Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    # The 'setup' command
    setup_parser = subparsers.add_parser("setup", help="Initialize the system with your .docx master resume")
    setup_parser.add_argument("resume", help="Path to the .docx master resume")

    # The 'check' command to verify text extraction
    subparsers.add_parser("check", help="Verify the CLI can read the stored resume")
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch recent job postings")
    fetch_parser.add_argument("--role", default="junior software", help="The job title to search for")
    fetch_parser.add_argument("--location", default="calgary, alberta, canada", help="Location (e.g., 'Calgary, Alberta, Canada', or 'Canada')")
    fetch_parser.add_argument("--time", default="today", choices=["today", "week"], help="Timeframe: 'today' or 'week'")
    
    # Score command
    subparsers.add_parser("score", help="Score fetched jobs and save them to the vault")
    # Tailor command
    subparsers.add_parser("tailor", help="Generate tailored documents for top-scoring jobs")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        setup(args.resume)
    elif args.command == "check":
        read_vault()
    elif args.command == "fetch":
        fetch_recent_jobs(args.role, args.location, args.time)
    elif args.command == "score":
        score_jobs()
    elif args.command == "tailor":
        tailor_jobs()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()