#!/usr/bin/env python3
"""
Job Alert System — Monitors for new jobs and sends instant notifications.
Supports email, macOS notifications, and Slack webhook alerts.
"""

import json
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from browser_config import get_browser_options, get_user_agent, is_comet_available
from resume_matcher import score_resume

# Alert settings
ALERT_INTERVAL_MINUTES = int(sys.argv[1]) if len(sys.argv) > 1 else 30
NOTIFICATION_METHOD = sys.argv[2] if len(sys.argv) > 2 else "email"  # email, slack, terminal

# Resume for scoring
RESUME_PATH = BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume.md"

def send_email_alert(job):
    """Send email alert for new job."""
    import smtplib
    from email.mime.text import MIMEText
    
    to_email = "AbdullahFageeh@gmail.com"
    from_email = "AbdullahFageeh@gmail.com"
    password = "cucfcehiapgxttyh"
    
    subject = f"🔔 New Job Alert: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}"
    body = f"""
    <h2>🎯 New Entry-Level Ops Job Found!</h2>
    
    <h3>{job.get('title', 'N/A')}</h3>
    <p><strong>Company:</strong> {job.get('company', 'N/A')}</p>
    <p><strong>Location:</strong> {job.get('location', 'Remote')}</p>
    <p><strong>Link:</strong> <a href="{job.get('link', '#')}">View Job</a></p>
    <p><strong>Resume Match:</strong> {job.get('score', 'N/A')}%</p>
    
    <hr>
    <p><i>Auto-detected by Job Search Automation at {datetime.now().strftime('%Y-%m-%d %H:%M')}</i></p>
    """
    
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        print("  ✅ Email alert sent")
        return True
    except Exception as e:
        print(f"  ❌ Email alert failed: {e}")
        return False

def send_macos_notification(title, message):
    """Send macOS native notification."""
    apple_script = f"""
    display notification "{message}" with title "{title}" sound "default"
    """
    try:
        subprocess.run(["osascript", "-e", apple_script], check=True)
        print("  ✅ macOS notification sent")
        return True
    except Exception as e:
        print(f"  ❌ Notification failed: {e}")
        return False

def send_slack_alert(job):
    """Send Slack webhook alert."""
    import httpx
    
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"  # Replace with your webhook
    
    payload = {
        "text": f"🔔 New Job Alert!\n\n*{job.get('title', 'Unknown')}* at *{job.get('company', 'Unknown')}*\n"
                f"Location: {job.get('location', 'Remote')}\n"
                f"Resume Match: {job.get('score', 'N/A')}%\n"
                f"Link: {job.get('link', '#')}"
    }
    
    try:
        response = httpx.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            print("  ✅ Slack alert sent")
            return True
        else:
            print(f"  ❌ Slack alert failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Slack alert failed: {e}")
        return False

def check_new_jobs():
    """Check for new jobs and send alerts."""
    print(f"\n🔍 Checking for new jobs... ({datetime.now().strftime('%H:%M:%S')})")
    
    # Import job scanner
    from entry_level_jobs import scan_linkedin_entry_level
    
    # Get current jobs
    jobs_file = BASE_DIR / "logs" / "entry_level_jobs.json"
    existing_jobs = []
    if jobs_file.exists():
        with open(jobs_file) as f:
            existing_jobs = json.load(f)
    
    existing_links = {j["link"] for j in existing_jobs}
    
    # Scan for new jobs
    new_jobs = scan_linkedin_entry_level()
    
    # Find truly new jobs
    truly_new = []
    for job in new_jobs:
        if job.get("link") not in existing_links:
            # Score the job
            score = score_resume(RESUME_PATH, job.get("description", ""))
            job["score"] = score
            truly_new.append(job)
    
    if not truly_new:
        print("  No new jobs found")
        return
    
    print(f"  🎉 Found {len(truly_new)} new jobs!")
    
    # Send alerts for high-scoring jobs (score > 50)
    for job in truly_new:
        if job.get("score", 0) > 50:
            print(f"\n  🔔 Alert: {job['title']} at {job['company']} ({job['score']}% match)")
            
            if NOTIFICATION_METHOD == "email":
                send_email_alert(job)
            elif NOTIFICATION_METHOD == "slack":
                send_slack_alert(job)
            elif NOTIFICATION_METHOD == "notification":
                send_macos_notification(
                    "New Job Alert!",
                    f"{job['title']} at {job['company']} ({job['score']}% match)"
                )
            else:
                print(f"  → {job['link']}")

def run_alert_loop():
    """Run continuous job alert monitoring."""
    print(f"{'='*60}")
    print(f"🔔 JOB ALERT SYSTEM")
    print(f"   Interval: {ALERT_INTERVAL_MINUTES} minutes")
    print(f"   Method: {NOTIFICATION_METHOD}")
    print(f"   Comet Browser: {'✅' if is_comet_available() else '❌'}")
    print(f"{'='*60}")
    
    while True:
        try:
            check_new_jobs()
            print(f"\n⏳ Next check in {ALERT_INTERVAL_MINUTES} minutes...")
            time.sleep(ALERT_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n\n🛑 Alert system stopped")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"🔄 Retrying in {ALERT_INTERVAL_MINUTES} minutes...")
            time.sleep(ALERT_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    if "--once" in sys.argv:
        check_new_jobs()
    else:
        run_alert_loop()