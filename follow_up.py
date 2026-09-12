#!/usr/bin/env python3
"""
Follow-up Scheduler — Track and automate follow-up emails for applications.
Sends timed follow-ups (3 days, 7 days, 14 days) after applying.
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from email_outreach import send_email, load_db
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Follow-up templates
FOLLOW_UP_TEMPLATES = {
    "3_day": {
        "subject": "Following up: {{ job_title }} application",
        "body": """Hi {{ name }},

I applied for the {{ job_title }} role at {{ company }} a few days ago and wanted to briefly follow up.

I'm very excited about this opportunity because {{ reason }}. My experience in {{ skill }} directly aligns with what you're looking for.

I know you're likely reviewing many applications, but I'd welcome any update on the timeline. Happy to provide any additional information.

Best regards,
Abdullah Fageeh
+966 595 266 637
"""
    },
    "7_day": {
        "subject": "Checking in: {{ job_title }} at {{ company }}",
        "body": """Hi {{ name }},

I hope this week is going well. I wanted to follow up on my application for the {{ job_title }} position.

I remain very interested in this role and would love the chance to contribute to {{ company }}'s {{ goal }}. 

If there's any additional information I can provide, please let me know. I'd also be happy to jump on a quick call if that's helpful.

Best regards,
Abdullah Fageeh
+966 595 266 637
"""
    },
    "14_day": {
        "subject": "One more note on {{ job_title }} at {{ company }}",
        "body": """Hi {{ name }},

I wanted to send one final note regarding my application for the {{ job_title }} role.

I completely understand hiring takes time, but I wanted to reiterate my strong interest. My background in {{ skill }} has prepared me well for the challenges this role entails.

If the role has been filled, I'd appreciate a quick update. If not, I'd love to stay in touch for future opportunities.

Thank you for your time,
Abdullah Fageeh
+966 595 266 637
"""
    },
    "rejection_graceful": {
        "subject": "Thank you for the update",
        "body": """Hi {{ name }},

Thank you for letting me know. I appreciate you taking the time to update me.

I've learned a lot about {{ company }} during this process and remain impressed by your work in {{ domain }}. I'd love to stay connected for future opportunities that might be a good fit.

Wishing you and the team all the best.

Best regards,
Abdullah Fageeh
+966 595 266 637
"""
    },
}

def load_applications() -> list:
    """Load all applications from tracking files."""
    applied = load_db(BASE_DIR / "logs" / "linkedin_applied.json", [])
    manual = load_db(BASE_DIR / "logs" / "applied.json", [])
    return applied + manual

def get_due_followups() -> list:
    """Find applications that need follow-ups."""
    apps = load_applications()
    due = []
    today = datetime.now().date()
    
    for app in apps:
        applied_date = datetime.fromisoformat(app["date"]).date() if isinstance(app["date"], str) else app["date"]
        days_since = (today - applied_date).days
        
        # Get follow-ups already sent
        followups_sent = app.get("followups_sent", [])
        
        # Determine what's due
        if days_since >= 3 and "3_day" not in followups_sent:
            due.append({"app": app, "type": "3_day", "days_since": days_since})
        elif days_since >= 7 and "7_day" not in followups_sent:
            due.append({"app": app, "type": "7_day", "days_since": days_since})
        elif days_since >= 14 and "14_day" not in followups_sent:
            due.append({"app": app, "type": "14_day", "days_since": days_since})
    
    return due

def send_followup(app: dict, followup_type: str, dry_run: bool = False) -> dict:
    """Send a follow-up email."""
    template = FOLLOW_UP_TEMPLATES[followup_type]
    
    # Extract contact email if available
    contact_email = app.get("contact_email")
    if not contact_email:
        return {"status": "skipped", "reason": "no_contact_email"}
    
    # Render template
    from jinja2 import Template
    body = Template(template["body"]).render(
        name=app.get("contact_name", "Hiring Manager"),
        job_title=app.get("title", "the position"),
        company=app.get("company", "your company"),
        reason="the opportunity to contribute to your team",
        skill="operations and process optimization",
        goal="mission and growth",
        domain="operations",
    )
    subject = Template(template["subject"]).render(
        job_title=app.get("title", "the position"),
        company=app.get("company", "your company"),
    )
    
    result = send_email(
        to=contact_email,
        subject=subject,
        body=body,
        dry_run=dry_run,
    )
    
    # Track follow-up sent
    if not dry_run and result.get("status") == "sent":
        app.setdefault("followups_sent", []).append(followup_type)
        # Save back to logs
        apps = load_applications()
        for a in apps:
            if a.get("url") == app.get("url"):
                a["followups_sent"] = app["followups_sent"]
                break
        with open(BASE_DIR / "logs" / "linkedin_applied.json", "w") as f:
            json.dump([a for a in apps if a.get("url") == app.get("url")], f, indent=2)
    
    return result

def schedule_cron_entry() -> str:
    """Generate cron entry for automated follow-ups."""
    user = Path.home()
    script = str(BASE_DIR / "follow_up.py")
    python = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
    return f"0 9 * * 1-5 {python} {script} send >> {BASE_DIR}/logs/followups.log 2>&1"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Follow-up Scheduler")
    sub = parser.add_subparsers(dest="action")
    
    # Check due
    sub.add_parser("due", help="Show follow-ups that are due")
    
    # Send all due
    p_send = sub.add_parser("send", help="Send all due follow-ups")
    p_send.add_argument("--dry-run", action="store_true", help="Preview without sending")
    
    # Show schedule
    sub.add_parser("schedule", help="Show cron schedule entry")
    
    # List all with status
    sub.add_parser("list", help="List all applications with follow-up status")
    
    args = parser.parse_args()
    
    if args.action == "due":
        due = get_due_followups()
        if not due:
            print("✅ No follow-ups due right now.")
            return
        print(f"\n📬 {len(due)} follow-up(s) due:\n")
        for d in due:
            app = d["app"]
            print(f"  {d['type'].replace('_', ' ').title()} ({d['days_since']} days ago)")
            print(f"    Company: {app.get('company', 'N/A')}")
            print(f"    Role: {app.get('title', 'N/A')}")
            print(f"    Contact: {app.get('contact_email', 'N/A')}")
            print()
    
    elif args.action == "send":
        due = get_due_followups()
        if not due:
            print("✅ No follow-ups due right now.")
            return
        for d in due:
            print(f"\nSending {d['type'].replace('_', ' ')} follow-up to {d['app'].get('company')}...")
            result = send_followup(d['app'], d['type'], dry_run=args.dry_run)
            status = "✅" if result.get("status") == "sent" else "⚠️"
            print(f"  {status} {result.get('status', 'unknown')}: {result.get('reason', '')}")
    
    elif args.action == "schedule":
        print(f"\nAdd this to your crontab (crontab -e):")
        print(f"\n  {schedule_cron_entry()}")
        print(f"\nThis will send follow-ups automatically at 9 AM on weekdays.\n")
    
    elif args.action == "list":
        apps = load_applications()
        if not apps:
            print("No applications tracked yet.")
            return
        today = datetime.now().date()
        print(f"\n{'Company':.<20} {'Role':.<30} {'Applied':.<12} {'Days':.<6} {'Follow-ups'}")
        print("-" * 80)
        for app in apps[-20:]:  # Last 20
            applied = datetime.fromisoformat(app["date"]).date() if isinstance(app["date"], str) else app["date"]
            days = (today - applied).days
            fups = app.get("followups_sent", [])
            fup_str = ", ".join(fups) if fups else "none"
            print(f"{app.get('company', '?')[:20]:.<20} {app.get('title', '?')[:30]:.<30} {app.get('date', '?')[:12]:.<12} {days:<6} {fup_str}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()