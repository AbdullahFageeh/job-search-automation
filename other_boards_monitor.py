#!/usr/bin/env python3
"""
Additional Job Board Monitor — Scrape multiple remote job boards for ops roles.
Boards: WeWorkRemotely, Climbladder, Working Nomads, Remotive, FlexJobs,
Remote OK, Dynamite Jobs, JustRemote, Wellfound (AngelList), Y Combinator,
Breathe Human, Otta, Built In
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from web_scraper import fetch_page, extract_emails

BASE_DIR = Path(__file__).parent
JOBS_FILE = BASE_DIR / "logs" / "other_jobs.json"
SEEN_FILE = BASE_DIR / "logs" / "other_seen.json"

BOARDS = {
    # === Remote Job Boards (Working) ===
    "weworkremotely": {
        "url": "https://weworkremotely.com/remote-jobs",
        "selector": "a[class*='job-card']",
    },
    "remotive_ops": {
        "url": "https://remotive.com/remote-jobs/operations",
        "selector": "a[class*='job']",
    },
    "remotive_support": {
        "url": "https://remotive.com/remote-jobs/customer-service",
        "selector": "a[class*='job']",
    },
    "remoteok_ops": {
        "url": "https://remoteok.com/remote-ops-jobs",
        "selector": "a[class*='job']",
    },
    "dynamite_remote": {
        "url": "https://dynamitejobs.com/remote-jobs",
        "selector": "a.job-card",
    },
    
    # === Entry-Level Focused (Working) ===
    "climbladder_entry": {
        "url": "https://climbladder.com/jobs?location=remote&seniority=entry-level",
        "selector": "a[href*='/jobs/']",
    },
    "climbladder_early": {
        "url": "https://climbladder.com/jobs?location=remote&seniority=early-career",
        "selector": "a[href*='/jobs/']",
    },
    
    # === Startup / Tech Platforms (Working) ===
    "wellfound_ops": {
        "url": "https://wellfound.com/jobs?location=Remote&role=operations",
        "selector": "a.job",
    },
    "yc_jobs": {
        "url": "https://www.ycombinator.com/jobs?location=Remote",
        "selector": "a.job-link",
    },
    
    # === Note: These require browser/JS or are blocked ===
    # "linkedin_remote_ops" - needs Playwright + login
    # "indeed_remote_ops" - 403 Forbidden (needs JS)
    # "glassdoor_remote_ops" - 403 Forbidden (needs JS)
}

TARGET_KEYWORDS = [
    "operations", "ops", "business operations", "bizops", "biz ops",
    "operations manager", "operations lead", "operations engineer",
    "production operations", "service operations", "technical operations",
    "people ops", "people operations",
    "customer success operations", "revenue operations",
    "program manager", "project manager",
    "service delivery", "site reliability",
    "operations associate", "operations coordinator", "operations analyst",
    "operations specialist", "business analyst", "operations support",
    "workflow", "process improvement", "operational",
]

AVOID_KEYWORDS = [
    "python developer", "java developer", "software engineer",
    "frontend developer", "backend developer", "full stack",
    "data engineer", "machine learning", "devops engineer",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_seen() -> set:
    """Load seen URLs, expiring entries older than 30 days."""
    from datetime import datetime, timedelta
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            seen_data = json.load(f)
        # Each entry is now a dict: {"url": "...", "seen_at": "..."}
        # Migrate old format (plain strings) to new format
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        seen_urls = set()
        cleaned = []
        for entry in seen_data:
            if isinstance(entry, dict):
                if entry.get("seen_at", "1970-01-01") >= cutoff:
                    seen_urls.add(entry["url"])
                    cleaned.append(entry)
                # else: expired, drop it
            else:
                # Legacy format (plain string) — keep but mark as new
                seen_urls.add(entry)
                cleaned.append({"url": entry, "seen_at": datetime.now().isoformat()})
        # Clean up seen file with only recent entries
        if len(cleaned) != len(seen_data):
            save_seen_raw(cleaned)
        return seen_urls
    return set()


def save_seen(seen: set):
    """Save seen URLs as list of dicts with timestamps."""
    from datetime import datetime
    seen_list = [{"url": url, "seen_at": datetime.now().isoformat()} for url in seen]
    save_seen_raw(seen_list)


def save_seen_raw(seen_list: list):
    """Internal: save seen data without timestamp logic."""
    with open(SEEN_FILE, "w") as f:
        json.dump(seen_list, f)


def load_jobs() -> list:
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            return json.load(f)
    return []


def save_jobs(jobs: list):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def is_relevant(title: str, text: str = "") -> bool:
    combined = (title + " " + text).lower()
    has_target = any(kw in combined for kw in TARGET_KEYWORDS)
    has_avoid = any(kw in combined for kw in AVOID_KEYWORDS)
    return has_target and not has_avoid


def scrape_board(name: str, config: dict) -> list:
    """Scrape a job board."""
    logger.info(f"Scraping {name}...")
    
    result = fetch_page(config["url"], timeout=15)
    if "error" in result:
        logger.warning(f"{name} failed: {result['error']}")
        return []
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(result["html"], "lxml")
    seen = load_seen()
    jobs = []
    
    # Find all links on page
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        
        if not title or len(title) < 5:
            continue
        
        # Make URL absolute
        if href.startswith("/"):
            base = config["url"].split("/")[0] + "//" + config["url"].split("//")[1].split("/")[0]
            href = base + href
        
        # Skip non-job links
        if "/jobs/" not in href and "/job/" not in href:
            continue
        
        # Skip if seen
        if href in seen:
            continue
        
        # Check relevance
        if not is_relevant(title):
            continue
        
        # Extract emails from surrounding text
        parent = a.find_parent(["div", "li", "article"])
        context = parent.get_text() if parent else ""
        emails = extract_emails(context)
        
        jobs.append({
            "source": name,
            "title": title.strip(),
            "link": href,
            "external_url": href,
            "emails": emails,
            "found_at": datetime.now().isoformat(),
            "matched_keywords": [kw for kw in TARGET_KEYWORDS if kw in title.lower()],
        })
        seen.add(href)
    
    save_seen(seen)
    return jobs


def scan_all() -> list:
    all_new = []
    for name, config in BOARDS.items():
        try:
            new_jobs = scrape_board(name, config)
            all_new.extend(new_jobs)
        except Exception as e:
            logger.error(f"Error scraping {name}: {e}")
    
    existing = load_jobs()
    existing_ids = {j.get("link") for j in existing}
    for job in all_new:
        if job["link"] not in existing_ids:
            existing.append(job)
    
    save_jobs(existing)
    return all_new


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Additional Job Board Monitor")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("once", help="Scan all boards once")
    sub.add_parser("alerts", help="Show recent jobs")
    sub.add_parser("stats", help="Show stats")
    
    args = parser.parse_args()
    
    if args.action == "once":
        print(f"\n🔍 Scanning additional job boards...")
        new_jobs = scan_all()
        
        if new_jobs:
            print(f"\n✅ Found {len(new_jobs)} new matching jobs!\n")
            for j in new_jobs:
                print(f"  📌 {j['title']}")
                print(f"     {j['source']} | {j['link']}")
                print()
        else:
            print("\n  No new matching jobs found.")
    
    elif args.action == "alerts":
        jobs = load_jobs()
        if not jobs:
            print("No jobs found yet.")
            return
        
        print(f"\n📋 Additional Board Jobs ({len(jobs)} total)\n")
        for j in jobs[-20:]:
            print(f"  {j['found_at'][:10]} | {j['source']}")
            print(f"  {j['title']}")
            print(f"  {j['link']}")
            print()
    
    elif args.action == "stats":
        jobs = load_jobs()
        seen = load_seen()
        print(f"\n📊 Additional Boards Stats")
        print(f"   Total jobs found: {len(jobs)}")
        print(f"   Links seen (deduped): {len(seen)}")
        
        by_board = {}
        for j in jobs:
            board = j.get("source", "unknown")
            by_board[board] = by_board.get(board, 0) + 1
        
        if by_board:
            print(f"\n   By Board:")
            for board, count in sorted(by_board.items(), key=lambda x: x[1], reverse=True):
                print(f"     {board}: {count}")
        print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()