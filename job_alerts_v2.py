#!/usr/bin/env python3
"""
Job Alert System v2.0
=====================
Instant notifications when new jobs match your criteria.
Modes:
  - watch:  Continuous monitoring with configurable interval
  - once:   One-time scan for new jobs
  - digest: Send a daily digest of all new jobs

Notification channels:
  - terminal:  Print to terminal (default)
  - email:     Send to your Gmail
  - slack:     Post to Slack webhook
  - macos:     macOS native notifications
"""

import json
import sys
import time
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

ALERTS_LOG = BASE_DIR / "logs" / "alerts_history.json"

# ============================================================
# NOTIFICATION CHANNELS
# ============================================================

def notify_terminal(job):
    """Print to terminal with formatting."""
    score = job.get("score", "N/A")
    source = job.get("source", "Unknown")
    print(f"\n{'='*60}")
    print(f"  🔔 NEW JOB ALERT — {source}")
    print(f"{'='*60}")
    print(f"  Title:    {job.get('title', 'N/A')}")
    print(f"  Company:  {job.get('company', 'N/A')}")
    print(f"  Location: {job.get('location', 'Remote')}")
    print(f"  Match:    {score}%")
    print(f"  Link:     {job.get('link', 'N/A')}")
    print(f"{'='*60}\n")


def notify_email(job):
    """Send email alert via Gmail SMTP."""
    import smtplib
    from email.mime.text import MIMEText

    to_email = os.getenv("GMAIL_EMAIL", "AbdullahFageeh@gmail.com")
    from_email = os.getenv("GMAIL_EMAIL", "AbdullahFageeh@gmail.com")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "cucfcehiapgxttyh")

    score = job.get("score", "N/A")
    subject = f"🎯 New Job: {job.get('title', 'Unknown')} at {job.get('company', '?')}"
    body = f"""
    <h2>🎯 New Job Match Found!</h2>
    <p><strong>Score:</strong> {score}% match</p>
    <h3>{job.get('title', 'N/A')}</h3>
    <p><strong>Company:</strong> {job.get('company', 'N/A')}</p>
    <p><strong>Location:</strong> {job.get('location', 'Remote')}</p>
    <p><strong>Source:</strong> {job.get('source', 'LinkedIn')}</p>
    <p><a href="{job.get('link', '#')}" style="background:#0073b1;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">📄 View Job on LinkedIn</a></p>
    <hr>
    <p style="color:#666;font-size:12px;">Alert sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Job Search Automation</p>
    """

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"  ✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        return False


def notify_macos(job):
    """Send macOS native notification."""
    title = f"New Job: {job.get('title', 'Job')[:40]}"
    message = f"{job.get('company', '?')} — {job.get('score', '?')}% match"
    script = f'display notification "{message}" with title "{title}" sound "default"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        print("  ✅ macOS notification sent")
        return True
    except Exception as e:
        print(f"  ❌ Notification failed: {e}")
        return False


def notify_slack(job):
    """Send Slack webhook alert."""
    import httpx

    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook or "YOUR" in webhook:
        print("  ⚠️  Slack webhook not configured (set SLACK_WEBHOOK_URL in .env)")
        return False

    score = job.get("score", "N/A")
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🎯 New Job Match: {score}%"}
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{job.get('title', 'Unknown')}*\nat *{job.get('company', '?')}* | {job.get('location', 'Remote')}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Job"},
                        "url": job.get("link", "#"),
                    }
                ]
            },
        ]
    }

    try:
        resp = httpx.post(webhook, json=payload, timeout=10)
        if resp.status_code == 200:
            print("  ✅ Slack alert sent")
            return True
    except Exception as e:
        print(f"  ❌ Slack failed: {e}")
    return False


NOTIFICATION_MAP = {
    "terminal": notify_terminal,
    "email": notify_email,
    "slack": notify_slack,
    "macos": notify_macos,
}


# ============================================================
# ALERT LOGGING
# ============================================================

def load_alert_history():
    if ALERTS_LOG.exists():
        with open(ALERTS_LOG) as f:
            return json.load(f)
    return {"notified_links": [], "alerts_sent": []}

def save_alert_history(history):
    with open(ALERTS_LOG, "w") as f:
        json.dump(history, f, indent=2)

def already_notified(link):
    history = load_alert_history()
    return link in history.get("notified_links", [])

def mark_notified(link):
    history = load_alert_history()
    if link not in history["notified_links"]:
        history["notified_links"].append(link)
    history["alerts_sent"].append({
        "link": link,
        "time": datetime.now().isoformat(),
    })
    # Keep only last 500
    if len(history["notified_links"]) > 500:
        history["notified_links"] = history["notified_links"][-500:]
    if len(history["alerts_sent"]) > 500:
        history["alerts_sent"] = history["alerts_sent"][-500:]
    save_alert_history(history)


# ============================================================
# JOB SCANNING
# ============================================================

def scan_for_new_jobs(include_linkedin=True):
    """Scan all sources for new jobs, return new ones only."""
    from entry_level_jobs import load_seen, load_jobs, SEARCH_SOURCES, scrape_linkedin
    from other_boards_monitor import scan_all as scan_other_boards

    new_jobs = []

    # LinkedIn scan (only if running with display)
    if include_linkedin:
        try:
            seen = load_seen()
            for source in SEARCH_SOURCES[:3]:  # Top 3 sources only for speed
                jobs = scrape_linkedin(source)
                for job in jobs:
                    if job["link"] not in seen:
                        job["alerted"] = True
                        new_jobs.append(job)
        except Exception as e:
            print(f"  ⚠️  LinkedIn scan skipped (browser not available): {e}")
    else:
        print("  ℹ️  LinkedIn scan skipped (background mode)")

    # Other boards scan (HTTP-based, works in background)
    try:
        other_new = scan_other_boards()
        for job in other_new:
            if not any(j.get("link") == job.get("link") for j in new_jobs):
                job["alerted"] = True
                new_jobs.append(job)
    except Exception as e:
        print(f"  ⚠️  Other boards scan error: {e}")

    return new_jobs


# ============================================================
# MAIN
# ============================================================

def check_new_jobs(channels=None, skip_linkedin=False):
    """Check for new jobs and send alerts."""
    if channels is None:
        channels = ["terminal"]

    print(f"\n🔍 Scanning for new jobs... ({datetime.now().strftime('%H:%M:%S')})")
    if skip_linkedin:
        print("   ⏭️  Skipping LinkedIn (background mode)")

    new_jobs = scan_for_new_jobs(include_linkedin=not skip_linkedin)

    if not new_jobs:
        print("  No new jobs found ✅")
        return 0

    alerted = 0
    for job in new_jobs:
        link = job.get("link", "")
        if already_notified(link):
            continue

        print(f"\n  🔔 {job.get('title', 'Unknown')} at {job.get('company', '?')}")

        for channel in channels:
            notifier = NOTIFICATION_MAP.get(channel)
            if notifier:
                notifier(job)

        mark_notified(link)
        alerted += 1
        time.sleep(1)  # Rate limiting

    print(f"\n✅ Alerted {alerted} new jobs")
    return alerted


def send_daily_digest():
    """Send a daily digest of all jobs found today."""
    from entry_level_jobs import load_jobs
    from other_boards_monitor import load_jobs as load_other_jobs

    today = datetime.now().strftime("%Y-%m-%d")
    all_jobs = load_jobs() + load_other_jobs()
    today_jobs = [j for j in all_jobs if j.get("found_at", "").startswith(today)]

    if not today_jobs:
        print("  No jobs found today")
        return

    # Sort by source
    by_source = defaultdict(list)
    for j in today_jobs:
        by_source[j.get("source", "Other")].append(j)

    # Build digest
    lines = [f"📊 Daily Job Digest — {today}\n", f"Total new jobs today: {len(today_jobs)}\n"]
    for source, jobs in sorted(by_source.items()):
        lines.append(f"\n--- {source} ({len(jobs)} jobs) ---")
        for j in jobs[:10]:  # Top 10 per source
            lines.append(f"  • {j.get('title', '?')} at {j.get('company', '?')}")
            lines.append(f"    {j.get('link', '')}")

    digest = "\n".join(lines)

    # Save to file
    digest_path = BASE_DIR / "logs" / f"digest_{today}.txt"
    digest_path.write_text(digest, encoding="utf-8")
    print(f"  ✅ Digest saved: {digest_path}")

    # Also send via email if configured
    if os.getenv("GMAIL_APP_PASSWORD"):
        print("  📧 Sending digest via email...")
        notify_email({"title": f"Daily Digest ({len(today_jobs)} jobs)",
                      "company": "Job Search Automation",
                      "link": f"file://{digest_path}",
                      "score": len(today_jobs)})


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Job Alert System")
    parser.add_argument("action", choices=["watch", "once", "digest", "stats"],
                        help="Action to perform")
    parser.add_argument("--interval", "-i", type=int, default=15,
                        help="Scan interval in minutes (default: 15)")
    parser.add_argument("--channels", "-c", nargs="+",
                        choices=["terminal", "email", "slack", "macos"],
                        default=["terminal"], help="Notification channels")

    args = parser.parse_args()

    if args.action == "once":
        check_new_jobs(args.channels)

    elif args.action == "watch":
        # In watch (background) mode, always skip LinkedIn — browser can't run in background
        print(f"{'='*60}")
        print(f"🔔 JOB ALERT WATCHER (Background Mode)")
        print(f"   Interval: {args.interval} minutes")
        print(f"   Channels: {', '.join(args.channels)}")
        print(f"   Sources: 8 job boards (LinkedIn skipped — use dashboard #21 for LinkedIn)")
        print(f"   Press Ctrl+C to stop")
        print(f"{'='*60}")

        while True:
            try:
                check_new_jobs(args.channels, skip_linkedin=True)
                print(f"⏳ Next scan in {args.interval} minutes...")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\n🛑 Alert watcher stopped")
                break

    elif args.action == "digest":
        send_daily_digest()

    elif args.action == "stats":
        history = load_alert_history()
        notified = len(history.get("notified_links", []))
        alerts = len(history.get("alerts_sent", []))
        print(f"\n📊 Alert Stats")
        print(f"  Total jobs alerted: {notified}")
        print(f"  Total alerts sent: {alerts}")
        if history.get("alerts_sent"):
            recent = history["alerts_sent"][-5:]
            print(f"\n  Recent alerts:")
            for a in recent:
                print(f"    {a['time'][:19]}")


if __name__ == "__main__":
    main()