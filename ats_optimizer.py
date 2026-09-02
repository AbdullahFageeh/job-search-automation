#!/usr/bin/env python3
"""
ATS Resume Optimizer — Scans resumes against ATS systems and provides optimization tips.
Uses keyword extraction, section analysis, and formatting checks.
"""

import re
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ATS common keywords for ops roles
ATS_KEYWORDS = {
    "skills": [
        "operations", "process improvement", "workflow", "automation",
        "data analysis", "stakeholder management", "cross-functional",
        "project management", "agile", "scrum", "kanban",
        "sql", "excel", "spreadsheet", "dashboard", "reporting",
        "kpi", "metrics", "analysis", "optimization",
        "logistics", "supply chain", "inventory", "procurement",
        "customer success", "customer support", "sla",
        "documentation", "runbook", "playbook", "sop",
        "jira", "asana", "notion", "slack", "confluence",
        "python", "scripting", "api", "integration",
    ],
    "education": ["bachelor", "master", "degree", "university", "gpa"],
    "certifications": ["certified", "certification", "pmp", "itil", "six sigma", "lean"],
    "leadership": ["led", "managed", "coordinated", "directed", "supervised", "mentored"],
    "action_words": [
        "achieved", "accelerated", "accomplished", "activated", "adopted",
        "analyzed", "automated", "built", "calculated", "captured",
        "coordinated", "created", "delivered", "developed", "designed",
        "directed", "documented", "driven", "enhanced", "established",
        "evaluated", "executed", "expanded", "facilitated", "generated",
        "implemented", "improved", "initiated", "increased", "innovated",
        "launched", "led", "managed", "maximized", "monitored",
        "negotiated", "optimized", "orchestrated", "organized", "overhauled",
        "planned", "produced", "promoted", "reduced", "redefined",
        "reengineered", "resolved", "restructured", "revised", "simplified",
        "streamlined", "strengthened", "structured", "streamlined",
    ],
}

def read_resume(path):
    """Read resume content (supports .md, .txt, .pdf via text extraction)."""
    p = Path(path)
    if not p.exists():
        print(f"❌ File not found: {path}")
        return ""
    
    if p.suffix == ".pdf":
        # For PDF, try to extract text
        try:
            import PyPDF2
            import io
            with open(p, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except:
            print("⚠️  PDF parsing failed. Install PyPDF2 or use .md files.")
            return ""
    
    return p.read_text(encoding="utf-8")

def extract_keywords(text):
    """Extract keywords from text."""
    words = re.findall(r"\b\w+\b", text.lower())
    return Counter(words)

def check_section(headers, section):
    """Check if a section header exists in resume."""
    for header in headers:
        if header.lower() in [h.lower() for h in headers]:
            return True
    return False

def analyze_resume(resume_path):
    """Analyze resume for ATS compatibility."""
    text = read_resume(resume_path)
    if not text:
        return
    
    print(f"\n{'='*60}")
    print(f"📄 ATS Resume Analysis: {Path(resume_path).name}")
    print(f"{'='*60}")
    
    words = text.lower().split()
    keywords = extract_keywords(text)
    
    # Score components
    scores = {}
    issues = []
    suggestions = []
    
    # 1. Contact Info Check
    print("\n📋 CONTACT INFO")
    has_email = bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text))
    has_phone = bool(re.search(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}", text))
    has_location = any(city in text.lower() for city in ["city", "state", "country", "location", "based in"])
    
    scores["contact"] = sum([has_email, has_phone, has_location]) / 3 * 20
    print(f"  Email: {'✅' if has_email else '❌'}")
    print(f"  Phone: {'✅' if has_phone else '❌'}")
    print(f"  Location: {'✅' if has_location else '⚠️'}")
    
    if not has_email:
        issues.append("Missing email address")
    if not has_phone:
        issues.append("Missing phone number")
    
    # 2. Section Headers Check
    print("\n📑 SECTION HEADERS")
    required_sections = ["experience", "education", "skills", "summary", "objective"]
    found_sections = []
    
    for section in required_sections:
        if section.lower() in text.lower():
            found_sections.append(section)
            print(f"  ✅ {section.capitalize()}")
        else:
            print(f"  ❌ {section.capitalize()}")
            suggestions.append(f"Add a '{section}' section")
    
    scores["sections"] = len(found_sections) / len(required_sections) * 15
    
    # 3. Keyword Matching
    print("\n🔑 KEYWORD MATCHING")
    matched_keywords = []
    for keyword in ATS_KEYWORDS["skills"]:
        if keyword in text.lower():
            matched_keywords.append(keyword)
    
    keyword_score = len(matched_keywords) / len(ATS_KEYWORDS["skills"]) * 30
    scores["keywords"] = min(keyword_score, 30)
    print(f"  Matched: {len(matched_keywords)}/{len(ATS_KEYWORDS['skills'])} ATS keywords")
    
    if len(matched_keywords) < 10:
        missing = set(ATS_KEYWORDS["skills"]) - set(matched_keywords)
        top_missing = sorted(missing, key=lambda k: text.lower().count(k))[:10]
        suggestions.append(f"Add these keywords: {', '.join(top_missing[:5])}")
    
    # 4. Action Words
    print("\n💪 ACTION WORDS")
    action_count = sum(1 for word in ATS_KEYWORDS["action_words"] if word in text.lower())
    action_score = min(action_count / 10, 1) * 15
    scores["action_words"] = action_score
    print(f"  Found {action_count} strong action words")
    
    if action_count < 5:
        suggestions.append("Use more action verbs (achieved, led, optimized, etc.)")
    
    # 5. Metrics & Numbers
    print("\n📊 METRICS & QUANTIFIABLE RESULTS")
    numbers = re.findall(r"\d+%|\d+[kK]+|\d+\+|[\$£]\d+", text)
    metrics_score = min(len(numbers) / 5, 1) * 10
    scores["metrics"] = metrics_score
    print(f"  Found {len(numbers)} quantified results: {', '.join(numbers[:10])}")
    
    if len(numbers) < 3:
        suggestions.append("Add more metrics (%, $, numbers) to quantify achievements")
    
    # 6. Formatting Checks
    print("\n🎨 FORMATTING")
    has_bullet = "•" in text or "•" in text or "-" in text or "*" in text
    has_dates = bool(re.search(r"\b(20\d{2}|19\d{2})\b", text))
    has_bullet_points = text.count("\n") > 20  # Rough check for bullet points
    
    format_score = sum([has_bullet, has_dates, has_bullet_points]) / 3 * 10
    scores["formatting"] = format_score
    print(f"  Bullet points: {'✅' if has_bullet else '❌'}")
    print(f"  Dates: {'✅' if has_dates else '❌'}")
    print(f"  Structured layout: {'✅' if has_bullet_points else '⚠️'}")
    
    if not has_bullet:
        suggestions.append("Use bullet points for achievements")
    if not has_dates:
        suggestions.append("Add dates for all positions")
    
    # 7. Length Check
    print("\n📏 LENGTH")
    word_count = len(words)
    page_estimate = word_count / 250  # Rough estimate
    length_score = 10 if 250 <= word_count <= 750 else 5 if 200 <= word_count <= 1000 else 2
    scores["length"] = length_score
    print(f"  Word count: {word_count} (~{page_estimate:.1f} pages)")
    print(f"  Status: {'✅ Good' if 250 <= word_count <= 750 else '⚠️ Consider optimizing'}")
    
    # Total Score
    total = sum(scores.values())
    print(f"\n{'='*60}")
    print(f"📊 ATS SCORE: {total:.0f}/100")
    print(f"{'='*60}")
    
    if total >= 80:
        print("🌟 Excellent! Resume is ATS-optimized")
    elif total >= 60:
        print("👍 Good! Some improvements needed")
    elif total >= 40:
        print("⚠️  Fair — significant improvements needed")
    else:
        print("❌ Poor — major revisions recommended")
    
    if issues:
        print(f"\n🚨 Critical Issues:")
        for issue in issues:
            print(f"  • {issue}")
    
    if suggestions:
        print(f"\n💡 Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    return {
        "score": total,
        "scores": scores,
        "issues": issues,
        "suggestions": suggestions,
        "matched_keywords": matched_keywords,
    }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_resume(sys.argv[1])
    else:
        print("Usage: python3 ats_optimizer.py <resume_file>")
        print("\nAnalyzing all resumes in resumes/ folder...")
        for resume in sorted((BASE_DIR / "resumes").glob("*.md")):
            analyze_resume(resume)