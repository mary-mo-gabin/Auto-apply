import os
import json
import time
from pathlib import Path
from docx import Document
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is missing! Please add it to your .env file.")

# Initialize the Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.7-flash"
    
VAULT_DIR = Path(os.getenv("VAULT_DIR"))
MASTER_RESUME_PATH = VAULT_DIR / os.getenv("MASTER_RESUME_PATH")
JOBS_FILE = VAULT_DIR / os.getenv("JOBS_FILE")

def get_master_resume_text() -> str:
    """Extracts text from the master .docx file."""
    if not MASTER_RESUME_PATH.exists():
        raise FileNotFoundError("❌ Master resume not found in vault! Please run 'setup' first.")
    doc = Document(MASTER_RESUME_PATH)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

def triage_job_batch_with_retry(resume_text: str, job_chunk: list, max_retries: int = 3) -> list:
    """Evaluates a batch of up to 10 jobs at once, returning a JSON array of scores."""
    print(f"🧠 Scoring a batch of {len(job_chunk)} jobs...")
    
    # Format the jobs into a single, highly structured string
    jobs_text = ""
    for i, job in enumerate(job_chunk):
        jobs_text += f"--- JOB {i+1} ---\nTitle: {job['title']}\nCompany: {job['company']}\nDescription: {job['description']}\n\n"
    
    prompt = f"""
    Candidate Master Resume:
    {resume_text}
    
    You must evaluate the following {len(job_chunk)} job postings.
    {jobs_text}
    """
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are an expert technical recruiter evaluating candidates for software engineering and product roles. Your task is to evaluate alignment between a Candidate Master Resume and each job posting in the exact order provided. You must return a JSON array containing exactly one evaluation object per job, matching the requested schema.",
                    response_mime_type="application/json",
                    response_schema={
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "score": {"type": "INTEGER", "description": "Score from 0 to 100"},
                                "match_verdict": {"type": "STRING", "enum": ["HIGH", "MEDIUM", "LOW"]},
                                "aligned_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "gap_analysis": {"type": "STRING"},
                                "reasoning": {"type": "STRING"}
                            },
                            "required": ["score", "match_verdict", "aligned_skills", "gap_analysis", "reasoning"]
                        }
                    }
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "503" in error_msg:
                wait_time = 35
                print(f"   ⏳ API busy. Sleeping for {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Unrecoverable error: {error_msg}")
                return []
                
    return []

def generate_tailored_documents(resume_text: str, job: dict, max_retries: int = 3):
    """Generates the customized Resume and Cover Letter in Markdown."""
    print(f"✍️ Tailoring documents for: {job['company']}...")
    
    prompt = f"""
    Master Resume:
    {resume_text}
    
    Target Posting:
    Title: {job['title']}
    Company: {job['company']}
    Description: {job['description']}
    
    Output format: 
    ===RESUME_START===
    <Tailored Resume Markdown>
    ===RESUME_END===
    
    ===COVER_LETTER_START===
    <Tailored Cover Letter Markdown>
    ===COVER_LETTER_END===
    """
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are an executive resume strategist. Customize the candidate's master resume and write a targeted cover letter for the specified role. Rules: 1. Truthfulness: Never hallucinate unlisted tools, companies, or metrics. 2. Modularity: Select only the 3-4 most relevant projects and experiences from the master resume (e.g., emphasize CPSC 526 security and FastAPI for backend roles; emphasize PySpark/CNN for data roles). 3. Formatting: Output valid Markdown formatted for a strict 1-page resume and a 3-paragraph cover letter."
                )
            )
            
            # Save the output to a dedicated folder for this job
            safe_company_name = "".join(c if c.isalnum() else "_" for c in job['company'])
            output_dir = VAULT_DIR / f"application_{safe_company_name}"
            output_dir.mkdir(exist_ok=True)
            
            with open(output_dir / "tailored_application.md", "w", encoding="utf-8") as f:
                f.write(f"# Original job Link: {job['apply_link']}\n\n")
                f.write(response.text)
                
            print(f"✅ Generated application saved to {output_dir / 'tailored_application.md'}")
            return
        
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "503" in error_msg:
                wait_time = 35
                print(f"   ⏳ API busy. Sleeping for {wait_time}s before document generation retry {attempt + 1}/{max_retries}...: {e}")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Failed to generate documents: {error_msg}")
                return
    
def score_jobs():
    """Phase 3a: Only scores the jobs and saves the ledger."""
    if not JOBS_FILE.exists():
        print("❌ No daily_jobs.json found. Run the fetch command first!")
        return

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        print("⚠️ Jobs file is empty.")
        return

    resume_text = get_master_resume_text()
    scored_jobs = []

    print(f"🚀 Starting evaluation of {len(jobs)} jobs in batches of 10...\n")
    chunk_size = 10
    
    for i in range(0, len(jobs), chunk_size):
        chunk = jobs[i:i + chunk_size]
        evaluations = triage_job_batch_with_retry(resume_text, chunk)
        
        if evaluations and len(evaluations) == len(chunk):
            for job, eval_data in zip(chunk, evaluations):
                job['evaluation'] = eval_data
                scored_jobs.append(job)
                
        if i + chunk_size < len(jobs):
            print("   ⏱️ Pacing: Sleeping for 16 seconds...")
            time.sleep(16)

    # Save the evaluations back to the disk
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(scored_jobs, f, indent=4)
    print(f"\n💾 Triage complete! Saved {len(scored_jobs)} evaluations to {JOBS_FILE}")
    print("👀 You can now review the JSON, or run 'tailor' to generate documents for the top matches.")

def tailor_jobs():
    """Phase 3b: Reads the scored ledger and generates documents for the winners."""
    if not JOBS_FILE.exists():
        print("❌ No daily_jobs.json found.")
        return

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    # Filter out unscored jobs and sort by highest score
    scored_jobs = [j for j in jobs if 'evaluation' in j]
    scored_jobs.sort(key=lambda x: x['evaluation'].get('score', 0), reverse=True)
    
    # Keep top 3 jobs that score 75 or higher
    top_matches = [j for j in scored_jobs if j['evaluation'].get('score', 0) >= 75][:3]
    
    if not top_matches:
        print("⚠️ No jobs scored 75 or higher today. Try broadening your fetch criteria.")
        return
        
    print(f"\n🎯 Found {len(top_matches)} strong matches scoring 75+!")
    resume_text = get_master_resume_text()
    
    for match in top_matches:
        # Pacing between document generations
        print("   ⏱️ Pacing: Sleeping for 16 seconds...")
        time.sleep(16)

        score = match['evaluation']['score']
        print(f"\n⭐ Match: {match['title']} at {match['company']} (Score: {score})")
        generate_tailored_documents(resume_text, match)        