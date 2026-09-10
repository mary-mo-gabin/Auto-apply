import json
import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

from config import VAULT_DIR

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is missing! Please add it to your .env file.")

# Initialize the Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_ID = "gemini-3.5-flash-lite"

def triage_job_batch_with_retry(resume_text: str, job_chunk: list) -> list:
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
    
    retry_delay = 26
    while True:
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
            if "429" in error_msg:
                print(f"   ❌ Rate limit reached. Stopping retries: {error_msg}")
                quit()
            if "503" not in error_msg:
                print(f"   ❌ Unrecoverable error: {error_msg}")
                return []

            print(f"   ⏳ API unavailable. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 180)

def generate_tailored_documents(resume_text: str, job: dict):
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
    
    retry_delay = 26
    while True:
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
                f.write(job.get("title", ""))
                f.write("\n\n" + job.get("description", ""))
                
            print(f"✅ Generated application saved to {output_dir / 'tailored_application.md'}")
            return
        
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                print(f"   ❌ Rate limit reached. Stopping retries: {error_msg}")
                return
            if "503" not in error_msg:
                print(f"   ❌ Failed to generate documents: {error_msg}")
                return

            print(f"   ⏳ API unavailable. Retrying document generation in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 180)
