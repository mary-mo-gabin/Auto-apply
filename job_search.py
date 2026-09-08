import os
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Fetched jobs will be saved into the vault for the AI to read later
VAULT_DIR = os.getenv("VAULT_DIR")
JOBS_FILE = os.getenv("JOBS_FILE")

# Rapid key
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    raise ValueError("❌ RAPIDAPI_KEY is missing! Please add it to your .env file.")

def fetch_recent_jobs(role: str, location: str, time_filter: str):
    """Fetch recent job postings from Google Jobs via SerpApi.
    time_filter options: 'today' (past 24h) or 'week' (past 7 days)
    """
    print(f"🔍 Searching for '{role}' in '{location}' posted within the last {time_filter}...")
    
    url = "https://api.openwebninja.com/jsearch/search-v2"
    
    # JSearch handles date strings smoothly ('today', '3days', 'week')
    date_param = "today" if time_filter == "today" else "week"
    
    querystring = {
        "query": f"{role} in {location}",
        "page": "1",
        "num_pages": "2", # 10 results per page; 2 pages = 20 results in total
        "date_posted": date_param
    }
    
    headers = {
        "x-api-key": RAPIDAPI_KEY,
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json().get("data", {})
        
        # JSearch stores the array of jobs inside the "data" key
        jobs = data.get("jobs", [])
        
        if not jobs:
            print("⚠️ No jobs found matching your criteria today.")
            return []
        
        # Extract only the data we care about for the AI
        cleaned_jobs = []
        for job in jobs:
            city = job.get('job_city') or ''
            country = job.get('job_country') or ''
            job_location = f"{city}, {country}".strip(', ')
            
            cleaned_jobs.append({
                "title": job.get("job_title"),
                "company": job.get("employer_name"),
                "location": job_location,
                "description": job.get("job_description", "")[:3000], # Keep it manageable for the LLM
                "apply_link": job.get("job_apply_link", "No link provided")
            })
            
        # Save to the vault
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_jobs, f, indent=4)
        
        print(f"✅ Success! Found {len(cleaned_jobs)} jobs. Saved to '{JOBS_FILE}'")
        return cleaned_jobs
    
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")
        return []
    