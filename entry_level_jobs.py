#!/usr/bin/env python3
"""
LinkedIn Entry-Level Job Finder — Scrapes LinkedIn for entry-level remote ops roles.
Uses Comet browser for stealth and better JS rendering.
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

# Load shared browser config
sys.path.insert(0, str(Path(__file__).parent))
from browser_config import get_browser_options, get_user_agent, is_comet_available

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# File paths
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
SEEN_FILE = LOGS_DIR / "entry_level_seen.json"
JOBS_FILE = LOGS_DIR / "entry_level_jobs.json"

# LinkedIn credentials
LINKEDIN_EMAIL = "Abdullahfageeh@gmail.com"
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "@Bodi9090")

# Entry-level keywords
ENTRY_LEVEL_KEYWORDS = [
    "entry level", "entry-level", "entrylevel",
    "junior", "associate", "assistant", "intern", "internship",
    "graduate", "grad", "new grad", "fresh grad", "fresher",
    "no experience", "0 years", "0-1 years", "0-2 years",
    "l1", "level 1", "tier 1",
    "operations assistant", "operations associate",
    "operations intern", "junior operations",
    "business operations assistant", "bizops junior",
    "site reliability", "sre junior", "sre associate",
]

# Target keywords
TARGET_KEYWORDS = [
    "operations", "ops", "business operations", "bizops", "biz ops",
    "program manager", "project manager", "coordinator", "analyst",
    "associate", "specialist", "assistant",
    "customer success", "service delivery",
]

# Entry indicators
ENTRY_INDICATORS = [
    "entry level", "entry-level", "entry", "junior", "associate",
    "coordinator", "analyst", "specialist", "assistant", "intern",
    "trainee", "graduate", "new grad", "new-grad", "recent grad",
    "no experience", "0-1", "0-2", "0-3 years", "0-5 years", "1-2", "1-3",
    "up to 2", "up to 3", "fresh grad", "2027", "2026",
]

# Avoid keywords
AVOID_KEYWORDS = [
    "senior", "principal", "director", "vp", "head of", "chief",
    "manager", "10+ years", "5+ years", "8+ years", "10 years", "5 years",
]

# Search sources (reduced to 6 high-value queries to avoid rate limiting)
SEARCH_SOURCES = [
    {"name": "LinkedIn (Entry-Level Ops)", "keywords": "entry%20level%20operations"},
    {"name": "LinkedIn (Junior Ops)", "keywords": "junior%20operations"},
    {"name": "LinkedIn (Operations Analyst)", "keywords": "operations%20analyst"},
    {"name": "LinkedIn (Operations Coordinator)", "keywords": "operations%20coordinator"},
    {"name": "LinkedIn (Operations Assistant)", "keywords": "operations%20assistant"},
    {"name": "LinkedIn (Program Coordinator)", "keywords": "program%20coordinator"},
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


def scrape_linkedin(source):
    """Scrape LinkedIn for entry-level jobs using Comet browser with saved logins."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return []

    jobs = []
    seen = load_seen()
    logger.info(f"Searching: {source['name']}...")
    url = f"https://www.linkedin.com/jobs/search/?keywords={source['keywords']}&f_WT=2&f_EI=1&f_E=1"

    try:
        p = sync_playwright().start()
        
        # Use Comet browser with saved profile (inherits all logins)
        opts = get_browser_options(headless=False, slow_mo=50)
        browser = p.chromium.launch(**opts)
        page = browser.new_page()
        
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Check if logged in (page.url is a property, not method)
        current_url = page.url.lower()
        current_title = page.title().lower()
        
        if "sign-in" in current_url or "login" in current_title:
            logger.warning(f"  ⚠️ Login required - please login in browser window")
            browser.close()
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

            jobs.append({
                "source": source["name"],
                "title": title.strip(),
                "company": company,
                "location": location or "Remote",
                "link": href,
                "found_at": datetime.now().isoformat(),
                "entry_level": True,
            })
            seen.add(href)
        
        browser.close()
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
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error scanning {source['name']}: {e}")

    existing = load_jobs()
    existing_ids = {j.get("link") for j in existing}
    for job in all_new:
        if job.get("link") not in existing_ids and not job.get("manual"):
            existing.append(job)
    save_jobs(existing)
    return all_new


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Entry-Level Remote Job Finder")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("scan", help="Scan for entry-level remote ops jobs")
    sub.add_parser("list", help="List found jobs")
    sub.add_parser("stats", help="Show stats")

    args = parser.parse_args()

    if args.action == "scan":
        print(f"\nScanning for entry-level remote ops jobs...\n")
        new_jobs = scan_all()

        if new_jobs:
            auto = [j for j in new_jobs if not j.get("manual")]
            manual = [j for j in new_jobs if j.get("manual")]

            if auto:
                print(f"\nFound {len(auto)} entry-level jobs:\n")
                for j in auto:
                    print(f"  {j['title']}")
                    if j.get('company'):
                        print(f"    Company: {j['company']}")
                    print(f"    {j['link']}")
                    print()

            if manual:
                print(f"Need login for {len(manual)} searches:\n")
                for j in manual:
                    print(f"  {j['link']}")
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
        seen = load_seen()
        print(f"\nEntry-Level Job Stats")
        print(f"  Total jobs found: {len(jobs)}")
        print(f"  Searches done: {len(seen)}")
        if jobs:
            by_source = {}
            for j in jobs:
                src = j.get("source", "unknown")
                by_source[src] = by_source.get(src, 0) + 1
            print(f"\n  By Source:")
            for src, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
                print(f"    {src}: {count}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
