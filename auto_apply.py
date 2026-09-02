#!/usr/bin/env python3
"""
Auto-Apply Engine — Fully automated job application pipeline.
Uses Comet browser for stealth, resume matcher for scoring, and LinkedIn Easy Apply.
"""

import json
import time
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Import shared modules
sys.path.insert(0, str(Path(__file__).parent))
from browser_config import get_browser_options, get_user_agent, is_comet_available
from resume_matcher import load_resume, score_resume

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# LinkedIn credentials from .env
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "Abdullahfageeh@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "@Bodi9090")

# Resume mapping
RESUME_MAP = {
    "ladders": "resumes/Ladders_BizOps.md",
    "swooped": "resumes/Swooped_BizOps.md",
    "point.me": "resumes/point.me_BizOps.md",
    "motivate": "resumes/Motive_BizOps.md",
    "outer signal": "resumes/OuterSignal_BizOps.md",
    "whatnot": "resumes/Whatnot_StrategyOps.md",
    "gitlab": "resumes/GitLab_CS_Ops.md",
    "default": "resumes/Operations_Coordinator.md",
}

def get_resume_for_company(company_name):
    """Select best resume for company."""
    company_lower = company_name.lower()
    for key, path in RESUME_MAP.items():
        if key in company_lower:
            return BASE_DIR / path
    return BASE_DIR / RESUME_MAP["default"]

def login_linkedin(page):
    """Login to LinkedIn with Comet browser."""
    print("🔐 Logging into LinkedIn...")
    page.goto("https://www.linkedin.com/login", timeout=60000)
    time.sleep(3)
    
    try:
        # Enter credentials
        page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
        page.fill('input[name="password"]', LINKEDIN_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=30000)
        print("✅ LinkedIn login successful")
        return True
    except Exception as e:
        print(f"⚠️ Login may need manual intervention: {e}")
        print("👉 Please complete login manually in the browser window")
        input("Press Enter after you've logged in...")
        return True

def check_application_success(page):
    """Check if application was submitted successfully."""
    try:
        # LinkedIn shows success page or stays on job page
        if "apply" in page.url().lower() and "saved" in page.url().lower():
            return True
        if page.is_visible("text=Application submitted", timeout=5000):
            return True
        if page.is_visible("text=You applied", timeout=5000):
            return True
        # If URL changed away from apply page, likely success
        if "apply" not in page.url().lower():
            return True
        return False
    except:
        return False

def apply_to_job_easy(page, job_url, resume_path):
    """Apply to a job via LinkedIn Easy Apply using Comet browser."""
    print(f"   📝 Applying: {job_url}")
    page.goto(job_url, timeout=30000)
    time.sleep(3)
    
    try:
        # Click Easy Apply button
        page.click('button[aria-label*="Easy Apply"]', timeout=10000)
        time.sleep(2)
        
        # Upload resume if upload field exists
        if page.is_visible("input[type='file']", timeout=3000):
            page.set_input_files("input[type='file']", str(resume_path))
            time.sleep(2)
        
        # Try to fill common fields
        for selector in ["input[placeholder*='phone']", "input[name*='phone']"]:
            if page.is_visible(selector, timeout=1000):
                page.fill(selector, "+1234567890")
                break
        
        # Click submit
        for selector in [
            'button[aria-label*="Submit"]',
            'button[type="submit"]',
            'button:has-text("Submit application")',
            'button:has-text("Submit")',
        ]:
            if page.is_visible(selector, timeout=2000):
                page.click(selector)
                time.sleep(3)
                break
        
        success = check_application_success(page)
        return "Applied" if success else "Unknown"
        
    except Exception as e:
        print(f"   ⚠️ Application issue: {e}")
        return "Failed"

def auto_apply(max_jobs=10, days_old=30):
    """Auto-apply to entry-level jobs."""
    print(f"🚀 Auto-Apply Engine Starting...")
    print(f"   Comet Browser: {'✅' if is_comet_available() else '❌'}")
    print(f"   Max applications: {max_jobs}")
    
    # Load jobs
    jobs_file = BASE_DIR / "logs" / "entry_level_jobs.json"
    if not jobs_file.exists():
        print("❌ No jobs found. Run entry_level_jobs.py first.")
        return
    
    with open(jobs_file) as f:
        jobs = json.load(f)
    
    # Load already applied
    applied_file = BASE_DIR / "logs" / "linkedin_applied.json"
    applied = []
    if applied_file.exists():
        with open(applied_file) as f:
            applied = json.load(f)
    applied_links = {a.get("link", "") for a in applied}
    
    # Filter new jobs
    new_jobs = [j for j in jobs if j["link"] not in applied_links]
    new_jobs = new_jobs[:max_jobs]
    
    if not new_jobs:
        print("✅ No new jobs to apply to!")
        return
    
    print(f"📋 Found {len(new_jobs)} new jobs to apply to\n")
    
    # Launch Comet browser (headed for stealth)
    with sync_playwright() as p:
        browser = p.chromium.launch(**get_browser_options(headless=False, slow_mo=100))
        context = browser.new_context(user_agent=get_user_agent())
        page = context.new_page()
        
        # Login
        login_linkedin(page)
        
        results = []
        for i, job in enumerate(new_jobs, 1):
            print(f"\n[{i}/{len(new_jobs)}] {job['title']} at {job['company']}")
            
            resume_path = get_resume_for_company(job["company"])
            result = apply_to_job_easy(page, job["link"], resume_path)
            print(f"   → {result}")
            
            results.append({
                "title": job["title"],
                "company": job["company"],
                "link": job["link"],
                "result": result,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "resume_used": str(resume_path),
            })
            
            time.sleep(5 + i)  # Increasing delay for stealth
        
        browser.close()
    
    # Save results
    if applied_file.exists():
        with open(applied_file) as f:
            existing = json.load(f)
        existing.extend(results)
        with open(applied_file, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    else:
        with open(applied_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    
    success = sum(1 for r in results if r["result"] == "Applied")
    print(f"\n{'='*50}")
    print(f"🏁 Applications Complete!")
    print(f"   ✅ Successful: {success}")
    print(f"   ❌ Failed/Unknown: {len(results) - success}")
    print(f"   💾 Saved to {applied_file}")

if __name__ == "__main__":
    max_apps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    auto_apply(max_jobs=max_apps)