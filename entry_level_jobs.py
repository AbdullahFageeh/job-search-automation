#!/usr/bin/env python3
"""
LinkedIn Entry-Level Job Finder — Uses Comet persistent context (inherits saved LinkedIn login).
"""

import json
import os
import time
import sys
import logging
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from browser_config import COMET_PATH, COMET_PROFILE, USE_COMET, get_persistent_options

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SEEN_FILE = LOGS_DIR / "entry_level_seen.json"
JOBS_FILE = LOGS_DIR / "entry_level_jobs.json"
SA_JOBS_FILE = LOGS_DIR / "saudi_jobs.json"  # On-site jobs within Saudi Arabia

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "Abdullahfageeh@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "@Bodi9090")

ENTRY_INDICATORS = [
    "entry level", "entry-level", "entrylevel", "junior", "associate",
    "coordinator", "analyst", "specialist", "assistant", "intern",
    "trainee", "graduate", "new grad", "new-grad", "recent grad",
    "no experience", "0-1", "0-2", "0-3 years", "0-5 years", "1-2", "1-3",
    "up to 2", "up to 3", "fresh grad", "2027", "2026",
]

TARGET_KEYWORDS = [
    "operations", "ops", "business operations", "bizops", "biz ops",
    "program manager", "project manager", "coordinator", "analyst",
    "associate", "specialist", "assistant", "customer success", "service delivery",
]

AVOID_KEYWORDS = [
    "senior", "principal", "director", "vp", "head of", "chief",
    "manager", "10+ years", "5+ years", "8+ years", "10 years", "5 years",
]

SEARCH_SOURCES = [
    {"name": "Entry-Level Ops", "keywords": "entry%20level%20operations"},
    {"name": "Junior Ops", "keywords": "junior%20operations"},
    {"name": "Operations Analyst", "keywords": "operations%20analyst"},
    {"name": "Operations Coordinator", "keywords": "operations%20coordinator"},
    {"name": "Operations Assistant", "keywords": "operations%20assistant"},
    {"name": "Program Coordinator", "keywords": "program%20coordinator"},
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def load_seen():
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def load_jobs():
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            return json.load(f)
    return []

def save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def is_entry_level(title, snippet=""):
    combined = (title + " " + snippet).lower()
    has_entry = any(ind in combined for ind in ENTRY_INDICATORS)
    has_senior = any(kw in combined for kw in AVOID_KEYWORDS)
    return has_entry and not has_senior

def is_ops_relevant(title, snippet=""):
    combined = (title + " " + snippet).lower()
    return any(kw in combined for kw in TARGET_KEYWORDS)

def is_remote(job_dict):
    """Strict remote-only filter — reject any job with a physical city/location."""
    location = job_dict.get("location", "").lower()
    title = job_dict.get("title", "").lower()
    # On-site keywords (hard exclude)
    onsite_indicators = [
        "new york", "san francisco", "san jose", "silicon valley",
        "seattle", "boston", "chicago", "austin", "dallas", "houston",
        "los angeles", "l.a.", "virginia", "ohio", "new jersey",
        "miami", "denver", "atlanta", "philadelphia", "washington",
        "pennsylvania", "massachusetts", "california", "texas", "florida",
        "on-site", "onsite", "in office", "must be on-site",
    ]
    is_onsite = any(kw in location for kw in onsite_indicators)
    # If title says on-site
    if "on-site" in title or "onsite" in title:
        return False
    if is_onsite:
        return False
    return True

def is_saudi_arabia(job_dict):
    """Check if job is located in Saudi Arabia."""
    location = job_dict.get("location", "").lower()
    title = job_dict.get("title", "").lower()
    sa_keywords = [
        "saudi arabia", "saudi", "riyadh", "jeddah", "dammam",
        "ksa", "tabuk", "khobar", "duba", "al khobar", "medina", "makkah", "mecca",
    ]
    return any(kw in location for kw in sa_keywords) or any(kw in title for kw in sa_keywords)

def scrape_linkedin(source):
    jobs = []
    seen = load_seen()
    logger.info(f"Searching: {source['name']}...")
    url = f"https://www.linkedin.com/jobs/search/?keywords={source['keywords']}&f_WT=2&f_EI=1&f_E=1"

    try:
        p = sync_playwright().start()
        context = p.chromium.launch_persistent_context(**get_persistent_options())
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        if "sign-in" in page.url.lower() or "login" in page.title().lower():
            logger.warning(f"  Login required for {source['name']}")
            context.close()
            p.stop()
            return []

        from bs4 import BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, "lxml")

        for card in soup.find_all("a", href=lambda h: h and "/jobs/view/" in h)[:30]:
            href = card.get("href", "")
            title = card.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            if href.startswith("/"):
                href = f"https://www.linkedin.com{href}"
            if href in seen:
                continue
            if not is_ops_relevant(title):
                continue
            if not is_entry_level(title):
                continue

            company = ""
            location = ""
            parent = card.find_parent(["li", "div"])
            if parent:
                for span in parent.find_all("span"):
                    txt = span.get_text(strip=True).lower()
                    if "remote" in txt or "united states" in txt:
                        location = span.get_text(strip=True)
                        break

            job = {
                "source": source["name"],
                "title": title.strip(),
                "company": company,
                "location": location or "Remote",
                "link": href,
                "found_at": datetime.now().isoformat(),
                "entry_level": True,
            }
            
            # Only add truly remote jobs (or Saudi Arabia on-site)
            if not is_remote(job):
                # Save Saudi Arabia on-site jobs to separate file
                if is_saudi_arabia(job):
                    sa_jobs = load_sa_jobs()
                    if job["link"] not in {j["link"] for j in sa_jobs}:
                        sa_jobs.append(job)
                        save_sa_jobs(sa_jobs)
                        logger.info(f"  Saved to Saudi jobs: {title} ({location})")
                    # Also include SA jobs in the main remote jobs list
                    jobs.append(job)
                else:
                    logger.info(f"  Skipped (not remote): {title} ({location})")
                seen.add(href)
                continue
            
            jobs.append(job)
            seen.add(href)
        
        context.close()
        p.stop()
    except Exception as e:
        logger.error(f"Error scanning {source['name']}: {e}")

    save_seen(seen)
    return jobs

def scan_all():
    all_new = []
    for source in SEARCH_SOURCES:
        try:
            new_jobs = scrape_linkedin(source)
            all_new.extend(new_jobs)
            time.sleep(3)
        except Exception as e:
            logger.error(f"Error scanning {source['name']}: {e}")

    existing = load_jobs()
    existing_ids = {j.get("link") for j in existing}
    for job in all_new:
        if job.get("link") not in existing_ids and not job.get("manual"):
            existing.append(job)
    save_jobs(existing)
    return all_new

def load_sa_jobs() -> list:
    if SA_JOBS_FILE.exists():
        with open(SA_JOBS_FILE) as f:
            return json.load(f)
    return []

def save_sa_jobs(jobs: list):
    with open(SA_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Entry-Level Remote Job Finder")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("scan", help="Scan for entry-level remote ops jobs")
    sub.add_parser("list", help="List found jobs")
    sub.add_parser("stats", help="Show stats")
    sub.add_parser("saudi", help="Show Saudi Arabia on-site jobs")
    args = parser.parse_args()

    if args.action == "scan":
        print(f"\nScanning for entry-level remote ops jobs...\n")
        new_jobs = scan_all()
        if new_jobs:
            auto = [j for j in new_jobs if not j.get("manual")]
            manual = [j for j in new_jobs if j.get("manual")]
            if auto:
                print(f"\nFound {len(auto)} entry-level jobs:\n")
                for j in auto[:20]:
                    print(f"  {j['title']}")
                    if j.get('company'):
                        print(f"    Company: {j['company']}")
                    print(f"    {j['link']}")
                    print()
            if manual:
                print(f"Need login for {len(manual)} searches\n")
        else:
            print("\nNo new jobs found.")

    elif args.action == "list":
        jobs = load_jobs()
        if not jobs:
            print("No jobs yet. Run: python3 entry_level_jobs.py scan")
            return
        print(f"\nEntry-Level Remote Ops Jobs ({len(jobs)} total)\n")
        for j in jobs[-30:]:
            print(f"  {j['title']}")
            if j.get('company'):
                print(f"    {j['company']}")
            print(f"    {j['link']}")
            print()

    elif args.action == "stats":
        jobs = load_jobs()
        print(f"\nTotal jobs found: {len(jobs)}")
        if jobs:
            sources = {}
            for j in jobs:
                src = j.get("source", "Unknown")
                sources[src] = sources.get(src, 0) + 1
            for src, count in sorted(sources.items(), key=lambda x: -x[1]):
                print(f"  {src}: {count}")
        
        # Saudi Arabia stats
        sa_jobs = load_sa_jobs()
        if sa_jobs:
            print(f"\n🇸🇦 Saudi Arabia On-Site Jobs: {len(sa_jobs)}")
            for j in sa_jobs[:10]:
                print(f"  {j['title']} — {j.get('location', 'N/A')}")

    elif args.action == "saudi":
        sa_jobs = load_sa_jobs()
        if not sa_jobs:
            print("No Saudi Arabia jobs yet. Run: python3 entry_level_jobs.py scan")
            return
        print(f"\n🇸🇦 Saudi Arabia On-Site Jobs ({len(sa_jobs)} total)\n")
        for j in sa_jobs:
            print(f"  {j['title']}")
            if j.get('company'):
                print(f"    {j['company']}")
            print(f"    Location: {j.get('location', 'N/A')}")
            print(f"    {j['link']}")
            print()

    else:
        print("Usage: python3 entry_level_jobs.py [scan|list|stats|saudi]")

if __name__ == "__main__":
    main()
