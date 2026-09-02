#!/usr/bin/env python3
"""
Cover Letter Generator — Auto-generate tailored cover letters per job.
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime
from jinja2 import Template
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# Cover letter template
COVER_LETTER_TEMPLATE = """Dear {{ hiring_manager or "Hiring Manager" }},

I'm writing to express my strong interest in the {{ job_title }} role at {{ company }}. With my background in {{ primary_skill }} and a track record of {{ key_achievement }}, I'm confident I can bring immediate value to your team.

At {{ last_company }}, I {{ last_achievement }}. This experience taught me the importance of {{ relevant_insight }}, a skill I understand is critical for this role given your focus on {{ company_focus }}.

What draws me to {{ company }} is {{ company_hook }}. I'm particularly excited about {{ specific_interest }} and how my experience in {{ matching_skill }} aligns with your needs.

Here's what I'd bring to the role:

• {{ bullet_1 }}
• {{ bullet_2 }}
• {{ bullet_3 }}

I'd welcome the opportunity to discuss how my background can contribute to {{ company }}'s goals. Thank you for your time and consideration.

Best regards,
Abdullah Fageeh
{{ phone }}
{{ email }}
{{ linkedin }}
"""

# User profile data
PROFILE = {
    "primary_skills": [
        "operations leadership and process optimization",
        "business operations and strategic execution",
        "cross-functional team coordination",
        "data-driven operational decision making",
    ],
    "key_achievements": [
        "streamlining operations that reduced costs by 30% while improving quality",
        "building scalable processes that supported 3x growth",
        "leading cross-functional initiatives that improved efficiency by 40%",
        "designing operational frameworks adopted across multiple teams",
    ],
    "last_companies": ["Ladders", "Swooped", "Motive", "GitLab"],
    "last_achievements": [
        "led a major operational overhaul that reduced incident response time by 40%",
        "built a vendor management program that saved $500K annually",
        "designed and launched a new onboarding process that improved time-to-productivity by 60%",
        "automated manual workflows that saved 20+ hours per week across the team",
    ],
    "relevant_insights": [
        "operational excellence requires both data and empathy",
        "great processes are invisible to the customer but essential to the business",
        "the best operations leaders are equal parts analyst, communicator, and problem-solver",
        "continuous improvement is more valuable than perfection",
    ],
    "matching_skills": [
        "process optimization and operational efficiency",
        "stakeholder management and cross-functional leadership",
        "incident management and problem resolution",
        "workflow automation and tooling",
    ],
    "bullets": [
        "Proven ability to design and execute operational strategies that drive measurable business outcomes",
        "Experience managing complex, multi-stakeholder projects from initiation through delivery",
        "Strong analytical mindset with hands-on experience in data-driven decision making",
        "Track record of building processes that scale with company growth",
        "Deep expertise in incident management, post-mortems, and continuous improvement",
        "Ability to translate business strategy into actionable operational plans",
    ],
}

def generate_cover_letter(job_title: str, company: str, job_text: str = "", 
                          hiring_manager: str = "", format_out: str = "md") -> str:
    """Generate a tailored cover letter."""
    
    # Extract insights from job description
    company_focus = "building scalable operations"  # default
    company_hook = "your reputation for operational excellence"
    specific_interest = "the opportunity to contribute to your mission"
    
    if job_text:
        # Try to extract company info
        if "culture" in job_text.lower():
            culture_match = re.search(r'(?:culture|values|team)[\s:]+([^.\n]{10,100})', job_text.lower())
            if culture_match:
                company_hook = f"your culture of {culture_match.group(1)[:80]}"
        
        if "mission" in job_text.lower():
            mission_match = re.search(r'mission[^.]*\.?([^.]{10,100})', job_text.lower())
            if mission_match:
                specific_interest = f"your mission to {mission_match.group(1)[:80]}"
        
        # Extract what they're looking for
        if re.search(r'looking for|seeking|ideal candidate', job_text.lower()):
            focus_match = re.search(r'(?:looking for|seeking|ideal)[^.\n]{0,100}', job_text.lower())
            if focus_match:
                company_focus = focus_match.group(0)[:80]
    
    # Pick randomized elements for variety
    import random
    primary_skill = random.choice(PROFILE["primary_skills"])
    key_achievement = random.choice(PROFILE["key_achievements"])
    last_company = random.choice(PROFILE["last_companies"])
    last_achievement = random.choice(PROFILE["last_achievements"])
    relevant_insight = random.choice(PROFILE["relevant_insights"])
    matching_skill = random.choice(PROFILE["matching_skills"])
    
    bullets = random.sample(PROFILE["bullets"], 3)
    
    template = Template(COVER_LETTER_TEMPLATE)
    
    letter = template.render(
        hiring_manager=hiring_manager,
        job_title=job_title,
        company=company,
        primary_skill=primary_skill,
        key_achievement=key_achievement,
        last_company=last_company,
        last_achievement=last_achievement,
        relevant_insight=relevant_insight,
        company_focus=company_focus,
        company_hook=company_hook,
        specific_interest=specific_interest,
        matching_skill=matching_skill,
        bullet_1=bullets[0],
        bullet_2=bullets[1],
        bullet_3=bullets[2],
        phone="+966 595 266 637",
        email="AbdullahFageeh@gmail.com",
        linkedin="linkedin.com/in/abdullahfageeh",
    )
    
    if format_out == "md":
        return letter
    elif format_out == "text":
        return letter
    elif format_out == "html":
        html = letter.replace("\n\n", "<br><br>")
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto;">
        {html}
        </body>
        </html>
        """
    return letter

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cover Letter Generator")
    parser.add_argument("job_title", help="Job title")
    parser.add_argument("company", help="Company name")
    parser.add_argument("--manager", "-m", help="Hiring manager name")
    parser.add_argument("--job", "-j", help="Path to job description or URL")
    parser.add_argument("--format", "-f", choices=["md", "text", "html"], default="md")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--count", "-n", type=int, default=1, help="Generate N variations")
    
    args = parser.parse_args()
    
    job_text = ""
    if args.job:
        from web_scraper import read_job_text
        job_text = read_job_text(args.job)
    
    for i in range(args.count):
        letter = generate_cover_letter(
            args.job_title, args.company, job_text,
            args.manager, args.format
        )
        
        if args.output:
            out_path = Path(args.output)
            ext = out_path.suffix or ".md"
            filename = f"CoverLetter_{args.company.replace(' ', '_')}_{args.job_title.replace(' ', '_')}{ext}"
            if args.count > 1:
                filename = f"CoverLetter_{args.company.replace(' ', '_')}_{args.job_title.replace(' ', '_')}_{i+1}{ext}"
            Path(filename).write_text(letter, encoding="utf-8")
            print(f"✅ Cover letter saved: {filename}")
        else:
            if args.count > 1:
                print(f"\n{'='*60}")
                print(f"  Variation {i+1}")
                print(f"{'='*60}")
            print(letter)
            if args.count > 1 and i < args.count - 1:
                print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    main()