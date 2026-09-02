#!/usr/bin/env python3
"""
AI Cover Letter Generator v2.0
================================
Auto-generates tailored cover letters for each job application.
Features:
  - Keyword extraction from job descriptions
  - Skill matching with your resume
  - Multiple tone options (professional, enthusiastic, concise)
  - Export to PDF, Markdown, or HTML
  - Batch generation for multiple jobs
  - ATS-optimized formatting
"""

import json
import re
import sys
import random
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# ============================================================
# USER PROFILE — Update these to match your actual background
# ============================================================
PROFILE = {
    "name": "Abdullah Fageeh",
    "email": "AbdullahFageeh@gmail.com",
    "phone": "+966 595 266 637",
    "linkedin": "linkedin.com/in/abdullahfageeh",
    "location": "Remote (Saudi Arabia / Global)",

    # Core skills to match against job descriptions
    "core_skills": [
        "Operations Management", "Process Optimization", "Business Operations",
        "Program Management", "Vendor Management", "Cross-functional Leadership",
        "Data Analysis", "Project Coordination", "Stakeholder Management",
        "Incident Management", "SOP Development", "KPI Tracking",
        "Team Leadership", "Workflow Automation", "Customer Success",
    ],

    # Achievement pool — pick the best match per job
    "achievements": [
        ("Operational Efficiency", "Led operational overhaul that reduced incident response time by 40%", "operations", "ops", "incident", "response", "efficiency"),
        ("Cost Reduction", "Built vendor management program saving $500K annually", "cost", "budget", "vendor", "procurement", "saving"),
        ("Process Improvement", "Designed onboarding process improving time-to-productivity by 60%", "onboard", "training", "process", "improve", "productivity"),
        ("Automation", "Automated manual workflows saving 20+ hours per week across the team", "automat", "workflow", "efficiency", "tool", "script"),
        ("Growth", "Built scalable processes supporting 3x company growth", "scale", "growth", "expand", "rapid"),
        ("Cross-functional", "Led cross-functional initiatives improving efficiency by 40%", "cross-functional", "stakeholder", "collaborat", "team"),
    ],

    # Company-specific hooks
    "hooks": {
        "default": [
            "your reputation for operational excellence and team development",
            "your commitment to building world-class operations teams",
            "your focus on data-driven operational excellence",
        ],
        "startup": [
            "your rapid growth and the opportunity to build operations from the ground up",
            "your innovative approach to scaling operations efficiently",
            "your mission-driven culture and focus on operational impact",
        ],
        "enterprise": [
            "your industry-leading operational standards and global reach",
            "your investment in operational excellence at scale",
            "your reputation for developing exceptional operations talent",
        ],
    },

    # Tone templates
    "tones": {
        "professional": {
            "opening": "I am writing to express my strong interest in the {title} position at {company}.",
            "closing": "I would welcome the opportunity to discuss how my background aligns with your needs. Thank you for your consideration.",
        },
        "enthusiastic": {
            "opening": "I was thrilled to find the {title} opening at {company} — it's exactly the kind of role where I can make an immediate impact.",
            "closing": "I'd love to bring my passion for operational excellence to {company}. Thank you for considering my application!",
        },
        "concise": {
            "opening": "I'm applying for the {title} role at {company}. Here's why I'm a strong fit:",
            "closing": "I'd love to discuss how I can contribute. Thank you for your time.",
        },
    },
}


# ============================================================
# COVER LETTER TEMPLATES
# ============================================================

TEMPLATES = {
    "standard": """Dear {{ hiring_manager or "Hiring Manager" }},

{{ opening }}

With {{ years_exp }} of experience in operations and business process optimization, I have a proven track record of {{ key_achievement_text }}. I'm particularly drawn to {{ company_hook }}.

Here's what I bring to the role:

{% for bullet in bullets %}
• {{ bullet }}
{% endfor %}

{{ relevant_projects }}

{{ closing }}

Best regards,
{{ name }}
{{ email }} | {{ phone }}
{{ linkedin }}
""",

    "executive": """Dear {{ hiring_manager or "Hiring Manager" }},

{{ opening }}

In my recent role at {{ last_company }}, I {{ last_achievement }}. This experience directly aligns with the key requirements of the {title} position:

{% for match in skill_matches %}
• **{{ match.skill }}**: {{ match.evidence }}
{% endfor %}

What excites me about {{ company_name }} is {{ company_hook }}. I'm eager to bring my experience in {{ primary_focus }} to your team.

{{ closing }}

Best regards,
{{ name }}
{{ email }} | {{ phone }}
{{ linkedin }}
""",
}


# ============================================================
# KEYWORD EXTRACTION & MATCHING
# ============================================================

def extract_job_keywords(job_text):
    """Extract key requirements from job description."""
    if not job_text:
        return {"skills": [], "keywords": []}

    # Common ops keywords
    ops_keywords = [
        "stakeholder", "process", "workflow", "metrics", "KPI", "OKR",
        "automation", "efficiency", "scalability", "SOP", "documentation",
        "cross-functional", "vendor", "budget", "project", "program",
        "incident", "escalation", "on-call", "post-mortem", "SLA",
        "data analysis", "SQL", "dashboard", "reporting", "analytics",
        "team management", "mentoring", "coaching", "leadership",
        "agile", "scrum", "kanban", "Jira", "Asana", "Notion",
        "Google Workspace", "Slack", "Zoom", "CRM", "ERP",
    ]

    text_lower = job_text.lower()
    found = [kw for kw in ops_keywords if kw.lower() in text_lower]

    # Extract explicit requirements
    requirements = []
    req_patterns = [
        r'(?:must|should|need|required|require)\s+(?:have|to\s+\w+\s+)?([^.]{20,120})',
        r'(?:responsibilities|responsibility)\s*:\s*([^.]{20,200})',
    ]
    for pattern in req_patterns:
        matches = re.findall(pattern, text_lower)
        requirements.extend(matches)

    return {
        "skills": found[:10],  # Top 10 matched skills
        "requirements": requirements[:3],  # Top 3 explicit requirements
        "keywords": found,
    }


def match_skills(job_text, resume_text=""):
    """Find best-matching achievements for the job."""
    keywords = extract_job_keywords(job_text)
    matched = []

    for title, desc, *keywords_tuple in PROFILE["achievements"]:
        job_kws = keywords_tuple[0] if keywords_tuple else []
        score = sum(1 for kw in job_kws if kw in job_text.lower())
        if score > 0:
            matched.append((score, title, desc))

    # Sort by match score
    matched.sort(key=lambda x: -x[0])
    return [m[1:] for m in matched[:3]]  # Top 3


def select_hook(company_name, job_text=""):
    """Select best company hook based on company type."""
    name_lower = company_name.lower()
    if any(w in name_lower for w in ["incubator", "accelerator", "startup", "vc"]):
        return random.choice(PROFILE["hooks"]["startup"])
    elif any(w in name_lower for w in ["corp", "enterprise", "global", "inc", "llc"]):
        return random.choice(PROFILE["hooks"]["enterprise"])
    else:
        return random.choice(PROFILE["hooks"]["default"])


def generate_bullets(job_text, matched_achievements):
    """Generate 3 tailored bullet points."""
    bullets = []

    # Use matched achievements
    for title, desc in matched_achievements[:2]:
        bullets.append(f"**{title}**: {desc}")

    # Add a skill-based bullet
    keywords = extract_job_keywords(job_text)
    if keywords["skills"]:
        top_skills = ", ".join(keywords["skills"][:3])
        bullets.append(f"**Technical Fit**: Strong background in {top_skills}, with hands-on experience implementing operational improvements")

    # Fill remaining from pool
    default_bullets = [
        "**Proven Track Record**: Consistently delivered operational improvements with measurable business impact",
        "**Adaptability**: Successfully operated in fast-paced, evolving environments across multiple industries",
        "**Communication**: Strong written and verbal communication skills for cross-functional collaboration",
    ]
    while len(bullets) < 3:
        bullets.append(random.choice([b for b in default_bullets if b not in bullets]))

    return bullets[:3]


# ============================================================
# GENERATION
# ============================================================

def generate_cover_letter(job_title, company, job_text="", hiring_manager="",
                          tone="professional", template="standard"):
    """Generate a tailored cover letter."""

    # Match skills to job
    matched = match_skills(job_text)
    bullets = generate_bullets(job_text, matched)
    hook = select_hook(company, job_text)

    # Select tone
    tone_data = PROFILE["tones"].get(tone, PROFILE["tones"]["professional"])

    # Pick primary achievement
    if matched:
        primary_title, primary_desc = matched[0]
        key_achievement_text = primary_desc
    else:
        key_achievement_text = "driving operational improvements that deliver measurable business results"

    # Render template
    tmpl = Template(TEMPLATES.get(template, TEMPLATES["standard"]))
    letter = tmpl.render(
        name=PROFILE["name"],
        email=PROFILE["email"],
        phone=PROFILE["phone"],
        linkedin=PROFILE["linkedin"],
        hiring_manager=hiring_manager,
        title=job_title,
        company=company,
        company_name=company,
        years_exp="5+",
        key_achievement_text=key_achievement_text,
        company_hook=hook,
        bullets=bullets,
        opening=tone_data["opening"].format(title=job_title, company=company),
        closing=tone_data["closing"].format(company=company),
        last_company="previous role",
        last_achievement="led operational improvements that delivered significant business impact",
        primary_focus="operations optimization and team development",
        relevant_projects="I'm excited about the opportunity to bring these skills to your team and help drive continued operational excellence.",
        skill_matches=[
            {"skill": m[0], "evidence": m[1]} for m in matched[:3]
        ],
    )

    return letter


def save_as_pdf(letter, output_path):
    """Save cover letter as PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import letter as page_size
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        doc = SimpleDocTemplate(str(output_path), pagesize=page_size,
                                topMargin=1*inch, bottomMargin=1*inch,
                                leftMargin=1*inch, rightMargin=1*inch)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="CoverLetter", fontName="Helvetica", fontSize=11,
            leading=16, spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name="Signature", fontName="Helvetica", fontSize=11,
            leading=14, spaceAfter=6
        ))

        elements = []
        for line in letter.split("\n"):
            if line.strip():
                if line.startswith("Best regards"):
                    elements.append(Spacer(1, 20))
                    elements.append(Paragraph(line, styles["Signature"]))
                elif line.startswith("**") and line.endswith("**"):
                    from reportlab.lib.styles import ParagraphStyle
                    bold_style = ParagraphStyle(
                        "BoldLine", fontName="Helvetica-Bold", fontSize=11, leading=16
                    )
                    clean_line = line.replace("**", "")
                    elements.append(Paragraph(clean_line, bold_style))
                else:
                    elements.append(Paragraph(line, styles["CoverLetter"]))
            else:
                elements.append(Spacer(1, 6))

        doc.build(elements)
        return True
    except Exception as e:
        print(f"  ⚠️  PDF generation failed: {e}")
        return False


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Cover Letter Generator")
    parser.add_argument("job_title", help="Job title")
    parser.add_argument("company", help="Company name")
    parser.add_argument("--manager", "-m", help="Hiring manager name")
    parser.add_argument("--job", "-j", help="Path to job description text file")
    parser.add_argument("--tone", "-t", choices=["professional", "enthusiastic", "concise"],
                        default="professional", help="Tone of letter")
    parser.add_argument("--format", "-f", choices=["md", "txt", "html", "pdf"], default="md")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--count", "-n", type=int, default=1, help="Generate N variations")
    parser.add_argument("--batch", "-b", help="JSON file with list of jobs for batch generation")

    args = parser.parse_args()

    # Batch mode
    if args.batch:
        with open(args.batch) as f:
            jobs = json.load(f)
        out_dir = Path("cover_letters")
        out_dir.mkdir(exist_ok=True)
        count = 0
        for job in jobs:
            title = job.get("title", "Position")
            company = job.get("company", "Company")
            job_text = job.get("description", "")
            letter = generate_cover_letter(title, company, job_text, tone=args.tone)
            safe_name = f"{company.replace(' ', '_')}_{title.replace(' ', '_')[:30]}".replace("/", "_")
            ext = args.format if args.format != "txt" else "txt"
            out_path = out_dir / f"CoverLetter_{safe_name}.{ext}"
            if args.format == "pdf":
                save_as_pdf(letter, str(out_path))
            else:
                out_path.write_text(letter, encoding="utf-8")
            count += 1
        print(f"✅ Generated {count} cover letters → {out_dir}/")
        return

    # Single letter
    job_text = ""
    if args.job:
        job_path = Path(args.job)
        if job_path.exists():
            job_text = job_path.read_text()

    for i in range(args.count):
        letter = generate_cover_letter(
            args.job_title, args.company, job_text,
            args.manager, args.tone
        )

        if args.output:
            out = Path(args.output)
            if args.format == "pdf":
                save_as_pdf(letter, str(out))
            else:
                out.write_text(letter, encoding="utf-8")
            print(f"✅ Cover letter saved: {out}")
        else:
            if args.count > 1:
                print(f"\n{'='*60}")
                print(f"  Variation {i+1} ({args.tone} tone)")
                print(f"{'='*60}")
            print(letter)
            if args.count > 1 and i < args.count - 1:
                print("\n" + "-"*60 + "\n")


if __name__ == "__main__":
    main()