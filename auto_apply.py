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

# Try to import AI answerer (requires OPENAI_API_KEY)
try:
    from ai_answerer import AIAnswerer
    HAS_AI_ANSWERER = True
except ImportError:
    HAS_AI_ANSWERER = False

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

def is_remote_job(job):
    """Strict remote-only filter."""
    location = job.get("location", "").lower()
    title = job.get("title", "").lower()
    onsite_indicators = [
        "new york", "san francisco", "san jose", "silicon valley",
        "seattle", "boston", "chicago", "austin", "dallas", "houston",
        "los angeles", "l.a.", "virginia", "ohio", "new jersey",
        "miami", "denver", "atlanta", "philadelphia", "washington",
        "on-site", "onsite", "in office",
    ]
    if any(kw in location for kw in onsite_indicators):
        return False
    if "on-site" in title or "onsite" in title:
        return False
    return True

def auto_apply(max_jobs=10):
    """Auto-apply to ENTRY-LEVEL REMOTE jobs using Comet browser with saved login."""
    print(f"🚀 Auto-Apply Engine Starting...")
    print(f"   Comet Browser: {'✅' if USE_COMET else '❌'}")
    print(f"   Max applications: {max_jobs}")
    print(f"   Filter: REMOTE ONLY + ENTRY LEVEL OPS\n")
    
    # Load jobs
    jobs_file = BASE_DIR / "logs" / "entry_level_jobs.json"
    if not jobs_file.exists():
        print("❌ No jobs found. Run: python3 entry_level_jobs.py scan 50")
        return
    
    with open(jobs_file) as f:
        jobs = json.load(f)
    
    # Filter: REMOTE ONLY
    remote_jobs = [j for j in jobs if is_remote_job(j)]
    print(f"📊 Total jobs: {len(jobs)}, Remote only: {len(remote_jobs)}")
    if len(jobs) - len(remote_jobs) > 0:
        print(f"   ⚠️  Filtered out {len(jobs) - len(remote_jobs)} on-site jobs\n")
    
    # Load already applied
    applied_file = BASE_DIR / "logs" / "linkedin_applied.json"
    applied = []
    if applied_file.exists():
        with open(applied_file) as f:
            applied = json.load(f)
    applied_links = {a.get("link", "") for a in applied}
    
    # Filter new jobs (remote + not yet applied)
    new_jobs = [j for j in remote_jobs if j["link"] not in applied_links]
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
            # Wait for page to fully load (LinkedIn is SPA-heavy)
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(4)
            
            # Scroll to make sure button is loaded
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(1)
            
            # Look for Easy Apply button (try multiple selectors)
            apply_button = None
            button_selectors = [
                # LinkedIn current selectors (2024-2025)
                'button[data-control-name="apply_button"]',
                'button[data-control-name="continue_apply_click"]',
                'button[data-control-name="continue_to_apply"]',
                # Text-based selectors
                'button:has-text("Easy Apply")',
                'button:has-text("Apply")',
                # Class-based selectors
                'button.share-box-button--apply',
                'a[data-control-name="spark_apply_apply_now"]',
            ]
            
            for selector in button_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        apply_button = btn
                        print(f"   → Found button: {selector[:40]}...")
                        break
                except:
                    continue
            
            if apply_button:
                apply_button.click()
                print("   → Clicked Easy Apply")
                time.sleep(3)
                
                # Check if we're on the application form or got redirected
                current_url = page.url
                if "apply" not in current_url and "job" not in current_url:
                    print(f"   → Redirected to external site: {current_url[:60]}...")
                    results.append({
                        "title": job["title"],
                        "company": job.get("company", ""),
                        "link": job["link"],
                        "result": "External Application",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                    })
                    continue
                    
                    # Initialize AI answerer if available
                    ai = None
                    if HAS_AI_ANSWERER:
                        api_key = os.getenv("OPENAI_API_KEY")
                        if api_key:
                            ai = AIAnswerer(api_key)
                            ai.set_job(job.get("company", ""), job.get("description", ""))
                    
                    # Try to fill application form with AI answers
                    if ai:
                        try:
                            print("   → Filling application form with AI...")
                            
                            # Fill text inputs
                            text_inputs = page.locator("input[type='text'], input[type='email'], input[type='tel'], input[type='number'], textarea")
                            for input_el in text_inputs.all():
                                try:
                                    placeholder = input_el.get_attribute("placeholder") or ""
                                    label = input_el.get_attribute("aria-label") or ""
                                    name = input_el.get_attribute("name") or ""
                                    
                                    # Skip already filled fields
                                    current_value = input_el.input_value()
                                    if current_value and len(current_value) > 2:
                                        continue
                                    
                                    # Determine question context
                                    question = label or placeholder or name
                                    if question and len(question) > 3:
                                        # Skip file uploads and specific fields
                                        input_type = input_el.get_attribute("type") or "text"
                                        if input_type in ["file"]:
                                            continue
                                        
                                        # Get AI answer based on field type
                                        if "email" in question.lower() or "@email" in str(name).lower():
                                            answer = "AbdullahFageeh@gmail.com"
                                        elif "phone" in question.lower() or "tel" in str(name).lower():
                                            answer = "+966 595 266 637"
                                        elif "linkedin" in question.lower() or "profile" in question.lower():
                                            answer = "https://linkedin.com/in/abdullah-fageeh"
                                        elif "years" in question.lower() or "how long" in question.lower():
                                            answer = ai.answer_numeric(question)
                                        else:
                                            answer = ai.answer_text(question)
                                        
                                        # Fill the field
                                        input_el.fill(answer)
                                        print(f"      • Filled: {question[:40]}...")
                                        time.sleep(0.5)
                                except:
                                    continue
                            
                            # Handle dropdowns/selects
                            selects = page.locator("select, [role='listbox']")
                            for select_el in selects.all():
                                try:
                                    label = select_el.get_attribute("aria-label") or ""
                                    if label and len(label) > 3:
                                        # Get options
                                        options = page.locator(f"select[aria-label='{label}'] option").all_text_contents()
                                        if options and len(options) > 1:
                                            answer = ai.answer_choice(label, options)
                                            select_el.select_option(label=answer)
                                            print(f"      • Selected: {label[:40]}... → {answer}")
                                            time.sleep(0.5)
                                except:
                                    continue
                            
                            # Handle radio buttons for common questions
                            radio_labels = page.locator("label:has(input[type='radio'])")
                            for radio_label in radio_labels.all():
                                try:
                                    label_text = radio_label.inner_text()
                                    if len(label_text) > 3 and len(label_text) < 200:
                                        # Check if already checked
                                        if "checked" in radio_label.get_attribute("class") or radio_label.locator("input[type='radio']").is_checked():
                                            continue
                                        # Use AI to decide
                                        question = label_text
                                        answer = ai.answer_text(f"Choose: {label_text}")
                                        if answer.lower() in label_text.lower():
                                            radio_label.click()
                                            print(f"      • Selected: {label_text[:40]}...")
                                            time.sleep(0.5)
                                except:
                                    continue
                        except Exception as e:
                            print(f"      ⚠️  AI form filling error: {e}")
                    
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
