#!/usr/bin/env python3
"""
Application Analytics Dashboard v2.0
======================================
Track, analyze, and optimize your job search strategy.

Features:
  - Application funnel visualization
  - Response rate tracking by platform
  - Time-to-response analysis
  - Company response heat map
  - Application velocity (apps/day)
  - Best-performing job categories
  - Weekly/monthly trends
  - Export to CSV for deeper analysis
"""

import json
import sys
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from tabulate import tabulate

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ============================================================
# DATA LOADING
# ============================================================

def load_json(path, default=None):
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return default or []


def load_all_applications():
    """Load all applications from all sources."""
    sources = [
        BASE_DIR / "logs" / "linkedin_applied.json",
        BASE_DIR / "logs" / "entry_level_jobs.json",
        BASE_DIR / "logs" / "other_jobs.json",
    ]

    all_apps = []
    seen = set()
    for src in sources:
        jobs = load_json(src, [])
        for job in jobs:
            link = job.get("link") or job.get("url", "")
            if link and link not in seen:
                seen.add(link)
                all_apps.append(job)

    return all_apps


def load_alerts():
    return load_json(BASE_DIR / "logs" / "alerts_history.json", {"alerts_sent": []})


# ============================================================
# ANALYTICS ENGINE
# ============================================================

def compute_funnel(applications):
    """Compute application funnel stages."""
    statuses = Counter(a.get("status", "Applied") for a in applications)
    total = len(applications)

    # Normalize statuses
    applied = statuses.get("Applied", 0) + statuses.get("applied", 0)
    viewed = statuses.get("Viewed", 0) + statuses.get("viewed", 0)
    interviewing = statuses.get("Interviewing", 0) + statuses.get("Interview", 0)
    offered = statuses.get("Offer", 0) + statuses.get("Offered", 0)
    rejected = statuses.get("Rejected", 0) + statuses.get("rejected", 0)
    no_response = total - applied - viewed - interviewing - offered - rejected

    funnel = {
        "Applied": applied,
        "Viewed": viewed,
        "Interviewing": interviewing,
        "Offer": offered,
        "Rejected": rejected,
        "No Response": max(0, no_response),
    }
    return funnel


def compute_conversion_rates(funnel):
    """Calculate conversion rates between funnel stages."""
    total = sum(funnel.values())
    if total == 0:
        return {}

    rates = {}
    stages = ["Applied", "Viewed", "Interviewing", "Offer"]
    for i in range(len(stages) - 1):
        current = funnel.get(stages[i], 0)
        next_stage = funnel.get(stages[i+1], 0)
        if current > 0:
            rates[f"{stages[i]} → {stages[i+1]}"] = (next_stage / current) * 100
        else:
            rates[f"{stages[i]} → {stages[i+1]}"] = 0
    return rates


def compute_velocity(applications):
    """Calculate application velocity over time."""
    if not applications:
        return {}

    dates = []
    for app in applications:
        date_str = app.get("applied_at") or app.get("found_at") or app.get("date", "")
        if date_str:
            try:
                dates.append(datetime.fromisoformat(date_str[:10]))
            except (ValueError, TypeError):
                pass

    if not dates:
        return {}

    dates.sort()
    today = datetime.now()

    # Daily applications (last 30 days)
    daily = defaultdict(int)
    for d in dates:
        key = d.strftime("%Y-%m-%d")
        daily[key] += 1

    last_7 = [d for d in dates if (today - d).days <= 7]
    last_30 = [d for d in dates if (today - d).days <= 30]

    return {
        "total": len(dates),
        "daily_avg_7d": len(last_7) / 7 if last_7 else 0,
        "daily_avg_30d": len(last_30) / 30 if last_30 else 0,
        "daily_breakdown": dict(sorted(daily.items())[-14:]),  # Last 14 days
        "first_application": dates[0].strftime("%Y-%m-%d") if dates else "N/A",
        "last_application": dates[-1].strftime("%Y-%m-%d") if dates else "N/A",
    }


def compute_platform_performance(applications):
    """Analyze which platforms produce best results."""
    platform_stats = defaultdict(lambda: {"applied": 0, "viewed": 0, "interview": 0, "offer": 0})

    for app in applications:
        platform = app.get("source", "Unknown")
        status = app.get("status", "Applied").lower()
        platform_stats[platform]["applied"] += 1
        if "view" in status:
            platform_stats[platform]["viewed"] += 1
        if "interview" in status:
            platform_stats[platform]["interview"] += 1
        if "offer" in status:
            platform_stats[platform]["offer"] += 1

    # Calculate conversion rates
    results = []
    for platform, stats in sorted(platform_stats.items(), key=lambda x: -x[1]["applied"]):
        applied = stats["applied"]
        interview_rate = (stats["interview"] / applied * 100) if applied > 0 else 0
        offer_rate = (stats["offer"] / applied * 100) if applied > 0 else 0
        results.append({
            "platform": platform,
            "applied": applied,
            "viewed": stats["viewed"],
            "interview": stats["interview"],
            "offer": stats["offer"],
            "interview_rate": interview_rate,
            "offer_rate": offer_rate,
        })

    return results


def compute_company_responses(applications):
    """Track which companies respond most."""
    company_stats = defaultdict(lambda: {"applied": 0, "responded": 0, "days_to_response": []})

    for app in applications:
        company = app.get("company", "Unknown") or "Unknown"
        status = app.get("status", "Applied").lower()
        company_stats[company]["applied"] += 1

        if status in ["viewed", "interview", "interviewing", "offer", "rejected"]:
            company_stats[company]["responded"] += 1

    results = []
    for company, stats in sorted(company_stats.items(), key=lambda x: -x[1]["applied"]):
        rate = (stats["responded"] / stats["applied"] * 100) if stats["applied"] > 0 else 0
        results.append({
            "company": company,
            "applied": stats["applied"],
            "responded": stats["responded"],
            "response_rate": rate,
        })

    return results[:20]  # Top 20


def compute_category_performance(applications):
    """Which job categories get the best response."""
    category_stats = defaultdict(lambda: {"applied": 0, "responded": 0})

    for app in applications:
        title = app.get("title", "").lower()
        # Categorize
        if any(w in title for w in ["analyst", "data"]):
            cat = "Analyst"
        elif any(w in title for w in ["coordinator", "assistant"]):
            cat = "Coordinator"
        elif any(w in title for w in ["manager", "lead"]):
            cat = "Manager"
        elif any(w in title for w in ["engineer", "technical"]):
            cat = "Technical"
        else:
            cat = "Operations"

        category_stats[cat]["applied"] += 1
        status = app.get("status", "").lower()
        if status not in ["applied", ""]:
            category_stats[cat]["responded"] += 1

    results = []
    for cat, stats in sorted(category_stats.items(), key=lambda x: -x[1]["applied"]):
        rate = (stats["responded"] / stats["applied"] * 100) if stats["applied"] > 0 else 0
        results.append({
            "category": cat,
            "applied": stats["applied"],
            "responded": stats["responded"],
            "response_rate": rate,
        })

    return results


# ============================================================
# DISPLAY
# ============================================================

def print_ascii_bar(value, max_value, width=30):
    """Print an ASCII bar chart."""
    if max_value == 0:
        return "░" * width
    bars = int(width * value / max_value)
    return "█" * bars + "░" * (width - bars)


def display_dashboard():
    """Display full analytics dashboard."""
    apps = load_all_applications()
    alerts = load_alerts()

    print(f"\n{'='*70}")
    print(f"  📊 JOB SEARCH ANALYTICS DASHBOARD")
    print(f"  {datetime.now().strftime('%B %d, %Y at %H:%M')}")
    print(f"{'='*70}")

    if not apps:
        print("\n  No applications found yet. Start applying to see analytics!")
        return

    # ---- OVERVIEW ----
    funnel = compute_funnel(apps)
    rates = compute_conversion_rates(funnel)
    velocity = compute_velocity(apps)

    print(f"\n  🎯 OVERVIEW")
    print(f"  {'─'*40}")
    print(f"  Total Applications:    {len(apps)}")
    print(f"  Total Alerts Sent:     {len(alerts.get('alerts_sent', []))}")
    if velocity:
        print(f"  Applications Today:    {velocity.get('daily_avg_7d', 0):.1f}/day (7-day avg)")
        print(f"  First Application:     {velocity.get('first_application', 'N/A')}")

    # ---- FUNNEL ----
    print(f"\n  📈 APPLICATION FUNNEL")
    print(f"  {'─'*40}")
    max_val = max(funnel.values()) if funnel else 1
    for stage, count in funnel.items():
        bar = print_ascii_bar(count, max_val, 25)
        pct = (count / len(apps) * 100) if apps else 0
        print(f"  {stage:<15} {count:4d} ({pct:5.1f}%) [{bar}]")

    if rates:
        print(f"\n  📊 Conversion Rates:")
        for stage, rate in rates.items():
            print(f"     {stage}: {rate:.1f}%")

    # ---- VELOCITY ----
    if velocity:
        print(f"\n  🚀 APPLICATION VELOCITY")
        print(f"  {'─'*40}")
        daily = velocity.get("daily_breakdown", {})
        if daily:
            max_daily = max(daily.values()) if daily else 1
            for day, count in list(daily.items())[-7:]:  # Last 7 days
                bar = print_ascii_bar(count, max(max_daily, 1), 30)
                print(f"  {day}: {count:2d} apps [{bar}]")

    # ---- PLATFORM PERFORMANCE ----
    platform_stats = compute_platform_performance(apps)
    if platform_stats:
        print(f"\n  🌐 PLATFORM PERFORMANCE")
        print(f"  {'─'*40}")
        table = []
        for p in platform_stats:
            table.append([
                p["platform"][:25],
                p["applied"],
                p["interview"],
                f"{p['interview_rate']:.1f}%",
            ])
        print(tabulate(table, headers=["Platform", "Applied", "Interviews", "Rate"],
                       tablefmt="simple"))

    # ---- CATEGORY PERFORMANCE ----
    category_stats = compute_category_performance(apps)
    if category_stats:
        print(f"\n  📂 CATEGORY PERFORMANCE")
        print(f"  {'─'*40}")
        table = []
        for c in category_stats:
            table.append([
                c["category"],
                c["applied"],
                c["responded"],
                f"{c['response_rate']:.1f}%",
            ])
        print(tabulate(table, headers=["Category", "Applied", "Responded", "Rate"],
                       tablefmt="simple"))

    # ---- TOP COMPANIES ----
    company_stats = compute_company_responses(apps)
    if company_stats:
        print(f"\n  🏢 TOP COMPANIES BY APPLICATIONS")
        print(f"  {'─'*40}")
        table = []
        for c in company_stats[:10]:
            table.append([
                c["company"][:30],
                c["applied"],
                c["responded"],
                f"{c['response_rate']:.0f}%",
            ])
        print(tabulate(table, headers=["Company", "Applied", "Response", "Rate"],
                       tablefmt="simple"))

    # ---- INSIGHTS ----
    print(f"\n  💡 INSIGHTS & RECOMMENDATIONS")
    print(f"  {'─'*40}")

    # Best platform
    if platform_stats:
        best_platform = max(platform_stats, key=lambda x: x.get("interview_rate", 0))
        print(f"  ✅ Best platform: {best_platform['platform']} ({best_platform['interview_rate']:.1f}% interview rate)")

    # Best category
    if category_stats:
        best_cat = max(category_stats, key=lambda x: x.get("response_rate", 0))
        print(f"  ✅ Best category: {best_cat['category']} ({best_cat['response_rate']:.1f}% response rate)")

    # Application pace
    if velocity and velocity.get("daily_avg_7d", 0) < 5:
        print(f"  ⚠️  Low velocity: {velocity.get('daily_avg_7d', 0):.1f} apps/day — try to reach 10+/day")
    elif velocity and velocity.get("daily_avg_7d", 0) >= 10:
        print(f"  ✅ Great velocity: {velocity.get('daily_avg_7d', 0):.1f} apps/day")

    # Follow-up needed
    followup_count = 0
    for app in apps:
        date_str = app.get("applied_at") or app.get("found_at", "")
        if date_str:
            try:
                app_date = datetime.fromisoformat(date_str[:10])
                days_since = (datetime.now() - app_date).days
                if 5 <= days_since <= 14 and app.get("status", "").lower() in ["applied", ""]:
                    followup_count += 1
            except (ValueError, TypeError):
                pass

    if followup_count > 0:
        print(f"  ⏰ {followup_count} applications need follow-up (5-14 days old)")

    print(f"\n{'='*70}\n")


def export_csv():
    """Export all application data to CSV."""
    apps = load_all_applications()
    if not apps:
        print("  No applications to export")
        return

    out_path = BASE_DIR / "logs" / f"applications_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "title", "company", "location", "source", "status",
            "link", "applied_at", "found_at", "score", "notes"
        ], extrasaction="ignore")
        writer.writeheader()
        for app in apps:
            writer.writerow(app)

    print(f"  ✅ Exported {len(apps)} applications to {out_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Application Analytics Dashboard")
    parser.add_argument("action", nargs="?", choices=["dashboard", "export", "funnel", "platforms", "categories"],
                        default="dashboard", help="Action to perform")

    args = parser.parse_args()

    if args.action == "dashboard":
        display_dashboard()
    elif args.action == "export":
        export_csv()
    elif args.action == "funnel":
        apps = load_all_applications()
        funnel = compute_funnel(apps)
        rates = compute_conversion_rates(funnel)
        print(f"\n  Funnel:")
        for stage, count in funnel.items():
            print(f"    {stage}: {count}")
        print(f"\n  Conversion Rates:")
        for stage, rate in rates.items():
            print(f"    {stage}: {rate:.1f}%")
    elif args.action == "platforms":
        apps = load_all_applications()
        stats = compute_platform_performance(apps)
        table = [[p["platform"], p["applied"], p["interview"], f"{p['interview_rate']:.1f}%"] for p in stats]
        print(tabulate(table, headers=["Platform", "Applied", "Interviews", "Rate"], tablefmt="simple"))
    elif args.action == "categories":
        apps = load_all_applications()
        stats = compute_category_performance(apps)
        table = [[c["category"], c["applied"], c["responded"], f"{c['response_rate']:.1f}%"] for c in stats]
        print(tabulate(table, headers=["Category", "Applied", "Response", "Rate"], tablefmt="simple"))


if __name__ == "__main__":
    main()