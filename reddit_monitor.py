#!/usr/bin/env python3
"""
Reddit Jobs Monitor — Scrape r/remotejobs, r/forhire, r/ops, r/businessops subreddits.
Uses Playwright to bypass JS challenges.
"""

import json
import re
import time
import logging
from pathlib import Path
from datetime import datetime
from web_scraper import extract_emails

BASE_DIR = Path(__file__).parent
JOBS_FILE = BASE_DIR / "logs" / "reddit_jobs.json"
SEEN_FILE = BASE_DIR / "logs" / "reddit_seen.json"

SUBREDDITS = [
    "remotejobs",
    "forhire",
    "webmastertools",  # ops-adjacent
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
    # Must have at least one target keyword
    has_target = any(kw in combined for kw in TARGET_KEYWORDS)
    # Must NOT have avoidance keywords
    has_avoid = any(kw in combined for kw in AVOID_KEYWORDS)
    return has_target and not has_avoid


def scrape_reddit(subreddit: str) -> list:
    """Scrape a subreddit for job postings using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: playwright install chromium")
        return []

    jobs = []
    seen = load_seen()  # Load at start
    url = f"https://www.reddit.com/r/{subreddit}/hot/"
    logger.info(f"Scraping r/{subreddit}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)  # Wait for JS rendering

            # Get post elements
            posts = page.query_selector_all("a[data-click-id='t3']")
            if not posts:
                # Try alternative selector for new Reddit
                posts = page.query_selector_all("a[data-testid='click-link']")
            if not posts:
                # Try shreddit selector
                posts = page.query_selector_all("a[data-postlink]")

            for post in posts[:30]:  # Limit to 30 posts per sub
                try:
                    title = post.inner_text()
                    link = post.get_attribute("href")
                    if not link:
                        continue

                    # Make sure it's a valid Reddit link
                    if "reddit.com" not in link:
                        continue

                    # Extract post ID from link
                    post_id = re.search(r"/r/[\w]+/comments/([\w]+)", link)
                    if not post_id:
                        continue
                    post_id = post_id.group(1)

                    # Skip if already seen
                    if post_id in seen:
                        continue

                    # Check relevance
                    if not is_relevant(title):
                        continue

                    # Try to get external URL
                    external_url = None
                    try:
                        post_page = context.new_page()
                        post_page.goto(f"https://www.reddit.com{link}", wait_until="domcontentloaded", timeout=15000)
                        time.sleep(1.5)

                        # Look for external link
                        external = post_page.query_selector("a.external:has-text('Link'), a[data-click-id='body-external']")
                        if external:
                            external_url = external.get_attribute("href")

                        # Get post body for more context
                        body = post_page.inner_text(".md") or ""

                        # Check relevance with body text too
                        if not is_relevant(title, body):
                            post_page.close()
                            continue

                        # Extract emails from body
                        emails = extract_emails(body)

                        post_page.close()
                    except:
                        pass

                    jobs.append({
                        "source": f"reddit/r/{subreddit}",
                        "title": title.strip(),
                        "link": f"https://www.reddit.com{link}",
                        "external_url": external_url,
                        "post_id": post_id,
                        "emails": emails,
                        "found_at": datetime.now().isoformat(),
                        "matched_keywords": [kw for kw in TARGET_KEYWORDS if kw in title.lower()],
                    })
                    seen.add(post_id)

                except Exception as e:
                    logger.debug(f"Error processing post: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {e}")
        finally:
            browser.close()

    save_seen(seen)
    return jobs


def scan_all() -> list:
    """Scan all configured subreddits."""
    all_new = []
    for sub in SUBREDDITS:
        new_jobs = scrape_reddit(sub)
        all_new.extend(new_jobs)

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

    parser = argparse.ArgumentParser(description="Reddit Jobs Monitor")
    sub = parser.add_subparsers(dest="action")

    sub.add_parser("once", help="Scan all subreddits once")
    sub.add_parser("alerts", help="Show recent job alerts")
    sub.add_parser("stats", help="Show stats")

    args = parser.parse_args()

    if args.action == "once":
        print(f"\n🔍 Scanning Reddit subreddits...")
        new_jobs = scan_all()

        if new_jobs:
            print(f"\n✅ Found {len(new_jobs)} new matching jobs!\n")
            for j in new_jobs:
                print(f"  📌 {j['title']}")
                print(f"     {j['source']} | {j['link']}")
                if j.get('external_url'):
                    print(f"     🔗 {j['external_url']}")
                print()
        else:
            print("\n  No new matching jobs found.")

    elif args.action == "alerts":
        jobs = load_jobs()
        if not jobs:
            print("No jobs found yet.")
            return

        print(f"\n📋 Reddit Jobs ({len(jobs)} total)\n")
        for j in jobs[-20:]:  # Last 20
            print(f"  {j['found_at'][:10]} | {j['source']}")
            print(f"  {j['title']}")
            print(f"  {j['link']}")
            print()

    elif args.action == "stats":
        jobs = load_jobs()
        seen = load_seen()
        print(f"\n📊 Reddit Monitor Stats")
        print(f"   Total jobs found: {len(jobs)}")
        print(f"   Posts seen (deduped): {len(seen)}")

        by_sub = {}
        for j in jobs:
            sub = j.get("source", "unknown")
            by_sub[sub] = by_sub.get(sub, 0) + 1

        if by_sub:
            print(f"\n   By Subreddit:")
            for sub, count in sorted(by_sub.items(), key=lambda x: x[1], reverse=True):
                print(f"     {sub}: {count}")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()