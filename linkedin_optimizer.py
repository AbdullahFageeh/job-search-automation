#!/usr/bin/env python3
"""
LinkedIn Profile Optimizer — Analyzes your LinkedIn profile for ATS optimization.
Provides tips for headline, summary, skills, and experience sections.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Optimal LinkedIn settings for job seekers
OPTIMAL_SETTINGS = {
    "headline_max_length": 220,
    "summary_max_length": 2600,
    "ideal_skill_count": 50,
    "min_experience_years": 2,
    "recommended_sections": [
        "About", "Experience", "Education", "Skills", "Projects", 
        "Certifications", "Volunteer Experience", "Recommendations"
    ],
    "must_have_keywords": [
        "operations", "process", "workflow", "automation", "data analysis",
        "stakeholder", "cross-functional", "project management", "metrics",
        "kpi", "optimization", "efficiency", "logistics", "supply chain",
        "customer success", "documentation", "agile", "scrum"
    ],
    "power_verbs": [
        "Achieved", "Accelerated", "Accomplished", "Automated", "Built",
        "Created", "Delivered", "Developed", "Designed", "Directed",
        "Driven", "Enhanced", "Established", "Executed", "Expanded",
        "Generated", "Implemented", "Improved", "Increased", "Innovated",
        "Launched", "Led", "Managed", "Maximized", "Optimized",
        "Orchestrated", "Organized", "Produced", "Reduced", "Resolved",
        "Streamlined", "Strengthened", "Transformed"
    ]
}

def analyze_headline(headline):
    """Analyze LinkedIn headline for optimization."""
    score = 0
    tips = []
    
    if len(headline) < 50:
        tips.append("Headline is too short. Use all 220 characters!")
    elif len(headline) > OPTIMAL_SETTINGS["headline_max_length"]:
        tips.append("Headline is too long. Trim to 220 characters.")
    else:
        score += 20
    
    # Check for keywords
    keywords_found = sum(1 for kw in OPTIMAL_SETTINGS["must_have_keywords"] if kw.lower() in headline.lower())
    if keywords_found < 3:
        tips.append("Add more role-specific keywords (operations, data analysis, metrics, etc.)")
    else:
        score += 20
    
    # Check for value proposition
    if any(char in headline for char in ["|", "•", "–", "-"]):
        score += 10  # Using separators is good
    else:
        tips.append("Use separators (| or •) to organize your headline")
    
    # Check for metrics/results
    if any(char.isdigit() for char in headline):
        score += 10
    else:
        tips.append("Add quantifiable achievements or metrics")
    
    # Check for current role
    if any(word in headline.lower() for word in ["operations", "ops", "business", "project"]):
        score += 10
    else:
        tips.append("Include your target role title")
    
    return score, tips

def analyze_summary(summary):
    """Analyze LinkedIn summary/About section."""
    score = 0
    tips = []
    
    if len(summary) < 200:
        tips.append("Summary is too brief. Aim for 3-5 paragraphs (500-1000 words)")
    elif len(summary) > OPTIMAL_SETTINGS["summary_max_length"]:
        tips.append("Summary is too long. Trim to 2600 characters max.")
    else:
        score += 20
    
    # First person check
    if "i " in summary.lower() or "i'" in summary.lower():
        score += 10
    else:
        tips.append("Write in first person ('I am...') for a personal touch")
    
    # Keywords check
    keywords_found = sum(1 for kw in OPTIMAL_SETTINGS["must_have_keywords"] if kw.lower() in summary.lower())
    if keywords_found < 5:
        tips.append("Add more industry keywords throughout your summary")
    else:
        score += 20
    
    # Call to action
    if any(phrase in summary.lower() for phrase in ["contact", "reach out", "connect", "email", "open to"]):
        score += 10
    else:
        tips.append("Add a call-to-action (invite recruiters to connect)")
    
    # Metrics/numbers
    if any(char.isdigit() for char in summary):
        score += 10
    else:
        tips.append("Include quantifiable achievements and metrics")
    
    # Paragraph structure
    paragraphs = summary.strip().split("\n\n")
    if len(paragraphs) >= 3:
        score += 10
    else:
        tips.append("Structure your summary in 3-5 paragraphs")
    
    return score, tips

def generate_recommendations(current_headline, current_summary):
    """Generate complete LinkedIn profile optimization report."""
    print(f"\n{'='*60}")
    print(f"🔗 LINKEDIN PROFILE OPTIMIZER")
    print(f"{'='*60}")
    
    # Headline Analysis
    print(f"\n📝 HEADLINE ANALYSIS")
    headline_score, headline_tips = analyze_headline(current_headline)
    print(f"  Current: \"{current_headline}\"")
    print(f"  Score: {headline_score}/70")
    print(f"  Tips:")
    for tip in headline_tips:
        print(f"    • {tip}")
    
    # Summary Analysis
    print(f"\n📄 SUMMARY/ABOUT ANALYSIS")
    summary_score, summary_tips = analyze_summary(current_summary)
    print(f"  Length: {len(current_summary)} characters")
    print(f"  Score: {summary_score}/70")
    print(f"  Tips:")
    for tip in summary_tips:
        print(f"    • {tip}")
    
    # Overall Score
    total = headline_score + summary_score
    print(f"\n{'='*60}")
    print(f"📊 OVERALL PROFILE SCORE: {total}/140")
    print(f"{'='*60}")
    
    if total >= 120:
        print("🌟 Excellent! Your profile is well-optimized")
    elif total >= 90:
        print("👍 Good! Some improvements recommended")
    elif total >= 60:
        print("⚠️  Fair — significant improvements needed")
    else:
        print("❌ Poor — major revisions recommended")
    
    # Suggested headline formats
    print(f"\n💡 SUGGESTED HEADLINE FORMATS:")
    print(f"  1. Operations Specialist | Process Improvement | Data-Driven Decision Making")
    print(f"  2. Business Operations Associate | Workflow Optimization | Cross-Functional Collaboration")
    print(f"  3. Junior Ops Manager | Logistics & Supply Chain | KPI Tracking & Reporting")
    print(f"  4. Operations Analyst | Process Automation | Stakeholder Management | SQL & Excel")
    
    # Suggested summary structure
    print(f"\n💡 SUGGESTED SUMMARY STRUCTURE:")
    print(f"  Paragraph 1: Who you are + target role")
    print(f"  Paragraph 2: Key skills + expertise areas")
    print(f"  Paragraph 3: Notable achievements + metrics")
    print(f"  Paragraph 4: What you're looking for + call-to-action")
    
    return {
        "headline_score": headline_score,
        "summary_score": summary_score,
        "total_score": total,
        "headline_tips": headline_tips,
        "summary_tips": summary_tips,
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Read from file (headline.txt and summary.txt)
        headline_file = sys.argv[1]
        summary_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        with open(headline_file) as f:
            headline = f.read().strip()
        
        summary = ""
        if summary_file and Path(summary_file).exists():
            with open(summary_file) as f:
                summary = f.read().strip()
        
        generate_recommendations(headline, summary)
    else:
        print("Usage: python3 linkedin_optimizer.py <headline.txt> [summary.txt]")
        print("\nOr enter your details interactively:")
        
        headline = input("\nYour current LinkedIn headline: ")
        summary = input("Your current LinkedIn summary (press Enter to skip): ")
        
        if headline:
            generate_recommendations(headline, summary)