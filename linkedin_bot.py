#!/usr/bin/env python3
"""
LinkedIn Automation: Search jobs, apply, send connection requests, message contacts.
Uses Comet browser for stealth automation.
"""

import os
import sys
import json
import time
import random
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from browser_config import get_browser_options, get_user_agent, is_comet_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("linkedin")

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
APPLIED_DB = BASE_DIR / "logs" / "linkedin_applied.json"
JOBS_DB = BASE_DIR / "logs" / "linkedin_jobs.json"

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def save_db(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def human_delay(base=2, variance=1):
    """Simulate human-like delay."""
    time.sleep(base + random.uniform(0, variance))

class LinkedInBot:
    def __init__(self):
        self.browser = None
        self.page = None
    
    def login(self):
        """Login to LinkedIn using Comet browser for stealth."""
        logger.info("Logging into LinkedIn...")
        logger.info(f"Using {'Comet' if is_comet_available() else 'Chromium'} browser")
        with sync_playwright() as p:
            self.browser = p.chromium.launch(**get_browser_options(headless=False))
            self.page = self.browser.new_page(user_agent=get_user_agent())
            self.page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            human_delay(3)
            
            # Check if already logged in
            if "feed" in self.page.url or "messaging" in self.page.url:
                logger.info("Already logged in.")
                return True
            
            # Fill credentials
            try:
                self.page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
                human_delay(1)
                self.page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
                human_delay(1)
                self.page.click('button[type="submit"]')
                human_delay(5)
                
                if "feed" in self.page.url or "messaging" in self.page.url or "linkedin.com/in/" in self.page.url:
                    logger.info("Login successful.")
                    return True
                else:
                    logger.warning("Login may have failed. Check browser.")
                    return False
            except Exception as e:
                logger.error(f"Login error: {e}")
                return False
    
    def search_jobs(self, query="operations manager remote"):
        """Search for jobs and return job URLs."""
        logger.info(f"Searching LinkedIn for: {query}")
        url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&f_WT=2&f_TPR=r10080"
        self.page.goto(url, wait_until="domcontentloaded")
        human_delay(4)
        
        jobs = []
        try:
            job_cards = self.page.query_selector_all('div[data-view-name="base-search-card"]')
            for card in job_cards[:20]:  # Limit to 20 per search
                try:
                    title_el = card.query_selector('a.job-card-list__title')
                    company_el = card.query_selector('span.job-card-container__listing-company-name')
                    location_el = card.query_selector('span.job-card-container__list-item-line')
                    
                    if title_el:
                        title = title_el.inner_text().strip()
                        company = company_el.inner_text().strip() if company_el else ""
                        link = title_el.get_attribute("href")
                        jobs.append({
                            "title": title,
                            "company": company,
                            "url": link,
                            "found_at": datetime.now().isoformat()
                        })
                except:
                    continue
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        logger.info(f"Found {len(jobs)} jobs.")
        return jobs
    
    def apply_to_job(self, job_url, resume_path):
        """Apply to a job using Easy Apply (if available)."""
        logger.info(f"Applying to: {job_url}")
        self.page.goto(job_url, wait_until="domcontentloaded")
        human_delay(3)
        
        try:
            # Look for Easy Apply button
            easy_apply = self.page.query_selector('[data-control-name="continued_apply_click"]')
            if easy_apply:
                easy_apply.click()
                human_delay(3)
                
                # Upload resume if file input exists
                file_input = self.page.query_selector('input[type="file"]')
                if file_input and Path(resume_path).exists():
                    file_input.set_input_files(str(resume_path))
                    human_delay(2)
                
                # Submit
                submit = self.page.query_selector('button[data-control-name="submitted_application"]')
                if submit:
                    submit.click()
                    human_delay(2)
                    logger.info(f"✓ Applied successfully!")
                    return True
                else:
                    logger.warning("Submit button not found. May need manual review.")
                    return False
            else:
                logger.info("No Easy Apply button — company application required.")
                return None  # Can't auto-apply
        except Exception as e:
            logger.error(f"Apply error: {e}")
            return False
    
    def send_connection_message(self, profile_url, message):
        """Send a connection request with a message."""
        logger.info(f"Sending connection request to: {profile_url}")
        self.page.goto(profile_url, wait_until="domcontentloaded")
        human_delay(3)
        
        try:
            connect_btn = self.page.query_selector('button[data-control-name="profileconnect"]')
            if connect_btn:
                connect_btn.click()
                human_delay(2)
                
                # Add note
                note_input = self.page.query_selector('textarea[aria-label*="Add a note"]')
                if note_input:
                    note_input.fill(message[:300])  # LinkedIn limit
                    human_delay(1)
                
                send_btn = self.page.query_selector('button[type="submit"]')
                if send_btn:
                    send_btn.click()
                    logger.info("✓ Connection request sent!")
                    return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
        return False
    
    def close(self):
        if self.browser:
            self.browser.close()

def main():
    bot = LinkedInBot()
    
    if not bot.login():
        logger.error("Failed to login. Exiting.")
        return
    
    try:
        # 1. Search for jobs
        all_jobs = []
        queries = ["operations manager remote", "business operations manager remote", "project manager remote"]
        for q in queries:
            jobs = bot.search_jobs(q)
            all_jobs.extend(jobs)
        
        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique_jobs.append(j)
        
        logger.info(f"Found {len(unique_jobs)} unique jobs after dedup.")
        
        # 2. Filter & apply
        applied = load_db(APPLIED_DB, [])
        jobs_db = load_db(JOBS_DB, [])
        
        for job in unique_jobs[:10]:  # Limit to 10 per run
            if any(a.get("url") == job["url"] for a in applied):
                logger.info(f"Skipping (already applied): {job['title']}")
                continue
            
            resume = str(BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Ladders_BizOps.pdf")
            result = bot.apply_to_job(job["url"], resume)
            
            if result is True:
                applied.append({
                    "url": job["url"],
                    "title": job["title"],
                    "company": job["company"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "method": "easy_apply"
                })
                save_db(APPLIED_DB, applied)
            
            jobs_db.append(job)
            save_db(JOBS_DB, jobs_db)
            
            human_delay(5)  # Rate limit
        
        # 3. Send networking messages (if contacts provided)
        network = load_db(BASE_DIR / "logs" / "network.json", [])
        # TODO: Load contact list and send messages
        
        logger.info("=== LinkedIn automation cycle complete ===")
    finally:
        bot.close()

if __name__ == "__main__":
    main()