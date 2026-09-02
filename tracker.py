#!/usr/bin/env python3
"""
Application Tracker — Track, categorize, and manage all job applications.
Provides status tracking, next actions, and analytics.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

APPLIED_DB = BASE_DIR / "logs" / "linkedin_applied.json"
ENTRY_JOBS_DB = BASE_DIR / "logs" / "entry_level_jobs.json"
OTHER_JOBS_DB = BASE_DIR / "logs" / "other_jobs.json"

def load_db(path, default=None):
    if Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def load_all_applications():
    """Load all applications from all sources."""
    all_apps = []
    for db_path in [APPLIED_DB, ENTRY_JOBS_DB, OTHER_JOBS_DB]:
        all_apps.extend(load_db(db_path, []))
    
    # Deduplicate by URL/link
    seen = set()
    unique = []
    for app in all_apps:
        link = app.get("link", app.get("url", ""))
        if link and link not in seen:
            seen.add(link)
            unique.append(app)
    
    return unique

def get_stats(applications):
    """Generate statistics from applications."""
    if not applications:
        return {}
    
    statuses = Counter(app.get("status", "Applied") for app in applications)
    companies = Counter(app.get("company", "Unknown") for app in applications)
    titles = Counter(app.get("title", "Unknown") for app in applications)
    
    dates = [app.get("date", app.get("found_at", "")) for app in applications if app.get("date")]
    today = datetime.now().strftime("%Y-%m-%d")
    this_week = [d for d in dates if d and (datetime.now() - datetime.strptime(d[:10], "%Y-%m-%d")).days <= 7]
    this_month = [d for d in dates if d and (datetime.now() - datetime.strptime(d[:10], "%Y-%m-%d")).days <= 30]
    
    return {
        "total": len(applications),
        "statuses": dict(statuses),
        "top_companies": companies.most_common(10),
        "top_titles": titles.most_common(10),
        "applied_today": sum(1 for d in dates if d == today),
        "applied_this_week": len(this_week),
        "applied_this_month": len(this_month),
    }

def print_tracker():
    """Print application tracker dashboard."""
    print(f"\n{'='*60}")
    print(f"📊 APPLICATION TRACKER — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    
    applications = load_all_applications()
    stats = get_stats(applications)
    
    if not applications:
        print("\n  No applications tracked yet.")
        print("  Run auto_apply.py or entry_level_jobs.py to start applying!")
        return
    
    # Stats
    print(f"\n📈 OVERVIEW")
    print(f"  Total Applications:    {stats['total']}")
    print(f"  Applied Today:         {stats.get('applied_today', 0)}")
    print(f"  Applied This Week:     {stats.get('applied_this_week', 0)}")
    print(f"  Applied This Month:    {stats.get('applied_this_month', 0)}")
    
    # Status breakdown
    print(f"\n📊 STATUS BREAKDOWN")
    for status, count in stats.get("statuses", {}).items():
        pct = count / stats["total"] * 100
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        print(f"  {status:.<20} {count:3d} ({pct:5.1f}%) [{bar}]")
    
    # Top companies
    print(f"\n🏢 TOP COMPANIES TARGETED")
    for company, count in stats.get("top_companies", [])[:5]:
        print(f"  • {company}: {count} roles")
    
    # Top titles
    print(f"\n💼 MOST TARGETED ROLES")
    for title, count in stats.get("top_titles", [])[:5]:
        print(f"  • {title}: {count} applications")
    
    # Recent applications
    print(f"\n🕒 RECENT APPLICATIONS (Last 10)")
    recent = sorted(applications, key=lambda x: x.get("date", x.get("found_at", "")), reverse=True)[:10]
    for app in recent:
        date = app.get("date", app.get("found_at", "Unknown"))[:10]
        title = app.get("title", "Unknown")[:40]
        company = app.get("company", "Unknown")[:20]
        status = app.get("status", "Applied")
        print(f"  {date} | {status:.<12} | {title} | {company}")
    
    # Follow-ups needed
    needs_followup = []
    for app in applications:
        date_str = app.get("date", "")
        if date_str:
            app_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
            days_since = (datetime.now() - app_date).days
            if 3 <= days_since <= 14 and app.get("status") != "Rejected":
                needs_followup.append((app, days_since))
    
    if needs_followup:
        print(f"\n📧 FOLLOW-UPS NEEDED ({len(needs_followup)})")
        for app, days in sorted(needs_followup, key=lambda x: x[1])[:5]:
            print(f"  • {app.get('title', '')} at {app.get('company', '')} — {days} days ago")

if __name__ == "__main__":
    print_tracker()