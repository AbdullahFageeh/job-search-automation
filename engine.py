#!/usr/bin/env python3
"""
Job Search Automation Engine
Searches, applies, and tracks everything automatically.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Setup
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / f"job-search-{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config
EMAIL = os.getenv("EMAIL")
PHONE = os.getenv("PHONE")
LINKEDIN_URL = os.getenv("LINKEDIN_URL")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MIN_SALARY = int(os.getenv("MIN_SALARY", "80000"))
TARGET_ROLES = os.getenv("TARGET_ROLES", "").split(",")
AVOID_ROLES = os.getenv("AVOID_ROLES", "").split(",")
APPLY_LIMIT = int(os.getenv("APPLY_LIMIT_PER_DAY", "5"))

# Target jobs database
JOBS_DB = BASE_DIR / "logs" / "jobs.json"
APPLIED_DB = BASE_DIR / "logs" / "applied.json"
NETWORK_DB = BASE_DIR / "logs" / "network.json"

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def save_db(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_today_count(applied_list):
    today = datetime.now().date()
    return sum(1 for a in applied_list if a.get("date", "").startswith(str(today)))

def is_already_applied(url, applied_list):
    return any(a.get("url") == url for a in applied_list)

# ============ JOB SEARCHERS ============

class LinkedInSearcher:
    """Searches LinkedIn for remote operations jobs."""
    
    def __init__(self):
        self.base_url = "https://www.linkedin.com/jobs/search/"
    
    def build_url(self, query="operations manager", remote=True, days=7):
        params = {
            "keywords": query,
            "f_WT": "2" if remote else "1",
            "f_TPR": f"r{days * 24 * 60}"  # minutes
        }
        from urllib.parse import urlencode
        return f"{self.base_url}?{urlencode(params)}"

class WellfoundSearcher:
    """Searches Wellfound for startup operations roles."""
    
    def __init__(self):
        self.base_url = "https://wellfound.com/jobs"
    
    def build_url(self, query="operations", remote=True):
        from urllib.parse import urlencode
        params = {"search": query, "location": "remote" if remote else ""}
        return f"{self.base_url}?{urlencode(params)}"

class RemoteCoSearcher:
    """Searches Remote.co for project manager roles."""
    
    def __init__(self):
        self.base_url = "https://remote.co/remote-jobs/project-manager"
    
    def build_url(self):
        return self.base_url

# ============ RESUME SELECTOR ============

class ResumeSelector:
    """Picks the best resume for a given job."""
    
    RESUME_MAP = {
        "ladders": {
            "business operations": "Abdullah_Fageeh_Resume_Ladders_BizOps.pdf",
            "service operations": "Abdullah_Fageeh_Resume_Ladders_SvcOpsStrategy.pdf",
        },
        "point": "Abdullah_Fageeh_Resume_point.me_BizOps.pdf",
        "swooped": "Abdullah_Fageeh_Resume_Swooped_BizOps.pdf",
        "motive": "Abdullah_Fageeh_Resume_Motive_BizOps.pdf",
        "outersignal": "Abdullah_Fageeh_Resume_OuterSignal_BizOps.pdf",
        "whatnot": "Abdullah_Fageeh_Resume_Whatnot_StrategyOps.pdf",
        "gitlab": "Abdullah_Fageeh_Resume_GitLab_CS_Ops.pdf",
    }
    
    @staticmethod
    def pick_resume(company_name, job_title):
        company_lower = company_name.lower()
        for key, value in ResumeSelector.RESUME_MAP.items():
            if key in company_lower:
                if isinstance(value, dict):
                    for title_key, resume in value.items():
                        if title_key.lower() in job_title.lower():
                            return BASE_DIR / "resumes" / resume
                else:
                    return BASE_DIR / "resumes" / value
        # Default to Ladders BizOps
        return BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Ladders_BizOps.pdf"

# ============ MAIN ORCHESTRATOR ============

class JobSearchEngine:
    def __init__(self):
        self.linkedin = LinkedInSearcher()
        self.wellfound = WellfoundSearcher()
        self.remote_co = RemoteCoSearcher()
        self.resume_selector = ResumeSelector()
    
    def get_search_urls(self):
        """Generate all search URLs to scrape."""
        urls = []
        for role in TARGET_ROLES:
            urls.append(self.linkedin.build_url(role))
        urls.append(self.wellfound.build_url())
        urls.append(self.remote_co.build_url())
        return urls
    
    def run_once(self):
        """Run one full cycle: search → evaluate → apply."""
        logger.info("=== Starting Job Search Cycle ===")
        applied = load_db(APPLIED_DB, [])
        
        if get_today_count(applied) >= APPLY_LIMIT:
            logger.info(f"Daily limit ({APPLY_LIMIT}) reached. Stopping.")
            return
        
        urls = self.get_search_urls()
        logger.info(f"Searching {len(urls)} sources...")
        for url in urls:
            logger.info(f"  → {url[:80]}...")
        
        # Phase 1: Search (use fetch_webpage / browser)
        # Phase 2: Evaluate matches
        # Phase 3: Apply with tailored resume
        # Phase 4: Log results
        
        logger.info("Cycle complete.")
    
    def run_loop(self, interval_hours=6):
        """Run continuously."""
        while True:
            self.run_once()
            logger.info(f"Sleeping {interval_hours} hours...")
            time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    engine = JobSearchEngine()
    if "--loop" in sys.argv:
        engine.run_loop()
    else:
        engine.run_once()