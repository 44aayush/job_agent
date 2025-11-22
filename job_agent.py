import os
import requests
import json
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Strict keywords - The job TITLE must contain at least one of these
BASE_KEYWORDS = [
    "DevSecOps",
    "Cloud Security",
    "Platform Engineering",
    "Infrastructure as Code",
    "Application Security",
    "Terraform",
    "AWS",
    "Security",
    "Cyber Security",
    "Information Security",
    "IT Security"
]

# Negative keywords to filter out non-tech roles (e.g., "Marketing", "Sales")
NEGATIVE_KEYWORDS = ["Marketing", "Sales", "HR", "Recruiting", "Design", "Legal"]

JOB_RESULTS_DIR = "job_results"

def contains_keyword(text, keywords):
    """
    Checks if any keyword exists in text (case-insensitive).
    Uses word boundaries to avoid partial matches (e.g., preventing 'law' matching 'lawyer').
    """
    if not text:
        return False
    text = text.lower()
    for k in keywords:
        # Regex for word boundary to ensure exact word match (e.g. match "AWS" but not "Paws")
        pattern = r'(?<!\w)' + re.escape(k.lower()) + r'(?!\w)'
        if re.search(pattern, text):
            return True
    return False

def fetch_arbeitnow_jobs():
    """Fetches jobs from ArbeitNow (Free API)."""
    print("Fetching ArbeitNow jobs...")
    try:
        response = requests.get("https://www.arbeitnow.com/api/job-board-api")
        if response.status_code == 200:
            data = response.json().get("data", [])
            filtered = []
            for job in data:
                title = job['title']
                
                # 1. Check matches
                is_match = contains_keyword(title, BASE_KEYWORDS)
                
                # 2. Filter out garbage
                is_garbage = any(n.lower() in title.lower() for n in NEGATIVE_KEYWORDS)
                
                # FIX: Only add if it matches keywords AND is not garbage. 
                # Removed the "OR job['remote']" check which caused the wrong titles.
                if is_match and not is_garbage:
                     filtered.append({
                        "title": title,
                        "company": job['company_name'],
                        "location": job['location'],
                        "url": job['url'],
                        "source": "ArbeitNow"
                    })
            return filtered
    except Exception as e:
        print(f"Error fetching ArbeitNow: {e}")
    return []

def fetch_serpapi_jobs(api_key):
    """
    Fetches jobs from LinkedIn, Xing, Indeed, StepStone via Google Jobs.
    """
    if not api_key:
        print("Skipping SerpApi (No Key found in env)")
        return []
        
    print("Fetching LinkedIn/Xing/Indeed/StepStone via SerpApi...")
    all_jobs = []
    
    # Construct a specialized query to target specific platforms and roles
    # Query Format: Werkstudent (Keywords) (site:linkedin.com OR site:xing.com ...)
    keywords_or = " OR ".join([f'"{k}"' for k in BASE_KEYWORDS])
    
    # This tells Google to look specifically for these terms
    full_query = f'Werkstudent ({keywords_or})'
    
    params = {
        "engine": "google_jobs",
        "q": full_query,
        "hl": "en",       # Interface language
        "gl": "de",       # Region: Germany
        "location": "Germany",
        "tbs": "qdr:d",   # Posted in last 24 hours
        "api_key": api_key
    }
    
    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        if response.status_code == 200:
            results = response.json().get("jobs_results", [])
            for job in results:
                # Extract source (e.g., "via LinkedIn")
                via = job.get('via', 'Google Jobs')
                
                # Filter out if the source is generic garbage, keep the good ones
                # Google Jobs aggregates them, so we just verify the title matches our strict logic
                if contains_keyword(job.get('title'), BASE_KEYWORDS):
                    
                    # Get best link
                    link = job.get('share_link')
                    if job.get('related_links'):
                        link = job['related_links'][0].get('link', link)

                    all_jobs.append({
                        "title": job.get('title'),
                        "company": job.get('company_name'),
                        "location": job.get('location'),
                        "url": link,
                        "source": via  # This will display "via LinkedIn", "via Xing", etc.
                    })
    except Exception as e:
        print(f"Error fetching SerpApi: {e}")
        
    return all_jobs

def save_results(jobs):
    if not os.path.exists(JOB_RESULTS_DIR):
        os.makedirs(JOB_RESULTS_DIR)
    
    date_str = datetime.now().strftime("%d%m%y")
    filename = f"{date_str}_Result.txt"
    filepath = os.path.join(JOB_RESULTS_DIR, filename)
    
    # Sort jobs by source for better readability
    jobs.sort(key=lambda x: x['source'])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"JOB SEARCH REPORT - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"Total Jobs Found: {len(jobs)}\n")
        f.write("==================================================\n\n")
        
        if not jobs:
            f.write("No new matching jobs found in the last 24h.\n")
        
        for job in jobs:
            f.write(f"Role:     {job['title']}\n")
            f.write(f"Company:  {job['company']}\n")
            f.write(f"Location: {job['location']}\n")
            f.write(f"Source:   {job['source']}\n")
            f.write(f"Link:     {job['url']}\n")
            f.write("-" * 50 + "\n")
            
    print(f"Successfully saved {len(jobs)} jobs to {filepath}")

def main():
    serpapi_key = os.environ.get("SERPAPI_KEY")
    
    arbeitnow_jobs = fetch_arbeitnow_jobs()
    serpapi_jobs = fetch_serpapi_jobs(serpapi_key)
    
    all_jobs = arbeitnow_jobs + serpapi_jobs
    save_results(all_jobs)

if __name__ == "__main__":
    main()