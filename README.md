# Job Search Automation

Fully automated job search system for remote operations roles.

## Structure

```
job-search-automation/
├── dashboard.py          # Main control center
├── engine.py             # Core automation engine
├── linkedin_bot.py       # LinkedIn automation (search, apply, network)
├── email_outreach.py     # Email outreach automation
├── job_monitor.py        # Job board monitoring & alerts
├── web_scraper.py        # Webpage fetching & parsing (static + JS)
├── config/
│   └── .env              # Credentials & settings (PRIVATE)
├── resumes/              # Tailored resumes (MD + PDF)
├── outreach/             # Email templates
└── logs/                 # Application & tracking data
```

## Quick Start

```bash
# Open dashboard
cd ~/job-search-automation
python3 dashboard.py

# Or run individual tools:
python3 linkedin_bot.py              # LinkedIn automation
python3 email_outreach.py send       # Send outreach emails
python3 email_outreach.py add --email x@y.com --name "John" --company "Acme"
python3 job_monitor.py once          # Scan for new jobs
python3 job_monitor.py loop          # Continuous monitoring
```

## Setup

1. Install Playwright browsers:
```bash
playwright install chromium
```

2. Edit `.env` with your credentials (already done ✅)

3. Add contacts for outreach:
```bash
python3 email_outreach.py add --email "colleague@company.com" --name "John" --company "Acme" --template warm_outreach
```

## Automation Modes

| Mode | Command | What It Does |
|------|---------|--------------|
| **Interactive** | `python3 dashboard.py` | Menu-driven control |
| **LinkedIn Auto** | `python3 linkedin_bot.py` | Search + Easy Apply |
| **Email Outreach** | `python3 email_outreach.py send` | Send warm/cold emails |
| **Job Monitor** | `python3 job_monitor.py loop` | Scan boards every 30 min |