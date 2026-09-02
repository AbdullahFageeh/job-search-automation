#!/usr/bin/env python3
"""
Job Monitor — continuously searches remote job boards and alerts on new matches.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("monitor")

SEEN_DB = BASE_DIR / "logs" / "seen_jobs.json"
ALERTS_DB = BASE_DIR / "logs" / "alerts.json"

TARGET_ROLES = os.getenv("TARGET_ROLES", "operations manager,business operations,strategy operations,service operations,project manager").split(",")
AVOID_ROLES = os.getenv("AVOID_ROLES", "systems architect,automotive,SaaS,data pipeline,SQL engineer").split(",")

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def save_db(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def should_skip_job(title, description=""):
    """Check if job should be skipped based on avoidance criteria."""
    text = f"{title} {description}".lower()
    return any(avoid in text for avoid in AVOID_ROLES)

def is_relevant_job(title, description=""):
    """Check if job matches our targets."""
    text = f"{title} {description}".lower()
    return any(target in text for target in TARGET_ROLES)

class RemoteCoMonitor:
    """Monitor Remote.co for new project manager jobs."""
    
    BASE_URL = "https://remote.co/remote-jobs/project-manager"
    
    def fetch_jobs(self):
        """Fetch jobs from Remote.co."""
        try:
            resp = requests.get(self.BASE_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            
            jobs = []
            for card in soup.find_all("a", href=True):
                title = card.get_text(strip=True)
                if title and len(title) > 10 and "manager" in title.lower():
                    link = card["href"]
                    if "remote.co/job-details/" in link:
                        jobs.append({
                            "title": title,
                            "url": link if link.startswith("http") else f"https:{link}",
                            "source": "remote.co",
                            "found_at": datetime.now().isoformat()
                        })
            return jobs[:20]
        except Exception as e:
            logger.error(f"Remote.co fetch error: {e}")
            return []

class WellfoundMonitor:
    """Monitor Wellfound for new operations roles."""
    
    BASE_URL = "https://wellfound.com/role/l/operations-manager"
    
    def fetch_jobs(self):
        """Fetch jobs from Wellfound."""
        try:
            resp = requests.get(self.BASE_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(resp.text, "html.parser")
            
            jobs = []
            for card in soup.find_all("a", href=True, class_=True):
                title = card.get_text(strip=True)
                if title and len(title) > 5 and ("manager" in title.lower() or "operations" in title.lower()):
                    link = card["href"]
                    if "wellfound.com/jobs/" in link:
                        jobs.append({
                            "title": title,
                            "url": link if link.startswith("http") else f"https:{link}",
                            "source": "wellfound",
                            "found_at": datetime.now().isoformat()
                        })
            return jobs[:20]
        except Exception as e:
            logger.error(f"Wellfound fetch error: {e}")
            return []

class LinkedInMonitor:
    """Monitor LinkedIn jobs via public API."""
    
    def fetch_jobs(self, query="operations manager remote"):
        """Fetch jobs from LinkedIn public search."""
        try:
            url = f"https://www.linkedin.com/jobs/search/?{urlencode({'keywords': query, 'f_WT': '2', 'f_TPR': 'r1440'})}"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            
            if resp.status_code != 200:
                logger.warning(f"LinkedIn returned {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, "html.parser")
            jobs = []
            
            for card in soup.find_all("a", href=True, class_=True):
                if "/jobs/view/" in card["href"]:
                    title = card.get_text(strip=True)
                    if title and len(title) > 5:
                        jobs.append({
                            "title": title,
                            "url": card["href"] if card["href"].startswith("http") else f"https:www.linkedin.com{card['href']}",
                            "source": "linkedin",
                            "found_at": datetime.now().isoformat()
                        })
            
            return jobs[:20]
        except Exception as e:
            logger.error(f"LinkedIn fetch error: {e}")
            return []

def run_monitor_cycle():
    """Run one monitoring cycle."""
    logger.info("=== Starting Job Monitor Cycle ===")
    
    seen = load_db(SEEN_DB, [])
    alerts = load_db(ALERTS_DB, [])
    
    # Fetch from all sources
    all_jobs = []
    
    for source, monitor in [
        ("Remote.co", RemoteCoMonitor()),
        ("Wellfound", WellfoundMonitor()),
    ]:
        jobs = monitor.fetch_jobs()
        logger.info(f"{source}: found {len(jobs)} jobs")
        all_jobs.extend(jobs)
    
    # Filter and check for new
    new_alerts = []
    for job in all_jobs:
        url = job["url"]
        
        if url in seen:
            continue
        
        if should_skip_job(job["title"]):
            continue
        
        if not is_relevant_job(job["title"]):
            continue
        
        seen.append(url)
        alert = {
            **job,
            "alerted_at": datetime.now().isoformat()
        }
        alerts.append(alert)
        new_alerts.append(alert)
        logger.info(f"🆕 NEW MATCH: {job['title']} @ {job['source']}")
        logger.info(f"   → {job['url']}")
    
    # Update databases
    save_db(SEEN_DB, seen)
    save_db(ALERTS_DB, alerts)
    
    if new_alerts:
        logger.info(f"Found {len(new_alerts)} new matching jobs!")
        # Could send email notification here
    else:
        logger.info("No new matching jobs found.")
    
    return new_alerts

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Job Monitor")
    parser.add_argument("action", choices=["once", "loop", "alerts", "stats"])
    parser.add_argument("--interval", type=int, default=60, help="Interval in minutes (for loop mode)")
    
    args = parser.parse_args()
    
    if args.action == "once":
        run_monitor_cycle()
    
    elif args.action == "loop":
        logger.info(f"Starting continuous monitoring (interval: {args.interval} min)")
        while True:
            run_monitor_cycle()
            logger.info(f"Sleeping {args.interval} minutes...")
            time.sleep(args.interval * 60)
    
    elif args.action == "alerts":
        alerts = load_db(ALERTS_DB, [])
        for a in alerts[-20:]:  # Last 20 alerts
            print(f"{a.get('alerted_at', '')[:10]} | {a['title']} | {a['source']} | {a['url']}")
    
    elif args.action == "stats":
        seen = load_db(SEEN_DB, [])
        alerts = load_db(ALERTS_DB, [])
        print(f"Total jobs seen: {len(seen)}")
        print(f"Total alerts: {len(alerts)}")
        today = datetime.now().strftime("%Y-%m-%d")
        today_alerts = sum(1 for a in alerts if a.get("alerted_at", "").startswith(today))
        print(f"Alerts today: {today_alerts}")

if __name__ == "__main__":
    main()