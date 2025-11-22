import os
import requests
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# We use a combined query to search for multiple roles at once to save API credits
BASE_KEYWORDS = [
    "DevSecOps",
    "Cloud Security",
    "Platform Engineering",
    "Infrastructure as Code",
    "Application Security",
    "Terraform",
    "AWS"
]

# Target Locations
LOCATIONS = ["Germany", "Munich", "Remote"]
JOB_RESULTS_DIR = "job_results"

def fetch_arbeitnow_jobs():
    """
    Fetches jobs directly from ArbeitNow API.
    ArbeitNow is great for English-speaking tech jobs in Germany.
    """
    print("Fetching ArbeitNow jobs...")
    try:
        response = requests.get("https://www.arbeitnow.com/api/job-board-api")
        if response.status_code == 200:
            data = response.json().get("data", [])
            filtered = []
            for job in data:
                title_lower = job['title'].lower()
                # Check if any of our keywords exist in the job title
                is_keyword_match = any(k.lower() in title_lower for k in BASE_KEYWORDS)
                is_remote = job['remote']
                
                # specific filter for Werkstudent/Intern roles if possible, 
                # but ArbeitNow often has mixed types, so we keep it broad for "English" tags
                if (is_keyword_match or is_remote) and "Werkstudent" in job['title']:
                     filtered.append({
                        "title": job['title'],
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
    Fetches jobs from LinkedIn, Xing, Indeed via Google Jobs Aggregator.
    We use Google Jobs because scraping LinkedIn/Indeed directly is blocked by CAPTCHAs.
    Google Jobs aggregates all of them.
    """
    if not api_key:
        print("Skipping SerpApi (No Key found in env)")
        return []
        
    print("Fetching LinkedIn/Xing/Indeed via SerpApi...")
    all_jobs = []
    
    # Construct a smart query: "Werkstudent (DevSecOps OR Cloud Security OR ...)"
    # This allows us to check 7+ job titles in a single API call.
    or_query = " OR ".join([f'"{k}"' for k in BASE_KEYWORDS])
    full_query = f"Werkstudent ({or_query})"
    
    params = {
        "engine": "google_jobs",
        "q": full_query,
        "hl": "en",       # English Interface
        "gl": "de",       # Location: Germany
        "location": "Germany",
        "tbs": "qdr:d",   # Posted in last 24 hours (qdr:d)
        "api_key": api_key
    }
    
    try:
        response = requests.get("https://serpapi.com/search.json", params=params)
        if response.status_code == 200:
            results = response.json().get("jobs_results", [])
            for job in results:
                # Extract the platform name (e.g., "via LinkedIn", "via Xing")
                via = job.get('via', 'Google Jobs')
                
                # Prioritize direct apply links
                link = job.get('share_link')
                if job.get('related_links'):
                    link = job['related_links'][0].get('link', link)

                all_jobs.append({
                    "title": job.get('title'),
                    "company": job.get('company_name'),
                    "location": job.get('location'),
                    "url": link,
                    "source": via  # Will show "via LinkedIn", "via Indeed", etc.
                })
    except Exception as e:
        print(f"Error fetching SerpApi: {e}")
        
    return all_jobs

def save_results(jobs):
    """Saves the fetched jobs to a text file in the job_results folder."""
    if not os.path.exists(JOB_RESULTS_DIR):
        os.makedirs(JOB_RESULTS_DIR)
    
    # Filename format: 221125_Result.txt (DDMMYY)
    date_str = datetime.now().strftime("%d%m%y")
    filename = f"{date_str}_Result.txt"
    filepath = os.path.join(JOB_RESULTS_DIR, filename)
    
    # Calculate stats
    sources = {}
    for job in jobs:
        src = job['source']
        sources[src] = sources.get(src, 0) + 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"JOB SEARCH REPORT - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"Total Jobs Found: {len(jobs)}\n")
        f.write(f"Sources: {json.dumps(sources, indent=2)}\n")
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
    
    # 1. Fetch Data from all sources
    arbeitnow_jobs = fetch_arbeitnow_jobs()
    serpapi_jobs = fetch_serpapi_jobs(serpapi_key)
    
    # 2. Merge
    all_jobs = arbeitnow_jobs + serpapi_jobs
    
    # 3. Save
    save_results(all_jobs)

if __name__ == "__main__":
    main()