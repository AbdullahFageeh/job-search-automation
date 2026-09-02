#!/usr/bin/env python3
"""
Interview Prep Generator — Generate role-specific interview questions and talking points.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

BASE_DIR = Path(__file__).parent

# Interview question banks by role type
QUESTION_BANKS = {
    "bizops": {
        "strategic": [
            "Tell me about a time you identified an operational inefficiency and fixed it.",
            "How do you prioritize competing demands from different stakeholders?",
            "Describe how you've used data to drive an operational decision.",
            "Walk me through how you'd design a new process from scratch.",
            "How do you measure success in an operations role?",
        ],
        "behavioral": [
            "Tell me about a time you had to manage a difficult stakeholder.",
            "Describe a situation where a process you built failed. What did you learn?",
            "Give an example of how you've improved cross-team collaboration.",
            "Tell me about a time you had to make a decision with incomplete data.",
        ],
        "technical": [
            "How do you approach building dashboards for operational metrics?",
            "What tools do you use for process documentation and tracking?",
            "How do you handle incident management and post-mortems?",
            "Describe your experience with workflow automation.",
        ],
        "questions_for_them": [
            "What does success look like in this role in the first 90 days?",
            "What's the biggest operational challenge the team is facing right now?",
            "How does the ops team collaborate with engineering and product?",
            "What metrics does leadership care about most?",
            "What's the tech stack the ops team uses day-to-day?",
        ],
    },
    "ops_manager": {
        "strategic": [
            "How do you align operations with business strategy?",
            "Describe how you've scaled operations as a company grew.",
            "How do you balance efficiency with customer experience?",
            "What's your approach to building and mentoring an ops team?",
            "How do you decide what to automate vs. what to keep manual?",
        ],
        "behavioral": [
            "Tell me about a time you had to push back on a stakeholder's request.",
            "Describe a process overhaul you led. What was the impact?",
            "Tell me about a time you had to handle a major incident under pressure.",
            "How do you handle conflicting priorities from leadership?",
        ],
        "leadership": [
            "How do you build a culture of accountability in ops?",
            "Describe your approach to onboarding new team members.",
            "How do you handle underperformance on your team?",
            "Tell me about a time you had to influence without authority.",
        ],
        "questions_for_them": [
            "What's the biggest operational bottleneck right now?",
            "How is the ops team structured and how does it evolve?",
            "What's the budget and headcount plan for the ops function?",
            "How does the company measure operational excellence?",
        ],
    },
    "tech_pm": {
        "strategic": [
            "How do you prioritize features in your roadmap?",
            "Describe how you've managed a product through a major pivot.",
            "How do you balance technical debt with new feature development?",
            "Walk me through your process for going from idea to launch.",
        ],
        "behavioral": [
            "Tell me about a time a project went off-track. How did you recover?",
            "Describe a conflict you had with engineering and how you resolved it.",
            "How do you handle scope creep on a project?",
            "Tell me about a product decision you made that was later proven wrong.",
        ],
        "technical": [
            "How do you work with engineering to estimate timelines?",
            "What's your experience with agile/scrum methodologies?",
            "How do you ensure technical feasibility before committing to a roadmap?",
            "Describe your experience with API integrations or system architecture.",
        ],
        "questions_for_them": [
            "What's the product vision for the next 12-18 months?",
            "How are product decisions made — data-driven or intuition?",
            "What's the engineering team's capacity like?",
            "How does product collaborate with design and marketing?",
        ],
    },
    "customer_success": {
        "strategic": [
            "How do you define and measure customer success?",
            "Describe your approach to reducing churn.",
            "How do you identify at-risk customers and intervene?",
            "What's your strategy for expanding accounts (upsell/cross-sell)?",
        ],
        "behavioral": [
            "Tell me about a time you saved a customer at risk of churn.",
            "Describe a difficult customer interaction and how you handled it.",
            "How do you balance customer needs with company resources?",
            "Tell me about a time you had to deliver bad news to a customer.",
        ],
        "operational": [
            "How do you build customer health scores?",
            "What tools do you use for customer success management?",
            "How do you handle escalations from customers?",
            "Describe your onboarding process for new customers.",
        ],
        "questions_for_them": [
            "What's the current churn rate and what's driving it?",
            "How does customer success collaborate with product and engineering?",
            "What's the customer lifecycle look like at this stage?",
            "What's the expansion revenue target for the CS team?",
        ],
    },
    "general": {
        "strengths": [
            "What are your top 3 strengths for this role?",
            "What makes you different from other candidates?",
            "Tell me about a time you exceeded expectations.",
        ],
        "challenges": [
            "What's a weakness you've worked to improve?",
            "Tell me about a failure and what you learned.",
            "How do you handle stress and tight deadlines?",
        ],
        "motivation": [
            "Why are you interested in this role/company?",
            "Where do you see yourself in 3-5 years?",
            "What motivates you in your work?",
        ],
    },
}

def generate_prep(role: str, company: str = "", job_text: str = "") -> dict:
    """Generate interview prep materials."""
    role_lower = role.lower()
    
    # Find best matching category
    category = "general"
    for key in QUESTION_BANKS:
        if key in role_lower:
            category = key
            break
    
    # Merge with general questions
    questions = {
        "category": category,
        "company": company or "Target Company",
        "role": role,
        "generated_at": datetime.now().isoformat(),
    }
    
    # Get category-specific questions
    cat_questions = QUESTION_BANKS.get(category, QUESTION_BANKS["general"])
    for qtype, q_list in cat_questions.items():
        questions[qtype] = q_list
    
    # Add general questions
    for qtype, q_list in QUESTION_BANKS["general"].items():
        if qtype not in questions:
            questions[qtype] = q_list
    
    # Extract keywords from job text for custom prep
    if job_text:
        import re
        skills = re.findall(r'\b\w+\b', job_text.lower())
        freq = {}
        for s in skills:
            if len(s) > 3 and s not in {'their', 'they', 'them', 'this', 'that', 'these', 'those', 'would', 'could', 'should'}:
                freq[s] = freq.get(s, 0) + 1
        top_skills = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:15]
        questions["key_skills_from_job"] = [s for s, c in top_skills]
    
    # Generate STAR method talking points
    questions["star_framework"] = {
        "S": "Situation — Set the context (what was the situation?)",
        "T": "Task — What was your responsibility?",
        "A": "Action — What did YOU specifically do? (use 'I' not 'we')",
        "R": "Result — What was the measurable outcome? (use numbers!)",
    }
    
    # Prepare elevator pitch
    questions["elevator_pitch_template"] = (
        "I'm an operations professional with [X] years of experience in [domain]. "
        "At [previous company], I [key achievement with metric]. "
        "I'm passionate about [relevant passion] and I'm excited about this role because [why this company/role]."
    )
    
    return questions

def format_output(prepare: dict) -> str:
    """Format interview prep for display."""
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"  Interview Prep: {prepare['role']} @ {prepare['company']}")
    output.append(f"{'='*60}\n")
    
    output.append("🎯 ELEVATOR PITCH TEMPLATE")
    output.append(f"   {prepare['elevator_pitch_template']}\n")
    
    output.append("⭐ STAR METHOD FRAMEWORK")
    for k, v in prepare['star_framework'].items():
        output.append(f"   {k}: {v}")
    output.append("")
    
    for section in ['strategic', 'behavioral', 'technical', 'leadership', 'operational']:
        if section in prepare:
            output.append(f"\n📋 {section.upper()} QUESTIONS ({len(prepare[section])})")
            for i, q in enumerate(prepare[section], 1):
                output.append(f"   {i}. {q}")
    
    if 'questions_for_them' in prepare:
        output.append(f"\n🔍 QUESTIONS TO ASK THEM ({len(prepare['questions_for_them'])})")
        for i, q in enumerate(prepare['questions_for_them'], 1):
            output.append(f"   {i}. {q}")
    
    if 'key_skills_from_job' in prepare:
        output.append(f"\n🔑 KEY SKILLS FROM JOB POSTING")
        output.append(f"   {', '.join(prepare['key_skills_from_job'])}")
    
    return "\n".join(output)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Interview Prep Generator")
    parser.add_argument("role", help="Role title (e.g., 'BizOps', 'Ops Manager')")
    parser.add_argument("--company", "-c", help="Company name")
    parser.add_argument("--job", "-j", help="Path to job description file or URL")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    args = parser.parse_args()
    
    job_text = ""
    if args.job:
        from web_scraper import read_job_text
        job_text = read_job_text(args.job)
    
    prep = generate_prep(args.role, args.company, job_text)
    
    if args.format == "json":
        print(json.dumps(prep, indent=2))
    else:
        print(format_output(prep))

if __name__ == "__main__":
    main()