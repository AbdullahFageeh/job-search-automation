#!/usr/bin/env python3
"""
Auto-Apply Engine — Fully automated job application pipeline.
Uses Comet browser with saved profile (inherits LinkedIn login).
"""

import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Import shared modules
sys.path.insert(0, str(Path(__file__).parent))
from browser_config import COMET_PATH, COMET_PROFILE, USE_COMET, get_user_agent
from resume_matcher import load_resume, score_resume

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# LinkedIn credentials from .env
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "Abdullahfageeh@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "@Bodi9090")

# Resume mapping
RESUME_MAP = {
    "ladders": "resumes/Abdullah_Fageeh_Resume_Ladders_BizOps.md",
    "swooped": "resumes/Abdullah_Fageeh_Resume_Swooped_BizOps.md",
    "point.me": "resumes/Abdullah_Fageeh_Resume_point.me_BizOps.md",
    "motive": "resumes/Abdullah_Fageeh_Resume_Motive_BizOps.md",
    "outer signal": "resumes/Abdullah_Fageeh_Resume_OuterSignal_BizOps.md",
    "whatnot": "resumes/Abdullah_Fageeh_Resume_Whatnot_StrategyOps.md",
    "gitlab": "resumes/Abdullah_Fageeh_Resume_GitLab_CS_Ops.md",
    "default": "resumes/Abdullah_Fageeh_Resume.md",
}

def get_resume_for_company(company_name):
    """Select best resume for company."""
    company_lower = company_name.lower()
    for key, path in RESUME_MAP.items():
        if key in company_lower:
            return BASE_DIR / path
    # Try to find PDF
    for key, path in RESUME_MAP.items():
        pdf_path = path.replace(".md", ".pdf")
        if Path(pdf_path).exists():
            if key in company_lower:
                return Path(pdf_path)
    # Fallback to first existing resume
    for p in RESUME_MAP.values():
        if Path(p).exists():
            pdf = p.replace(".md", ".pdf")
            if Path(pdf).exists():
                return Path(pdf)
            return Path(p)
    return BASE_DIR / "resumes/Abdullah_Fageeh_Resume.md"

def auto_apply(max_jobs=10):
    """Auto-apply to entry-level jobs using Comet browser with saved login."""
    print(f"🚀 Auto-Apply Engine Starting...")
    print(f"   Comet Browser: {'✅' if USE_COMET else '❌'}")
    print(f"   Max applications: {max_jobs}")
    
    # Load jobs
    jobs_file = BASE_DIR / "logs" / "entry_level_jobs.json"
    if not jobs_file.exists():
        print("❌ No jobs found. Run entry_level_jobs.py scan first.")
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
    
    # Launch Comet with persistent context (inherits LinkedIn login!)
    p = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=COMET_PROFILE,
        executable_path=COMET_PATH,
        headless=False,
        slow_mo=50,
        user_agent=get_user_agent(),
    )
    page = context.new_page()
    
    # Check if already logged in
    page.goto("https://www.linkedin.com", timeout=30000)
    time.sleep(2)
    
    if "sign-in" in page.url.lower() or "login" in page.title().lower():
        print("⚠️  Not logged in to LinkedIn")
        print("   Please login manually in the browser window...")
        input("Press Enter after you've logged in...")
    
    results = []
    for i, job in enumerate(new_jobs, 1):
        print(f"\n[{i}/{len(new_jobs)}] {job['title']} at {job.get('company', 'Unknown')}")
        
        resume_path = get_resume_for_company(job.get("company", ""))
        
        try:
            page.goto(job["link"], timeout=30000)
            time.sleep(3)
            
            # Look for Easy Apply button
            try:
                # Try multiple selectors for Easy Apply
                apply_button = page.locator('[data-control-name="continue_apply_click"]').first
                if apply_button.is_visible(timeout=5000):
                    apply_button.click()
                    print("   → Clicked Easy Apply")
                    time.sleep(2)
                    
                    # Try to upload resume
                    try:
                        file_input = page.locator("input[type='file']").first
                        if file_input.is_visible(timeout=3000):
                            file_input.set_input_files(str(resume_path))
                            print(f"   → Uploaded resume: {resume_path.name}")
                            time.sleep(2)
                    except:
                        pass  # Resume might already be filled
                    
                    # Try to submit
                    try:
                        submit = page.locator('button[type="submit"], button:has-text("Submit"), button:has-text("Review application")').first
                        if submit.is_visible(timeout=3000):
                            submit.click()
                            print("   → Submitted!")
                            results.append({
                                "title": job["title"],
                                "company": job.get("company", ""),
                                "link": job["link"],
                                "result": "Applied",
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "resume_used": str(resume_path),
                            })
                        else:
                            print("   → Manual review needed")
                            results.append({
                                "title": job["title"],
                                "company": job.get("company", ""),
                                "link": job["link"],
                                "result": "Manual Review",
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "resume_used": str(resume_path),
                            })
                    except:
                        print("   → No submit button found")
                        results.append({
                            "title": job["title"],
                            "company": job.get("company", ""),
                            "link": job["link"],
                            "result": "Needs Attention",
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "resume_used": str(resume_path),
                        })
                else:
                    print("   → No Easy Apply button (may need manual application)")
                    results.append({
                        "title": job["title"],
                        "company": job.get("company", ""),
                        "link": job["link"],
                        "result": "No Easy Apply",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    })
            except Exception as e:
                print(f"   → Error: {e}")
                results.append({
                    "title": job["title"],
                    "company": job.get("company", ""),
                    "link": job["link"],
                    "result": "Error",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
            
            # Human-like delay
            time.sleep(3 + i)
            
        except Exception as e:
            print(f"   → Failed: {e}")
            results.append({
                "title": job["title"],
                "company": job.get("company", ""),
                "link": job["link"],
                "result": "Failed",
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
    
    context.close()
    p.stop()
    
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
    print(f"   ✅ Applied: {success}")
    print(f"   ⚠️  Manual/Other: {len(results) - success}")
    print(f"   💾 Saved to {applied_file}")

if __name__ == "__main__":
    max_apps = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    auto_apply(max_jobs=max_apps)
