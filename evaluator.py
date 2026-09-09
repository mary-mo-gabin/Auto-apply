import json
import time

from ai_engine import generate_tailored_documents, triage_job_batch_with_retry
from document_utils import get_master_resume_text

from config import JOBS_FILE

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