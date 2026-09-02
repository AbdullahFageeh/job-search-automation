#!/usr/bin/env python3
"""
Auto-apply to entry-level remote operations jobs found on LinkedIn.
Uses Comet browser for stealth and Playwright for automation.
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

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from browser_config import get_browser_options, get_user_agent, is_comet_available

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("apply")

# Load credentials from .env
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "Abdullahfageeh@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "@Bodi9090")

# Resume mapping by company type
RESUMES = {
    "tech": BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Ladders_BizOps.pdf",
    "logistics": BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Motive_BizOps.pdf",
    "customer_success": BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_GitLab_CS_Ops.pdf",
    "strategy": BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Whatnot_StrategyOps.pdf",
}

# Company to resume type mapping
COMPANY_RESUME_MAP = {
    "tiktok": "tech",
    "flexport": "logistics",
    "doordash": "tech",
    "picnic": "tech",
    "loop": "tech",
    "airblox": "tech",
    "agave": "tech",
    "checkout": "tech",
    "uspack": "logistics",
    "schneider": "logistics",
    "calyx": "logistics",
    "triumph": "logistics",
    "ally": "logistics",
    "default": "tech",  # Default for other companies
}

APPLIED_DB = BASE_DIR / "logs" / "linkedin_applied.json"
ENTRY_JOBS_DB = BASE_DIR / "logs" / "entry_level_jobs.json"

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def save_db(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_resume_for_company(company):
    """Select best resume for the company type."""
    company_lower = company.lower()
    for keyword, resume_type in COMPANY_RESUME_MAP.items():
        if keyword in company_lower:
            return RESUMES[resume_type]
    return RESUMES["default"]

def human_delay(min_sec=2, max_sec=5):
    """Simulate human-like delay."""
    time.sleep(random.uniform(min_sec, max_sec))

def apply_to_jobs():
    """Auto-apply to entry-level jobs found earlier."""
    from playwright.sync_api import sync_playwright
    
    # Load jobs to apply to
    jobs = load_db(ENTRY_JOBS_DB, [])
    if not jobs:
        logger.error("No jobs found. Run: python3 entry_level_jobs.py scan")
        return
    
    # Load already applied jobs
    applied = load_db(APPLIED_DB, [])
    applied_urls = {a.get("url") for a in applied}
    
    # Filter out already applied
    jobs_to_apply = [j for j in jobs if j.get("link") not in applied_urls]
    
    if not jobs_to_apply:
        logger.info("All jobs already applied to!")
        return
    
    logger.info(f"Found {len(jobs_to_apply)} new jobs to apply to")
    logger.info(f"Using {'Comet' if is_comet_available() else 'Chromium'} browser for stealth")
    
    with sync_playwright() as p:
        # Launch Comet browser in headed mode for LinkedIn (anti-bot detection)
        browser = p.chromium.launch(**get_browser_options(headless=False, slow_mo=100))
        context = browser.new_context(
            user_agent=get_user_agent(),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        
        try:
            # Login to LinkedIn
            logger.info("Logging into LinkedIn...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            human_delay(3)
            
            # Check if already logged in
            if "feed" in page.url or "messaging" in page.url or "linkedin.com/in/" in page.url:
                logger.info("Already logged in.")
            else:
                # Fill credentials
                page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
                human_delay(1)
                page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
                human_delay(1)
                page.click('button[type="submit"]')
                human_delay(5)
                
                # Wait for login to complete
                page.wait_for_url("**/feed/**", timeout=15000)
                logger.info("Login successful.")
            
            # Apply to each job
            success_count = 0
            skip_count = 0
            manual_count = 0
            
            for i, job in enumerate(jobs_to_apply):
                job_url = job.get("link", "")
                if not job_url:
                    continue
                
                logger.info(f"\n[{i+1}/{len(jobs_to_apply)}] Applying to: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                try:
                    page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                    human_delay(3)
                    
                    # Check if Easy Apply button exists
                    try:
                        easy_apply = page.query_selector('[data-control-name="continued_apply_click"]')
                        if easy_apply:
                            easy_apply.click()
                            human_delay(3)
                            
                            # Check if application form opens
                            if "apply" in page.url.lower() or "application" in page.url.lower():
                                # Upload resume
                                resume_path = get_resume_for_company(job.get("company", ""))
                                if resume_path.exists():
                                    file_input = page.query_selector('input[type="file"]')
                                    if file_input:
                                        file_input.set_input_files(str(resume_path))
                                        human_delay(2)
                                
                                # Fill any required fields
                                # Phone number
                                phone = os.getenv("PHONE", "")
                                if phone:
                                    phone_input = page.query_selector('input[placeholder*="Phone"]')
                                    if phone_input:
                                        phone_input.fill(phone)
                                        human_delay(1)
                                
                                # Email
                                email = os.getenv("EMAIL", "")
                                if email:
                                    email_input = page.query_selector('input[placeholder*="Email"]')
                                    if email_input:
                                        email_input.fill(email)
                                        human_delay(1)
                                
                                # Submit application
                                submit_btn = page.query_selector('button[data-control-name="submitted_application"]')
                                if submit_btn:
                                    submit_btn.click()
                                    human_delay(3)
                                    success_count += 1
                                    logger.info(f"✓ Applied successfully!")
                                    
                                    # Record application
                                    applied.append({
                                        "url": job_url,
                                        "title": job.get("title", ""),
                                        "company": job.get("company", ""),
                                        "date": datetime.now().strftime("%Y-%m-%d"),
                                        "method": "easy_apply_auto",
                                        "resume": str(get_resume_for_company(job.get("company", ""))),
                                    })
                                    save_db(APPLIED_DB, applied)
                                else:
                                    logger.warning("Submit button not found.")
                                    manual_count += 1
                            else:
                                logger.info("Application form not detected.")
                                manual_count += 1
                        else:
                            logger.info("No Easy Apply button - company application required.")
                            manual_count += 1
                    except Exception as e:
                        logger.error(f"Apply error: {e}")
                        manual_count += 1
                    
                    human_delay(5, 10)  # Delay between applications
                
                except Exception as e:
                    logger.error(f"Error accessing job page: {e}")
                    manual_count += 1
                
                # Save progress after each job
                save_db(APPLIED_DB, applied)
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Applications submitted: {success_count}")
            logger.info(f"Need manual application: {manual_count}")
            logger.info(f"{'='*50}")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    apply_to_jobs()
