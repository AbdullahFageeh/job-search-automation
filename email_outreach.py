#!/usr/bin/env python3
"""
Email Outreach Automation
Sends cold outreach emails, follow-ups, and cover letters via Gmail.
"""

import os
import sys
import json
import time
import logging
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("email")

EMAIL = os.getenv("EMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
PHONE = os.getenv("PHONE")
LINKEDIN_URL = os.getenv("LINKEDIN_URL")

SENT_DB = BASE_DIR / "logs" / "emails_sent.json"
CONTACTS_DB = BASE_DIR / "logs" / "contacts.json"

def load_db(path, default=None):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default or []

def save_db(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def render_template(template_name, **kwargs):
    """Render an email template."""
    template_path = BASE_DIR / "outreach" / f"{template_name}.j2"
    if template_path.exists():
        with open(template_path) as f:
            template = Template(f.read())
        return template.render(**kwargs)
    return None

def send_email(to, subject, body_html, attachments=None):
    """Send an email via Gmail."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL, GMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"✓ Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"✗ Email failed to {to}: {e}")
        return False

def get_email_body(name, company="", role="", template="warm_outreach"):
    """Generate email body based on template."""
    
    # Warm outreach (former colleague/client)
    if template == "warm_outreach":
        return f"""
        <p>Hi {name},</p>
        <p>Hope you're doing well. It's been a while since we worked together at {company}.</p>
        <p>I'm exploring a new direction — moving from hands-on event production into <strong>operations consulting</strong>, where I help organizations diagnose bottlenecks and fix workflows. Before I commit to a specific path, I wanted to ask the people who know my work best:</p>
        <p><strong>If you could hire me to solve one problem, what would it be?</strong></p>
        <p>No pressure to respond — but if you have a thought, I'd genuinely value it. And if you hear of anyone looking for an operations consultant or fractional PM, I'd appreciate an intro.</p>
        <p>Thanks for the time — and for being part of my professional journey.</p>
        <p>Best,<br>Abdullah<br>{PHONE}<br><a href="{LINKEDIN_URL}">LinkedIn</a></p>
        """
    
    # Cold outreach (industry contact)
    elif template == "cold_outreach":
        return f"""
        <p>Hi {name},</p>
        <p>I hope you're well. I've been following {company}'s work in {role or "your industry"} and wanted to reach out.</p>
        <p>I'm transitioning from live event production (F1, FIFA, Neom Beach Games) into <strong>operations consulting</strong> — helping organizations diagnose bottlenecks, redesign workflows, and improve efficiency. 6+ years of experience, PMP-trained, NEBOSH-certified.</p>
        <p>Before I fully commit to this direction, I wanted to ask: <strong>would you ever hire someone with my background to solve an operations problem at {company}?</strong> If not, what's missing?</p>
        <p>Genuinely open to feedback — no pitch here, just trying to calibrate.</p>
        <p>Best,<br>Abdullah<br>{PHONE}<br><a href="{LINKEDIN_URL}">LinkedIn</a></p>
        """
    
    # Cover letter
    elif template == "cover_letter":
        return f"""
        <p>Dear Hiring Manager,</p>
        <p>I'm an operations leader who diagnoses bottlenecks and fixes them before they become problems. Over the past 6 years, I've managed production and site operations for some of the largest live events in the world — F1 Saudi Arabian GP, FIFA Club World Cup, Riyadh Fashion Week, and Neom Beach Games.</p>
        <p>What I bring to {company}:</p>
        <ul>
            <li><strong>Root-cause diagnosis:</strong> At F1 Jeddah, I analyzed 50K+ attendee flow patterns, identified congestion points, and redesigned zone operations — cutting blockages by 25%.</li>
            <li><strong>Cross-functional leadership:</strong> Coordinated 20+ vendors and 10+ crew members simultaneously; delivered 20% ahead of schedule across 6 venues.</li>
            <li><strong>AI-driven efficiency:</strong> I automate documentation with AI tools and am PMP-trained + NEBOSH-certified.</li>
        </ul>
        <p>I'd welcome the chance to discuss how I can help {company} streamline operations and improve delivery outcomes.</p>
        <p>Thank you for your time.</p>
        <p>Best regards,<br><strong>Abdullah Fageeh</strong><br>{PHONE} · {EMAIL}<br><a href="{LINKEDIN_URL}">LinkedIn</a></p>
        """
    
    # Follow-up
    elif template == "follow_up":
        return f"""
        <p>Hi {name},</p>
        <p>Just following up on my note from {datetime.now() - timedelta(days=3)}. No pressure at all, but if you have 2 minutes to share whether you'd ever hire someone with my background for an operations problem, I'd genuinely appreciate it.</p>
        <p>Either way, hope you're doing well.</p>
        <p>Best,<br>Abdullah<br>{PHONE}<br><a href="{LINKEDIN_URL}">LinkedIn</a></p>
        """
    
    return ""

def send_outreach(contact, template="warm_outreach"):
    """Send an outreach email to a contact."""
    subject_map = {
        "warm_outreach": "Quick question — what problem would you hire me to solve?",
        "cold_outreach": f"Operations consulting — would you hire me for this?",
        "follow_up": "Following up — quick question",
        "cover_letter": f"Application: {contact.get('role', 'Operations Role')} at {contact.get('company', 'your company')}"
    }
    
    body = get_email_body(
        name=contact.get("name", "there"),
        company=contact.get("company", ""),
        role=contact.get("role", ""),
        template=template
    )
    
    subject = subject_map.get(template, "Quick question")
    
    return send_email(contact["email"], subject, body)

def run_outreach_cycle():
    """Run the outreach cycle."""
    logger.info("=== Starting Outreach Cycle ===")
    
    contacts = load_db(CONTACTS_DB, [])
    sent = load_db(SENT_DB, [])
    
    # Rate limit: max 5 emails per day
    today = datetime.now().date()
    today_sent = sum(1 for s in sent if s.get("date") == str(today))
    
    if today_sent >= 5:
        logger.info(f"Daily email limit (5) reached. {today_sent} sent today.")
        return
    
    for contact in contacts:
        if today_sent >= 5:
            break
        
        # Check if already sent this template to this contact
        already_sent = any(
            s.get("email") == contact["email"] and s.get("template") == contact.get("template", "warm_outreach")
            and (datetime.now() - datetime.fromisoformat(s.get("date", "2020-01-01"))).days < 7
            for s in sent
        )
        
        if already_sent:
            logger.info(f"Skipping {contact['email']} (recently contacted)")
            continue
        
        success = send_outreach(contact, contact.get("template", "warm_outreach"))
        
        if success:
            sent.append({
                "email": contact["email"],
                "name": contact.get("name", ""),
                "template": contact.get("template", "warm_outreach"),
                "date": str(today),
                "timestamp": datetime.now().isoformat()
            })
            save_db(SENT_DB, sent)
        
        # Human-like delay between emails
        time.sleep(random.uniform(60, 180))  # 1-3 minutes
    
    logger.info(f"Outreach cycle complete. {today_sent + 1} emails sent today.")

def add_contact(email, name="", company="", role="", template="warm_outreach"):
    """Add a contact to the outreach list."""
    contacts = load_db(CONTACTS_DB, [])
    
    # Check duplicate
    if any(c.get("email") == email for c in contacts):
        logger.info(f"Contact {email} already exists.")
        return False
    
    contacts.append({
        "email": email,
        "name": name,
        "company": company,
        "role": role,
        "template": template
    })
    save_db(CONTACTS_DB, contacts)
    logger.info(f"Added contact: {email}")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Email Outreach Automation")
    parser.add_argument("action", choices=["send", "add", "list", "stats"])
    parser.add_argument("--email", help="Contact email (for add)")
    parser.add_argument("--name", help="Contact name (for add)")
    parser.add_argument("--company", help="Contact company (for add)")
    parser.add_argument("--template", choices=["warm_outreach", "cold_outreach", "follow_up", "cover_letter"], default="warm_outreach")
    
    args = parser.parse_args()
    
    if args.action == "add":
        if not args.email:
            logger.error("Email required for add action")
            return
        add_contact(args.email, args.name, args.company, args.template)
    
    elif args.action == "send":
        run_outreach_cycle()
    
    elif args.action == "list":
        contacts = load_db(CONTACTS_DB, [])
        for c in contacts:
            print(f"{c.get('name', '')} | {c.get('company', '')} | {c['email']} | {c.get('template', '')}")
    
    elif args.action == "stats":
        sent = load_db(SENT_DB, [])
        contacts = load_db(CONTACTS_DB, [])
        today = str(datetime.now().date())
        today_count = sum(1 for s in sent if s.get("date") == today)
        print(f"Total contacts: {len(contacts)}")
        print(f"Total emails sent: {len(sent)}")
        print(f"Sent today: {today_count}")

if __name__ == "__main__":
    main()