#!/usr/bin/env python3
"""
Weekly Report Generator — Generate a weekly summary of job search activities.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from tabulate import tabulate

BASE_DIR = Path(__file__).parent

def load_db(path, default=None):
    p = BASE_DIR / path
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return default or []

def generate_weekly_report() -> str:
    """Generate a weekly progress report."""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    week_str_start = week_ago.isoformat()
    week_str_end = today.isoformat()
    
    # Load all data
    applied = load_db("logs/linkedin_applied.json", [])
    emails = load_db("logs/emails_sent.json", [])
    alerts = load_db("logs/alerts.json", [])
    contacts = load_db("logs/contacts.json", [])
    
    # Filter to this week
    week_applied = [a for a in applied if a.get("date", "") >= week_str_start]
    week_emails = [e for e in emails if e.get("date", "") >= week_str_start]
    week_alerts = [a for a in alerts if a.get("timestamp", "") >= week_str_start]
    
    # Stats
    total_applied = len(applied)
    total_emails = len(emails)
    total_alerts = len(alerts)
    total_contacts = len(contacts)
    
    # Companies applied to
    companies = list(set(a.get("company", "Unknown") for a in week_applied))
    
    # Report
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  Weekly Job Search Report")
    lines.append(f"  Week of {week_ago.strftime('%b %d')} - {today.strftime('%b %d, %Y')}")
    lines.append(f"{'='*60}\n")
    
    lines.append("📊 THIS WEEK'S ACTIVITY")
    lines.append(f"   Applications sent:     {len(week_applied)}")
    lines.append(f"   Emails sent:           {len(week_emails)}")
    lines.append(f"   New job alerts:        {len(week_alerts)}")
    lines.append("")
    
    lines.append("📈 CUMULATIVE TOTALS")
    lines.append(f"   Total applications:    {total_applied}")
    lines.append(f"   Total emails sent:     {total_emails}")
    lines.append(f"   Total job alerts:      {total_alerts}")
    lines.append(f"   Contacts in pipeline:  {total_contacts}")
    lines.append("")
    
    if companies:
        lines.append("🏢 COMPANIES APPLIED TO (THIS WEEK)")
        for c in sorted(companies):
            lines.append(f"   • {c}")
        lines.append("")
    
    if week_applied:
        lines.append("📝 APPLICATIONS (THIS WEEK)")
        rows = []
        for a in week_applied[-10:]:
            rows.append([
                a.get("date", "")[:10],
                a.get("company", "?"),
                a.get("title", "?"),
                a.get("method", "manual"),
            ])
        lines.append(tabulate(rows, headers=["Date", "Company", "Role", "Method"], tablefmt="simple"))
        lines.append("")
    
    # Follow-up status
    apps_needing_followup = [a for a in applied if (datetime.now().date() - datetime.fromisoformat(a["date"]).date()).days >= 3 and len(a.get("followups_sent", [])) == 0]
    if apps_needing_followup:
        lines.append("⚠️  FOLLOW-UPS NEEDED")
        lines.append(f"   {len(apps_needing_followup)} applications need follow-up emails")
        lines.append("")
    
    # Goals
    lines.append("🎯 WEEKLY GOALS")
    lines.append(f"   [{'✅' if len(week_applied) >= 10 else '⬜'}] Send 10+ applications")
    lines.append(f"   [{'✅' if len(week_emails) >= 10 else '⬜'}] Send 10+ outreach emails")
    lines.append(f"   [{'✅' if len(week_alerts) >= 5 else '⬜'}] Review 5+ new job alerts")
    lines.append(f"   [ ] Update LinkedIn profile")
    lines.append(f"   [ ] Add 3 new contacts to pipeline")
    lines.append("")
    
    lines.append("💡 TIPS FOR NEXT WEEK")
    tips = [
        "Apply early in the week (Mon-Tue) for better visibility",
        "Personalize each application with a tailored cover letter",
        "Follow up on applications from 2 weeks ago",
        "Engage with target companies' LinkedIn posts",
        "Practice interview answers for common questions",
    ]
    import random
    for tip in random.sample(tips, 3):
        lines.append(f"   • {tip}")
    lines.append("")
    
    return "\n".join(lines)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Weekly Report Generator")
    parser.add_argument("--format", "-f", choices=["text", "md"], default="text")
    parser.add_argument("--output", "-o", help="Save report to file")
    
    args = parser.parse_args()
    
    report = generate_weekly_report()
    
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"✅ Report saved to: {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()