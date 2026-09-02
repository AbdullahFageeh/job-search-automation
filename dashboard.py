#!/usr/bin/env python3
"""
Job Search Automation Dashboard
Central control for all automation tasks.
"""

import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# Color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BLUE}{BOLD}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}\n")

def print_status(label, value, good=True):
    color = GREEN if good else YELLOW
    print(f"  {color}{label:.<40} {value}{RESET}")

def print_section(title):
    print(f"\n{BOLD}{title}{RESET}")
    print("  " + "-" * 50)

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def dashboard():
    """Main dashboard."""
    print_header("Abdullah Fageeh — Job Search Automation Dashboard")
    
    # Stats
    applied = load_db(BASE_DIR / "logs" / "applied.json", [])
    linkedin_applied = load_db(BASE_DIR / "logs" / "linkedin_applied.json", [])
    emails_sent = load_db(BASE_DIR / "logs" / "emails_sent.json", [])
    contacts = load_db(BASE_DIR / "logs" / "contacts.json", [])
    alerts = load_db(BASE_DIR / "logs" / "alerts.json", [])
    jobs = load_db(BASE_DIR / "logs" / "jobs.json", [])
    
    today = datetime.now().date()
    today_applied = sum(1 for a in applied + linkedin_applied 
                       if a.get("date", "").startswith(str(today)))
    today_emails = sum(1 for e in emails_sent 
                       if e.get("date") == str(today))
    
    print_section("📊 Overview")
    print_status("Total applications", len(applied) + len(linkedin_applied))
    print_status("Applications today", today_applied, today_applied < 5)
    print_status("Emails sent (total)", len(emails_sent))
    print_status("Emails sent today", today_emails, today_emails < 5)
    print_status("Contacts in pipeline", len(contacts))
    print_status("Job alerts received", len(alerts))
    print_status("Jobs in database", len(jobs))
    
    print_section("📁 Files Ready")
    resumes_dir = BASE_DIR / "resumes"
    for f in sorted(resumes_dir.glob("*.pdf")):
        print_status(f.name, f"{f.stat().st_size / 1024:.1f} KB", True)
    
    print_section("🚀 Quick Actions")
    print(f"  {YELLOW}1.{RESET} Run LinkedIn automation (search + apply)")
    print(f"  {YELLOW}2.{RESET} Send email outreach cycle")
    print(f"  {YELLOW}3.{RESET} Run job monitor (one-time scan)")
    print(f"  {YELLOW}4.{RESET} Add a contact for outreach")
    print(f"  {YELLOW}5.{RESET} View recent job alerts")
    print(f"  {YELLOW}6.{RESET} View application history")
    print(f"  {YELLOW}7.{RESET} Start continuous monitor (background)")
    print(f"  {YELLOW}8.{RESET} Fetch & parse a webpage")
    print(f"  {YELLOW}9.{RESET} Extract job details from URL")
    print(f"  {YELLOW}10.{RESET} Research a company")
    print(f"  {YELLOW}11.{RESET} Check resume against a job (ATS score)")
    print(f"  {YELLOW}12.{RESET} Generate interview prep")
    print(f"  {YELLOW}13.{RESET} Generate cover letter (v1)")
    print(f"  {YELLOW}14.{RESET} Research salary for a role")
    print(f"  {YELLOW}15.{RESET} Networking pipeline (contacts)")
    print(f"  {YELLOW}16.{RESET} Follow-up scheduler")
    print(f"  {YELLOW}17.{RESET} Generate weekly report")
    print(f"  {YELLOW}18.{RESET} Reddit career insights & tips")
    print(f"  {YELLOW}19.{RESET} GitHub ops resources & templates")
    print(f"  {YELLOW}20.{RESET} Scan additional job boards (Remotive, etc.)")
    print(f"  {YELLOW}21.{RESET} 🆕 Auto-apply to entry-level jobs (Comet browser)")
    print(f"  {YELLOW}22.{RESET} ATS Resume Optimizer")
    print(f"  {YELLOW}23.{RESET} Application Tracker")
    print(f"  {YELLOW}24.{RESET} LinkedIn Profile Optimizer")
    print(f"  {YELLOW}25.{RESET} Job Alerts (old)")
    print(f"  {YELLOW}26.{RESET} Daily Digest")
    print(f"  {YELLOW}27.{RESET} 🆕 Cover Letter Generator v2 (AI-tailored)")
    print(f"  {YELLOW}28.{RESET} 🆕 Job Alerts v2 (Watch mode)")
    print(f"  {YELLOW}29.{RESET} 🆕 Analytics Dashboard (Full stats)")
    print(f"  {YELLOW}30.{RESET} 🆕 Export applications to CSV")
    print(f"  {YELLOW}31.{RESET} 🆕 Clean AI Watermarks from files")
    print(f"  {YELLOW}32.{RESET} 🆕 Scan all cover letters for AI marks")
    print(f"  {YELLOW}33.{RESET} 🆕 AI Answerer (Test / Manage cache)")
    print(f"  {YELLOW}0.{RESET} Exit")
    
    return input("\nChoose action (0-33): ")

def run_linkedin():
    print(f"\n{GREEN}Starting LinkedIn automation...{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "linkedin_bot.py")],
        cwd=str(BASE_DIR)
    )
    return result.returncode

def run_email_outreach():
    print(f"\n{GREEN}Starting email outreach cycle...{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "email_outreach.py"), "send"],
        cwd=str(BASE_DIR)
    )
    return result.returncode

def run_job_monitor():
    print(f"\n{GREEN}Running job monitor...{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "job_monitor.py"), "once"],
        cwd=str(BASE_DIR)
    )
    return result.returncode

def add_contact():
    print(f"\n{BLUE}Add a contact for outreach:{RESET}")
    email = input("  Email: ").strip()
    name = input("  Name: ").strip()
    company = input("  Company: ").strip()
    template = input("  Template [warm_outreach/cold_outreach]: ").strip() or "warm_outreach"
    
    result = subprocess.run(
        ["python3", str(BASE_DIR / "email_outreach.py"), "add",
         "--email", email, "--name", name, "--company", company, "--template", template],
        cwd=str(BASE_DIR)
    )

def view_alerts():
    print(f"\n{BLUE}Recent job alerts:{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "job_monitor.py"), "alerts"],
        cwd=str(BASE_DIR)
    )

def view_history():
    print(f"\n{BLUE}Application history:{RESET}")
    applied = load_db(BASE_DIR / "logs" / "linkedin_applied.json", [])
    if not applied:
        print("  No applications yet.")
        return
    
    for a in applied[-10:]:
        print(f"\n  {GREEN}{a.get('date', 'N/A')}{RESET} | {a.get('company', '')} | {a.get('title', '')}")
        print(f"  {YELLOW}{a.get('url', '')}{RESET}")
        print(f"  Method: {a.get('method', 'manual')}")

def start_monitor_loop():
    print(f"\n{YELLOW}Starting continuous monitor (check every 30 min)...{RESET}")
    print(f"{YELLOW}Press Ctrl+C to stop.{RESET}\n")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "job_monitor.py"), "loop", "--interval", "30"],
        cwd=str(BASE_DIR)
    )

def fetch_webpage():
    print(f"\n{BLUE}Fetch a webpage:{RESET}")
    url = input("  URL: ").strip()
    js = input("  Use browser for JS-rendered page? (y/N): ").strip().lower() == "y"
    result = subprocess.run(
        ["python3", str(BASE_DIR / "web_scraper.py"), "fetch", url, "--js"] if js
        else ["python3", str(BASE_DIR / "web_scraper.py"), "fetch", url],
        cwd=str(BASE_DIR)
    )

def extract_job_details():
    print(f"\n{BLUE}Extract job details:{RESET}")
    url = input("  Job posting URL: ").strip()
    result = subprocess.run(
        ["python3", str(BASE_DIR / "web_scraper.py"), "job", url],
        cwd=str(BASE_DIR)
    )

def research_company():
    print(f"\n{BLUE}Research a company:{RESET}")
    name = input("  Company name: ").strip()
    result = subprocess.run(
        ["python3", str(BASE_DIR / "company_research.py"), name],
        cwd=str(BASE_DIR)
    )

def run_ats_checker():
    print(f"\n{BLUE}ATS Resume Checker:{RESET}")
    resume = input("  Resume file (e.g., resumes/Abdullah_Fageeh_Resume_Ladders_BizOps.md): ").strip()
    job = input("  Job description file or URL: ").strip()
    result = subprocess.run(
        ["python3", str(BASE_DIR / "ats_checker.py"), resume, job],
        cwd=str(BASE_DIR)
    )

def run_interview_prep():
    print(f"\n{BLUE}Interview Prep Generator:{RESET}")
    role = input("  Role title (e.g., Business Operations Manager): ").strip()
    company = input("  Company name: ").strip()
    job = input("  Job description file/URL (optional, press Enter to skip): ").strip()
    cmd = ["python3", str(BASE_DIR / "interview_prep.py"), role]
    if company:
        cmd.extend(["--company", company])
    if job:
        cmd.extend(["--job", job])
    subprocess.run(cmd, cwd=str(BASE_DIR))

def generate_cover_letter():
    print(f"\n{BLUE}Cover Letter Generator:{RESET}")
    role = input("  Job title: ").strip()
    company = input("  Company name: ").strip()
    manager = input("  Hiring manager (optional): ").strip()
    job = input("  Job description file/URL (optional): ").strip()
    cmd = ["python3", str(BASE_DIR / "cover_letter.py"), role, company]
    if manager:
        cmd.extend(["--manager", manager])
    if job:
        cmd.extend(["--job", job])
    subprocess.run(cmd, cwd=str(BASE_DIR))

def run_salary_research():
    print(f"\n{BLUE}Salary Research:{RESET}")
    role = input("  Role title (e.g., Operations Manager): ").strip()
    company = input("  Company name (optional): ").strip()
    cmd = ["python3", str(BASE_DIR / "salary_research.py"), role]
    if company:
        cmd.extend(["--company", company])
    subprocess.run(cmd, cwd=str(BASE_DIR))

def run_networking():
    print(f"\n{BLUE}Networking Pipeline:{RESET}")
    print(f"  {YELLOW}a.{RESET} Add contact")
    print(f"  {YELLOW}b.{RESET} List contacts")
    print(f"  {YELLOW}c.{RESET} Contacts due for re-engagement")
    print(f"  {YELLOW}d.{RESET} Suggest reachouts")
    print(f"  {YELLOW}e.{RESET} Generate outreach message")
    print(f"  {YELLOW}f.{RESET} View stats")
    sub = input("  Choose (a-f): ").strip().lower()
    
    if sub == "a":
        name = input("  Name: ").strip()
        email = input("  Email: ").strip()
        company = input("  Company: ").strip()
        role = input("  Role: ").strip()
        tier = input("  Tier [1=close, 2=strong, 3=warm, 4=cold] (default 3): ").strip() or "3"
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "add",
                        "--name", name, "--email", email, "--company", company,
                        "--role", role, "--tier", tier], cwd=str(BASE_DIR))
    elif sub == "b":
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "list"], cwd=str(BASE_DIR))
    elif sub == "c":
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "due"], cwd=str(BASE_DIR))
    elif sub == "d":
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "suggest"], cwd=str(BASE_DIR))
    elif sub == "e":
        email = input("  Contact email/name: ").strip()
        purpose = input("  Purpose (default: operations roles): ").strip() or "operations roles"
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "message", email, "--purpose", purpose], cwd=str(BASE_DIR))
    elif sub == "f":
        subprocess.run(["python3", str(BASE_DIR / "networking.py"), "stats"], cwd=str(BASE_DIR))

def run_followup():
    print(f"\n{BLUE}Follow-up Scheduler:{RESET}")
    print(f"  {YELLOW}a.{RESET} Check due follow-ups")
    print(f"  {YELLOW}b.{RESET} Send all due follow-ups")
    print(f"  {YELLOW}c.{RESET} Send (dry run - preview only)")
    print(f"  {YELLOW}d.{RESET} List all applications with status")
    print(f"  {YELLOW}e.{RESET} Show cron schedule")
    sub = input("  Choose (a-e): ").strip().lower()
    
    if sub == "a":
        subprocess.run(["python3", str(BASE_DIR / "follow_up.py"), "due"], cwd=str(BASE_DIR))
    elif sub == "b":
        subprocess.run(["python3", str(BASE_DIR / "follow_up.py"), "send"], cwd=str(BASE_DIR))
    elif sub == "c":
        subprocess.run(["python3", str(BASE_DIR / "follow_up.py"), "send", "--dry-run"], cwd=str(BASE_DIR))
    elif sub == "d":
        subprocess.run(["python3", str(BASE_DIR / "follow_up.py"), "list"], cwd=str(BASE_DIR))
    elif sub == "e":
        subprocess.run(["python3", str(BASE_DIR / "follow_up.py"), "schedule"], cwd=str(BASE_DIR))

def run_weekly_report():
    print(f"\n{BLUE}Generating weekly report...{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "weekly_report.py")],
        cwd=str(BASE_DIR),
        capture_output=True, text=True
    )
    print(result.stdout)

def run_reddit_insights():
    print(f"\n{BLUE}Reddit Career Insights:{RESET}")
    print(f"  {YELLOW}a.{RESET} Scan for new insights")
    print(f"  {YELLOW}b.{RESET} Read saved insights")
    print(f"  {YELLOW}c.{RESET} Browse by topic")
    print(f"  {YELLOW}d.{RESET} Stats")
    sub = input("  Choose (a-d): ").strip().lower()
    
    if sub == "a":
        subprocess.run(["python3", str(BASE_DIR / "reddit_insights.py"), "once"], cwd=str(BASE_DIR))
    elif sub == "b":
        subprocess.run(["python3", str(BASE_DIR / "reddit_insights.py"), "read"], cwd=str(BASE_DIR))
    elif sub == "c":
        subprocess.run(["python3", str(BASE_DIR / "reddit_insights.py"), "tips"], cwd=str(BASE_DIR))
    elif sub == "d":
        subprocess.run(["python3", str(BASE_DIR / "reddit_insights.py"), "stats"], cwd=str(BASE_DIR))

def run_github_resources():
    print(f"\n{BLUE}GitHub Resources:{RESET}")
    print(f"  {YELLOW}a.{RESET} Scan for new resources")
    print(f"  {YELLOW}b.{RESET} Browse saved resources")
    print(f"  {YELLOW}c.{RESET} Browse by category")
    print(f"  {YELLOW}d.{RESET} Search specific topic")
    print(f"  {YELLOW}e.{RESET} Stats")
    sub = input("  Choose (a-e): ").strip().lower()
    
    if sub == "a":
        subprocess.run(["python3", str(BASE_DIR / "github_resources.py"), "scan"], cwd=str(BASE_DIR))
    elif sub == "b":
        subprocess.run(["python3", str(BASE_DIR / "github_resources.py"), "browse"], cwd=str(BASE_DIR))
    elif sub == "c":
        subprocess.run(["python3", str(BASE_DIR / "github_resources.py"), "category"], cwd=str(BASE_DIR))
    elif sub == "d":
        subprocess.run(["python3", str(BASE_DIR / "github_resources.py"), "search"], cwd=str(BASE_DIR))
    elif sub == "e":
        subprocess.run(["python3", str(BASE_DIR / "github_resources.py"), "stats"], cwd=str(BASE_DIR))

def run_other_boards():
    print(f"\n{BLUE}Additional Job Boards:{RESET}")
    print(f"  {YELLOW}a.{RESET} Scan all boards (Remotive, etc.)")
    print(f"  {YELLOW}b.{RESET} View found jobs")
    print(f"  {YELLOW}c.{RESET} Stats")
    sub = input("  Choose (a-c): ").strip().lower()
    
    if sub == "a":
        subprocess.run(["python3", str(BASE_DIR / "other_boards_monitor.py"), "once"], cwd=str(BASE_DIR))
    elif sub == "b":
        subprocess.run(["python3", str(BASE_DIR / "other_boards_monitor.py"), "alerts"], cwd=str(BASE_DIR))
    elif sub == "c":
        subprocess.run(["python3", str(BASE_DIR / "other_boards_monitor.py"), "stats"], cwd=str(BASE_DIR))

def run_auto_apply():
    print(f"\n{GREEN}🚀 Auto-Apply with Comet Browser{RESET}")
    count = input("  How many jobs to apply to? (default: 10): ").strip() or "10"
    result = subprocess.run(
        ["python3", str(BASE_DIR / "auto_apply.py"), count],
        cwd=str(BASE_DIR)
    )

def run_ats_optimizer():
    print(f"\n{BLUE}🔍 ATS Resume Optimizer:{RESET}")
    resume = input("  Resume file (press Enter for all resumes): ").strip()
    if resume:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "ats_optimizer.py"), resume],
            cwd=str(BASE_DIR)
        )
    else:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "ats_optimizer.py")],
            cwd=str(BASE_DIR)
        )

def run_tracker():
    print(f"\n{BLUE}📊 Application Tracker:{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "tracker.py")],
        cwd=str(BASE_DIR)
    )

def run_linkedin_optimizer():
    print(f"\n{BLUE}🔗 LinkedIn Profile Optimizer:{RESET}")
    headline = input("  Your current LinkedIn headline: ").strip()
    summary = input("  Your current LinkedIn summary (optional): ").strip()
    if headline:
        # Write to temp files for the optimizer
        headline_file = BASE_DIR / "config" / "linkedin_headline.txt"
        summary_file = BASE_DIR / "config" / "linkedin_summary.txt"
        headline_file.write_text(headline, encoding="utf-8")
        if summary:
            summary_file.write_text(summary, encoding="utf-8")
            subprocess.run(["python3", str(BASE_DIR / "linkedin_optimizer.py"), str(headline_file), str(summary_file)], cwd=str(BASE_DIR))
        else:
            subprocess.run(["python3", str(BASE_DIR / "linkedin_optimizer.py"), str(headline_file)], cwd=str(BASE_DIR))

def run_job_alerts():
    print(f"\n{BLUE}🔔 Job Alert System:{RESET}")
    print(f"  {YELLOW}a.{RESET} Check for new jobs once")
    print(f"  {YELLOW}b.{RESET} Start continuous monitoring")
    sub = input("  Choose (a-b): ").strip().lower()
    
    if sub == "a":
        subprocess.run(["python3", str(BASE_DIR / "job_alerts.py"), "--once"], cwd=str(BASE_DIR))
    elif sub == "b":
        interval = input("  Check interval in minutes (default: 30): ").strip() or "30"
        method = input("  Alert method [email/notification/slack] (default: email): ").strip().lower() or "email"
        subprocess.run(["python3", str(BASE_DIR / "job_alerts.py"), interval, method], cwd=str(BASE_DIR))

def run_daily_digest():
    print(f"\n{BLUE}📧 Generating Daily Digest...{RESET}")
    result = subprocess.run(
        ["python3", str(BASE_DIR / "daily_digest.py")],
        cwd=str(BASE_DIR)
    )

def main():
    while True:
        action = dashboard()
        
        if action == "0":
            print(f"\n{GREEN}Good luck with your job search! 🚀{RESET}\n")
            break
        
        elif action == "1":
            run_linkedin()
        
        elif action == "2":
            run_email_outreach()
        
        elif action == "3":
            run_job_monitor()
        
        elif action == "4":
            add_contact()
        
        elif action == "5":
            view_alerts()
        
        elif action == "6":
            view_history()
        
        elif action == "7":
            start_monitor_loop()
        
        elif action == "8":
            fetch_webpage()
        
        elif action == "9":
            extract_job_details()
        
        elif action == "10":
            research_company()
        
        elif action == "11":
            run_ats_checker()
        
        elif action == "12":
            run_interview_prep()
        
        elif action == "13":
            generate_cover_letter()
        
        elif action == "14":
            run_salary_research()
        
        elif action == "15":
            run_networking()
        
        elif action == "16":
            run_followup()
        
        elif action == "17":
            run_weekly_report()
        
        elif action == "18":
            run_reddit_insights()
        
        elif action == "19":
            run_github_resources()
        
        elif action == "20":
            run_other_boards()
        
        elif action == "21":
            run_auto_apply()
        
        elif action == "22":
            run_ats_optimizer()
        
        elif action == "23":
            run_tracker()
        
        elif action == "24":
            run_linkedin_optimizer()
        
        elif action == "25":
            run_job_alerts()
        
        elif action == "26":
            run_daily_digest()
        
        elif action == "27":
            print("\n📝 Cover Letter Generator v2 (AI-Tailored)")
            print("="*40)
            title = input("Job Title: ").strip()
            company = input("Company: ").strip()
            manager = input("Hiring Manager (optional, Enter to skip): ").strip() or None
            job_file = input("Job description file (optional, Enter to skip): ").strip() or None
            tone = input("Tone [professional/enthusiastic/concise] (default: professional): ").strip() or "professional"
            fmt = input("Format [md/txt/html/pdf] (default: md): ").strip() or "md"
            cmd = f"python3 cover_letter_v2.py '{title}' '{company}' --tone {tone} --format {fmt}"
            if manager:
                cmd += f" --manager '{manager}'"
            if job_file:
                cmd += f" --job '{job_file}'"
            os.system(cmd)

        elif action == "28":
            print("\n🔔 Job Alerts v2")
            print("="*40)
            mode = input("Mode [once/watch/digest/stats] (default: once): ").strip() or "once"
            if mode == "watch":
                interval = input("Interval in minutes (default: 15): ").strip() or "15"
                channels = input("Channels [terminal/email/slack/macos] space-separated (default: terminal): ").strip() or "terminal"
                cmd = f"python3 job_alerts_v2.py watch --interval {interval} --channels {channels}"
            elif mode == "digest":
                cmd = "python3 job_alerts_v2.py digest"
            elif mode == "stats":
                cmd = "python3 job_alerts_v2.py stats"
            else:
                channels = input("Channels [terminal/email/slack/macos] space-separated (default: terminal): ").strip() or "terminal"
                cmd = f"python3 job_alerts_v2.py once --channels {channels}"
            os.system(cmd)

        elif action == "29":
            print("\n📊 Analytics Dashboard")
            print("="*40)
            mode = input("View [dashboard/export/funnel/platforms/categories] (default: dashboard): ").strip() or "dashboard"
            os.system(f"python3 analytics_dashboard.py {mode}")

        elif action == "30":
            print("\n📤 Exporting applications to CSV...")
            os.system("python3 analytics_dashboard.py export")

        elif action == "31":
            print("\n🧹 AI Watermark Cleaner")
            print("="*40)
            print("  1. Scan a file for AI watermarks")
            print("  2. Clean a file of AI watermarks")
            print("  3. Clean all cover letters")
            print("  4. Clean all resumes")
            print("  5. Pre-send check (scan + auto-clean)")
            sub = input("\n  Choice (1-5): ").strip()
            if sub == "1":
                path = input("  File path: ").strip()
                os.system(f"python3 clean_output.py scan '{path}'")
            elif sub == "2":
                path = input("  File path: ").strip()
                os.system(f"python3 clean_output.py clean '{path}'")
            elif sub == "3":
                os.system("python3 clean_output.py clean cover_letters/")
            elif sub == "4":
                os.system("python3 clean_output.py clean resumes/")
            elif sub == "5":
                path = input("  File to send: ").strip()
                os.system(f"python3 clean_output.py pre-send '{path}'")

        elif action == "32":
            print("\n🔍 Scanning all cover letters for AI watermarks...")
            os.system("python3 clean_output.py scan cover_letters/")

        elif action == "33":
            print("\n🤖 AI Application Answerer")
            print("=" * 40)
            print("  1. Test: Answer a sample question")
            print("  2. Test: Score job suitability")
            print("  3. Test: Generate cover letter for a job")
            print("  4. View cached answers")
            print("  5. Clear answer cache")
            sub = input("\n  Choice (1-5): ").strip()
            if sub == "1":
                q = input("  Enter question: ").strip()
                os.system(f"python3 ai_answerer.py answer '{q}'")
            elif sub == "2":
                idx = input("  Job index (from entry_level_jobs.json): ").strip() or "0"
                os.system(f"python3 ai_answerer.py suitability --index {idx}")
            elif sub == "3":
                idx = input("  Job index (from entry_level_jobs.json): ").strip() or "0"
                os.system(f"python3 ai_answerer.py cover_letter --index {idx}")
            elif sub == "4":
                os.system("python3 ai_answerer.py cache show")
            elif sub == "5":
                os.system("python3 ai_answerer.py cache clear")

        else:
            print(f"\n{RED}Invalid action. Try again.{RESET}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()