#!/usr/bin/env python3
"""
GitHub Jobs Monitor — Monitor GitHub repositories that list remote jobs.
Scans popular job-list repos and extracts relevant positions.
"""

import json
import re
import time
import logging
from pathlib import Path
from datetime import datetime
from web_scraper import fetch_page, extract_emails

BASE_DIR = Path(__file__).parent
JOBS_FILE = BASE_DIR / "logs" / "github_jobs.json"
SEEN_FILE = BASE_DIR / "logs" / "github_seen.json"

# Popular GitHub repos that list remote jobs (actively maintained)
JOB_REPOS = [
    "lucassaliba/awesome-remote-job",
    "samaritanlai/awesome-remote-job",
]

TARGET_KEYWORDS = [
    "operations", "ops", "business operations", "bizops", "biz ops",
    "operations manager", "operations lead", "operations engineer",
    "production operations", "service operations", "technical operations",
    "people ops", "people operations",
    "customer success operations", "revenue operations",
    "program manager", "project manager",
    "service delivery", "site reliability",
]

AVOID_KEYWORDS = [
    "python developer", "java developer", "software engineer",
    "frontend developer", "backend developer", "full stack",
    "data engineer", "machine learning", "devops engineer",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_seen() -> set:
    if SEEN_FILE.exists():
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def load_jobs() -> list:
    if JOBS_FILE.exists():
        with open(JOBS_FILE) as f:
            return json.load(f)
    return []


def save_jobs(jobs: list):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


def is_relevant(title: str, text: str = "") -> bool:
    """Check if a job post matches our target roles."""
    combined = (title + " " + text).lower()
    has_target = any(kw in combined for kw in TARGET_KEYWORDS)
    has_avoid = any(kw in combined for kw in AVOID_KEYWORDS)
    return has_target and not has_avoid


def parse_markdown_jobs(markdown: str, repo: str) -> list:
    """Parse job listings from a markdown file."""
    jobs = []
    lines = markdown.split("\n")
    
    for line in lines:
        # Match markdown links like [Job Title](https://company.com/job)
        matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        for title, url in matches:
            if not is_relevant(title):
                continue
            
            # Skip if already seen
            seen = load_seen()
            if url in seen:
                continue
            
            jobs.append({
                "source": f"github/{repo}",
                "title": title.strip(),
                "link": url,
                "external_url": url,
                "found_at": datetime.now().isoformat(),
                "matched_keywords": [kw for kw in TARGET_KEYWORDS if kw in title.lower()],
            })
            seen.add(url)
    
    save_seen(seen)
    return jobs


def scrape_repo(repo: str) -> list:
    """Scrape a GitHub repo for job listings."""
    logger.info(f"Scraping {repo}...")
    
    # Try to get raw README
    raw_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
    if not raw_url:
        raw_url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
    
    result = fetch_page(raw_url, timeout=10)
    if "error" in result:
        logger.warning(f"Failed to fetch {repo}: {result['error']}")
        return []
    
    markdown = result.get("text", "")
    return parse_markdown_jobs(markdown, repo)


def scan_all() -> list:
    """Scan all configured repos."""
    all_new = []
    for repo in JOB_REPOS:
        try:
            new_jobs = scrape_repo(repo)
            all_new.extend(new_jobs)
        except Exception as e:
            logger.error(f"Error scanning {repo}: {e}")
    
    # Save new jobs
    existing = load_jobs()
    existing_ids = {j.get("link") for j in existing}
    for job in all_new:
        if job["link"] not in existing_ids:
            existing.append(job)
    
    save_jobs(existing)
    return all_new


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Jobs Monitor")
    sub = parser.add_subparsers(dest="action")
    
    sub.add_parser("once", help="Scan all repos once")
    sub.add_parser("alerts", help="Show recent job alerts")
    sub.add_parser("stats", help="Show stats")
    
    args = parser.parse_args()
    
    if args.action == "once":
        print(f"\n🔍 Scanning GitHub repos for jobs...")
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
        
        print(f"\n📋 GitHub Jobs ({len(jobs)} total)\n")
        for j in jobs[-20:]:
            print(f"  {j['found_at'][:10]} | {j['source']}")
            print(f"  {j['title']}")
            print(f"  {j['link']}")
            print()
    
    elif args.action == "stats":
        jobs = load_jobs()
        seen = load_seen()
        print(f"\n📊 GitHub Monitor Stats")
        print(f"   Total jobs found: {len(jobs)}")
        print(f"   Links seen (deduped): {len(seen)}")
        
        by_repo = {}
        for j in jobs:
            repo = j.get("source", "unknown")
            by_repo[repo] = by_repo.get(repo, 0) + 1
        
        if by_repo:
            print(f"\n   By Repository:")
            for repo, count in sorted(by_repo.items(), key=lambda x: x[1], reverse=True):
                print(f"     {repo}: {count}")
        print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()