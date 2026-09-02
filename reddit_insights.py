#!/usr/bin/env python3
"""
Reddit Insights Monitor — Scrape Reddit for ops/BizOps career tips,
interview advice, salary discussions, and company culture insights.
"""

import json
import re
import time
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
INSIGHTS_FILE = BASE_DIR / "logs" / "reddit_insights.json"
SEEN_FILE = BASE_DIR / "logs" / "reddit_insights_seen.json"

# Subreddits valuable for ops career advice
SUBREDDITS = {
    "operations": {"desc": "Operations professionals"},
    "BizOps": {"desc": "Business Operations"},
    "ProductManagement": {"desc": "PM career advice"},
    "ExperiencedDevs": {"desc": "Senior tech career advice"},
    "careerguidance": {"desc": "General career advice"},
    "jobs": {"desc": "General job discussions"},
}

# What we're hunting for
TOPIC_KEYWORDS = [
    "operations", "bizops", "biz ops", "ops manager", "ops lead",
    "career", "salary", "negotiat", "interview", "resume",
    "promotion", "lateral", "pivot", "switch", "remote",
    "company culture", "layoff", "resilience", "job search",
    "job search tips", "how to", "advice", "tips",
    "compensation", "offer", "comp", "equity",
    "technical program manager", "technical pm", "tpm",
    "customer success", "service delivery",
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


def load_insights() -> list:
    if INSIGHTS_FILE.exists():
        with open(INSIGHTS_FILE) as f:
            return json.load(f)
    return []


def save_insights(insights: list):
    with open(INSIGHTS_FILE, "w") as f:
        json.dump(insights, f, indent=2)


def is_relevant(title: str, text: str = "") -> bool:
    combined = (title + " " + text).lower()
    return any(kw in combined for kw in TOPIC_KEYWORDS)


def scrape_subreddit(subreddit: str, desc: str) -> list:
    """Scrape a subreddit for career insights."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright not installed")
        return []

    insights = []
    seen = load_seen()
    url = f"https://www.reddit.com/r/{subreddit}/top/?t=week"
    logger.info(f"Scraping r/{subreddit} ({desc})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)

            # Get rendered HTML
            html = page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Find post links
            posts = soup.find_all("a", href=True)
            for post in posts[:30]:
                href = post.get("href", "")
                title = post.get_text(strip=True)

                if "/comments/" not in href or not title or len(title) < 10:
                    continue

                post_id = re.search(r"/comments/([\w]+)", href)
                if not post_id:
                    continue
                post_id = post_id.group(1)

                if post_id in seen:
                    continue

                if not is_relevant(title):
                    continue

                # Get post body for more context
                body_text = ""
                try:
                    post_page = context.new_page()
                    post_page.goto(f"https://www.reddit.com{href}", wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    body_el = post_page.query_selector(".md") or post_page.query_selector("[class*='content']")
                    if body_el:
                        body_text = body_el.inner_text()[:2000]
                    post_page.close()
                except:
                    pass

                insights.append({
                    "source": f"reddit/r/{subreddit}",
                    "title": title.strip(),
                    "link": f"https://www.reddit.com{href}",
                    "snippet": body_text[:500] if body_text else "",
                    "topic_tags": [kw for kw in TOPIC_KEYWORDS if kw in title.lower()],
                    "found_at": datetime.now().isoformat(),
                })
                seen.add(post_id)

        except Exception as e:
            logger.error(f"Error scraping r/{subreddit}: {e}")
        finally:
            browser.close()

    save_seen(seen)
    return insights


def scan_all() -> list:
    all_new = []
    for sub, info in SUBREDDITS.items():
        new = scrape_subreddit(sub, info["desc"])
        all_new.extend(new)

    existing = load_insights()
    existing_ids = {i.get("link") for i in existing}
    for item in all_new:
        if item["link"] not in existing_ids:
            existing.append(item)

    save_insights(existing)
    return all_new


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Reddit Insights Monitor (tips & advice)")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("once", help="Scan for new insights")
    sub.add_parser("read", help="Show recent insights")
    sub.add_parser("tips", help="Show career tips by topic")
    sub.add_parser("stats", help="Show stats")

    args = parser.parse_args()

    if args.action == "once":
        print(f"\n🔍 Scanning Reddit for career insights...")
        new = scan_all()

        if new:
            print(f"\n✅ Found {len(new)} new insights!\n")
            for item in new:
                print(f"  📌 {item['title']}")
                print(f"     {item['source']} | {item['link']}")
                if item.get("snippet"):
                    print(f"     {item['snippet'][:120]}...")
                print(f"     Tags: {', '.join(item['topic_tags'][:3])}")
                print()
        else:
            print("\n  No new insights found.")

    elif args.action == "read":
        insights = load_insights()
        if not insights:
            print("No insights yet. Run: python3 reddit_insights.py once")
            return

        print(f"\n📖 Career Insights ({len(insights)} total)\n")
        for item in insights[-15:]:
            print(f"  {item['found_at'][:10]} | {item['source']}")
            print(f"  📌 {item['title']}")
            print(f"  🔗 {item['link']}")
            if item.get("snippet"):
                print(f"  💡 {item['snippet'][:150]}...")
            print()

    elif args.action == "tips":
        insights = load_insights()
        if not insights:
            print("No insights yet. Run: python3 reddit_insights.py once")
            return

        # Group by topic
        topics = {}
        for item in insights:
            for tag in item.get("topic_tags", []):
                topics.setdefault(tag, []).append(item)

        print(f"\n📚 Insights by Topic\n")
        for topic, items in sorted(topics.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n  {topic.upper()} ({len(items)} threads)")
            for item in items[:3]:
                print(f"    • {item['title']}")
                print(f"      {item['link']}")
        print()

    elif args.action == "stats":
        insights = load_insights()
        seen = load_seen()
        print(f"\n📊 Reddit Insights Stats")
        print(f"   Total insights saved: {len(insights)}")
        print(f"   Posts scanned (deduped): {len(seen)}")

        by_sub = {}
        for i in insights:
            sub = i.get("source", "unknown")
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