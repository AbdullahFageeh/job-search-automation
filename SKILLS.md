# Job Search Automation Suite — Complete Guide

## 🚀 Quick Start

```bash
# Run full automation pipeline (scans, applies, reports)
./run_full_automation.sh 10

# Or use the interactive dashboard
python3 dashboard.py
```

## 📁 Project Structure

```
job-search-automation/
├── dashboard.py              # Central control (26 actions)
├── engine.py                 # Central orchestrator
├── run_full_automation.sh   # One-click full pipeline
│
├── 🔍 JOB DISCOVERY
│   ├── entry_level_jobs.py   # LinkedIn entry-level job scanner (Comet browser)
│   ├── job_monitor.py        # Continuous job board monitor
│   ├── other_boards_monitor.py  # Remotive, Climbladder, FlexJobs
│   ├── job_alerts.py         # Real-time job alerts (email/Slack/macOS)
│   └── reddit_monitor.py     # Reddit job thread monitoring
│
├── 📝 APPLICATION AUTOMATION
│   ├── auto_apply.py         # Auto-apply with Comet browser + resume matching
│   ├── apply_entry_level.py  # Entry-level specific applier
│   ├── linkedin_bot.py       # LinkedIn automation (search, apply, connect)
│   └── resume_matcher.py     # TF-IDF resume-job scoring
│
├── 📄 RESUME & PROFILE TOOLS
│   ├── ats_optimizer.py      # ATS compatibility scoring & tips
│   ├── ats_checker.py        # Resume vs job description scoring
│   ├── linkedin_optimizer.py # LinkedIn profile analysis
│   └── cover_letter.py       # Auto-generate tailored cover letters
│
├── 📧 OUTREACH & NETWORKING
│   ├── email_outreach.py     # Gmail outreach automation
│   ├── networking.py         # Contact pipeline management
│   ├── follow_up.py          # Automated follow-ups (3/7/14 days)
│   └── daily_digest.py       # Daily job summary email
│
├── 📊 TRACKING & ANALYTICS
│   ├── tracker.py            # Application tracker & analytics
│   ├── weekly_report.py      # Weekly summary generation
│   └── salary_research.py    # Salary data scraping
│
├── 📚 LEARNING & PREPARATION
│   ├── interview_prep.py     # Role-specific interview questions
│   ├── company_research.py   # Company research tool
│   ├── reddit_insights.py    # Career advice from Reddit
│   └── github_resources.py   # Ops templates & runbooks
│
├── 🌐 WEB & BROWSER
│   ├── browser_config.py     # Shared browser config (Comet browser)
│   ├── browser.py            # Browser launcher
│   └── web_scraper.py        # Generic webpage fetcher
│
├── 📁 Data & Storage
│   ├── resumes/              # 8 tailored resumes (MD + PDF)
│   ├── outreach/             # Email templates
│   ├── logs/                 # Job data, applications, alerts
│   └── config/               # Configuration files
│
└── 🔐 Configuration
    ├── .env                  # Credentials & settings
    └── README.md             # This file
```

## 🆕 New Skills Added (Latest)

### 1. **Comet Browser Integration** (`browser_config.py`)
- Uses Comet browser instead of default Chromium
- Better stealth against anti-bot detection
- Auto-detected at `/Applications/Comet.app`
- All scripts now use `get_browser_options()` for consistent configuration

### 2. **ATS Resume Optimizer** (`ats_optimizer.py`)
- Scores resumes against ATS systems (0-100)
- Checks: contact info, sections, keywords, action words, metrics, formatting
- Analyzes all resumes in `resumes/` folder automatically
- Provides actionable improvement suggestions

### 3. **Application Tracker** (`tracker.py`)
- Tracks all applications across all sources
- Status breakdown (Applied, Interview, Rejected, etc.)
- Analytics: applications per day/week/month
- Top companies and roles targeted
- Follow-up reminders (3-14 day window)

### 4. **LinkedIn Profile Optimizer** (`linkedin_optimizer.py`)
- Analyzes headline (220 chars max, keywords, metrics)
- Analyzes About/Summary section (structure, keywords, CTA)
- Suggested headline formats and summary structure
- Scoring system (0-140)

### 5. **Job Alert System** (`job_alerts.py`)
- Continuous monitoring for new jobs
- Resume matching (only alerts for >50% match)
- Multiple notification methods: Email, Slack, macOS notifications
- Configurable check interval (default: 30 minutes)

### 6. **Daily Digest** (`daily_digest.py`)
- Generates HTML summary of daily job search activity
- New jobs found, applications sent, follow-ups needed
- Sent to your email every morning
- Saved to `logs/digest_YYYY-MM-DD.html`

### 7. **Auto-Apply Engine** (`auto_apply.py`)
- Fully automated application pipeline
- Uses Comet browser for stealth
- Resume matching (selects best resume per company)
- Anti-detection: human-like delays, increasing wait times
- Logs all applications to `logs/linkedin_applied.json`

## 🎯 Dashboard Commands (0-26)

| # | Action | Description |
|---|--------|-------------|
| 1 | LinkedIn Automation | Search + apply via LinkedIn |
| 2 | Email Outreach | Send outreach cycle |
| 3 | Job Monitor | One-time job scan |
| 4 | Add Contact | Add to outreach pipeline |
| 5 | View Alerts | Recent job alerts |
| 6 | Application History | View past applications |
| 7 | Continuous Monitor | Background job scanning |
| 8 | Fetch Webpage | Parse any webpage |
| 9 | Job Details | Extract details from URL |
| 10 | Company Research | Research target companies |
| 11 | ATS Checker | Score resume vs job |
| 12 | Interview Prep | Generate practice questions |
| 13 | Cover Letter | Generate tailored cover letter |
| 14 | Salary Research | Research salary ranges |
| 15 | Networking | Contact pipeline management |
| 16 | Follow-up Scheduler | Automated follow-ups |
| 17 | Weekly Report | Generate weekly summary |
| 18 | Reddit Insights | Career tips from Reddit |
| 19 | GitHub Resources | Ops templates & runbooks |
| 20 | Other Job Boards | Remotive, Climbladder, etc. |
| **21** | **🆕 Auto-Apply** | **Auto-apply to jobs (Comet)** |
| **22** | **🆕 ATS Optimizer** | **Score all resumes** |
| **23** | **🆕 Application Tracker** | **Stats & analytics** |
| **24** | **🆕 LinkedIn Optimizer** | **Profile analysis** |
| **25** | **🆕 Job Alerts** | **Continuous monitoring** |
| **26** | **🆕 Daily Digest** | **Email summary** |

## 🔧 Configuration

### Browser Settings
- **Default Browser:** Comet (`/Applications/Comet.app`)
- **Fallback:** Playwright Chromium
- **User Agent:** Chrome 120 on macOS

### Resume Mapping
The auto-apply system automatically selects the best resume:
- **Tech companies** → Ladders_BizOps.pdf
- **Logistics companies** → Motive_BizOps.pdf
- **Customer Success roles** → GitLab_CS_Ops.pdf
- **Strategy roles** → Whatnot_StrategyOps.pdf
- **Default** → Operations_Coordinator.pdf

### Credentials (.env)
- LinkedIn email/password
- Gmail app password
- Target roles & salary range
- Keywords to avoid

## 📊 Current Stats

- **30 Python scripts** in the automation suite
- **8 tailored resumes** (MD + PDF each)
- **37 applications** tracked
- **Comet browser** integrated for stealth automation
- **Full pipeline**: Scan → Score → Apply → Track → Follow-up

## 🎯 Full Automation Pipeline

Run this to execute the complete workflow:
```bash
./run_full_automation.sh [num_jobs]
```

This runs:
1. Scan LinkedIn for entry-level jobs
2. Scan other job boards (Remotive, etc.)
3. Check for new jobs (alerts)
4. Auto-apply to top matches (Comet browser)
5. Generate daily digest email
6. Show application tracker

## 🔒 Anti-Detection Features

- Comet browser (real browser, not headless)
- Human-like delays (2-5 seconds randomized)
- Increasing delays between applications
- Realistic user agent strings
- Browser fingerprinting matches real user

## 📝 Notes

- **GitHub Jobs** is dead (shut down May 2019) — use GitHub Resources for templates instead
- **Wellfound** requires API key for scraping
- **Reddit** requires Playwright (blocks basic HTTP)
- **LinkedIn** may require manual login verification on first run