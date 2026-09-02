#!/usr/bin/env python3
"""
ATS Resume Checker — Score your resume against job descriptions.
Checks keyword matching, formatting, and ATS compatibility.
"""

import re
import json
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

import nltk
from nltk.corpus import stopwords
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

STOP_WORDS = set(stopwords.words('english'))

# Key ops/BizOps skill keywords
OPS_KEYWORDS = {
    "senior": ["operations", "ops", "process", "workflow", "efficiency", "optimization",
               "stakeholder", "cross-functional", "stakeholder management", "KPI", "SLA",
               "root cause", "incident", "incident management", "postmortem", "RCA",
               "SOP", "runbook", "escalation", "on-call", "oncall", "production",
    "sre", "site reliability", "MTTR", "MTBF", "MTTD", "post-mortem"],
    "business": ["revenue", "growth", "strategy", "analytics", "metrics", "dashboard",
               "OKR", "KPI", "stakeholder", "cross-functional", "alignment", "roadmap",
               "prioritization", "resource", "capacity", "forecast", "budget"],
    "technical": ["API", "database", "SQL", "Python", "automation", "CI/CD", "DevOps",
                 "monitoring", "alerting", "dashboard", "Slack", "Jira", "Confluence",
                 "Grafana", "Datadog", "PagerDuty", "Terraform", "Kubernetes", "AWS"],
    "leadership": ["lead", "lead", "manage", "mentor", "coached", "trained", "built",
                  "grew", "scaled", "process improvement", "change management", "training",
                  "documentation", "playbook", "runbook"],
    "tools": ["Jira", "Confluence", "Slack", "Google Sheets", "Excel", "Notion",
             "Asana", "Monday", "Linear", "Grafana", "Datadog", "PagerDuty",
             "New Relic", "Sentry", "Terraform", "Kubernetes", "Docker", "AWS", "GCP",
             "Azure"]
}

def read_resume_text(path: str) -> str:
    """Extract text from resume (supports MD and TXT)."""
    p = Path(path)
    if not p.exists():
        # Try looking in resumes/ directory
        p = BASE_DIR / "resumes" / path
    if not p.exists():
        # Try Downloads
        p = Path.home() / "Downloads" / path
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    return ""

def read_job_text(path_or_url: str) -> str:
    """Read job description from file or fetch from URL."""
    p = Path(path_or_url)
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore")
    
    # Try fetching from URL
    try:
        from web_scraper import extract_job_details
        result = extract_job_details(path_or_url)
        return result.get("description", "") + " " + result.get("requirements", "")
    except Exception as e:
        print(f"Could not fetch URL: {e}")
        return ""

def tokenize(text: str) -> list:
    """Tokenize text into keywords."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    # Remove stop words but keep acronyms and numbers
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]

def extract_bigrams(text: str) -> list:
    """Extract 2-word phrases."""
    words = tokenize(text)
    bigrams = []
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        bigrams.append(bigram)
    return bigrams

def calculate_score(resume_text: str, job_text: str) -> dict:
    """Calculate ATS compatibility score."""
    resume_tokens = Counter(tokenize(resume_text))
    job_tokens = Counter(tokenize(job_text))
    
    # Extract key requirements from job
    job_bigrams = extract_bigrams(job_text)
    job_bigram_set = set(w for w in job_bigrams if len(w) > 5)
    resume_bigrams = extract_bigrams(resume_text)
    resume_bigram_set = set(resume_bigrams)
    
    # Calculate scores
    job_keywords = set(job_tokens.keys())
    resume_keywords = set(resume_tokens.keys())
    
    # Keyword match rate
    matched = job_keywords.intersection(resume_keywords)
    keyword_score = (len(matched) / len(job_keywords) * 100) if job_keywords else 0
    
    # Bigram match (multi-word phrases)
    matched_bigrams = job_bigram_set.intersection(resume_bigram_set)
    bigram_score = (len(matched_bigrams) / len(job_bigram_set) * 100) if job_bigram_set else 0
    
    # Category-based matching
    category_scores = {}
    for category, keywords in OPS_KEYWORDS.items():
        job_has = sum(1 for k in keywords if k in job_tokens)
        resume_has = sum(1 for k in keywords if k in resume_tokens)
        if job_has > 0:
            category_scores[category] = min(resume_has / job_has * 100, 100)
    
    # Length check (ATS prefers 1-2 pages)
    word_count = len(resume_tokens)
    length_score = 100 if 400 <= word_count <= 1000 else max(0, 100 - abs(word_count - 700) * 0.5)
    
    # Formatting checks
    has_numbers = 1 if re.search(r'\d', resume_text) else 0
    has_dates = 1 if re.search(r'\d{4}', resume_text) else 0
    has_metrics = 1 if re.search(r'\d+%|\d+%', resume_text) else 0
    has_action_verbs = 1 if re.search(r'(led|managed|built|designed|created|improved|increased|reduced|optimized|automated)', resume_text, re.I) else 0
    
    formatting_score = ((has_numbers + has_dates + has_metrics + has_action_verbs) / 4) * 100
    
    # Overall score (weighted)
    overall = (
        keyword_score * 0.35 +
        bigram_score * 0.25 +
        (sum(category_scores.values()) / len(category_scores) if category_scores else 0) * 0.25 +
        formatting_score * 0.15 +
        length_score * 0.05
    )
    
    # Missing keywords
    missing = job_keywords - resume_keywords
    missing = [k for k in missing if len(k) > 3 and k not in STOP_WORDS]
    
    # Suggestions
    suggestions = []
    if keyword_score < 60:
        suggestions.append("Add more job-specific keywords from the posting")
    if bigram_score < 50:
        suggestions.append("Include multi-word phrases from the job description")
    if has_metrics == 0:
        suggestions.append("Add quantifiable metrics (%, $, numbers)")
    if has_action_verbs == 0:
        suggestions.append("Use strong action verbs (led, built, improved, automated)")
    if word_count < 400:
        suggestions.append("Resume may be too short (aim for 400-1000 words)")
    elif word_count > 1000:
        suggestions.append("Resume may be too long for ATS (aim for 400-1000 words)")
    
    # Category weaknesses
    for cat, score in category_scores.items():
        if score < 50:
            missing_cat = [k for k in OPS_KEYWORDS[cat] if k in job_tokens and k not in resume_tokens]
            if missing_cat:
                suggestions.append(f"Weak in {cat}: add {', '.join(missing_cat[:3])}")
    
    return {
        "overall_score": round(overall, 1),
        "keyword_score": round(keyword_score, 1),
        "bigram_score": round(bigram_score, 1),
        "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
        "formatting_score": round(formatting_score, 1),
        "length_score": round(length_score, 1),
        "word_count": word_count,
        "matched_keywords": list(matched)[:20],
        "missing_keywords": sorted(missing, key=lambda x: job_tokens.get(x, 0), reverse=True)[:15],
        "suggestions": suggestions,
        "rating": "🟢 Excellent" if overall >= 80 else "🟡 Good" if overall >= 60 else "🔴 Needs Work"
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ATS Resume Checker")
    parser.add_argument("resume", help="Path to resume file or job description")
    parser.add_argument("job", nargs="?", help="Path to job description or URL")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    
    args = parser.parse_args()
    
    resume_text = read_resume_text(args.resume)
    job_text = read_job_text(args.job)
    
    if not resume_text or not job_text:
        print("❌ Could not read resume or job description. Check file paths.")
        sys.exit(1)
    
    result = calculate_score(resume_text, job_text)
    
    if args.format == "json":
        import json
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  ATS Resume Score: {result['rating']} ({result['overall_score']}%)")
        print(f"{'='*60}")
        print(f"\n📊 Breakdown:")
        print(f"  Keyword Match:    {result['keyword_score']}%")
        print(f"  Phrase Match:     {result['bigram_score']}%")
        print(f"  Formatting:       {result['formatting_score']}%")
        print(f"  Length Score:     {result['length_score']}%")
        
        if result['category_scores']:
            print(f"\n📂 Category Scores:")
            for cat, score in result['category_scores'].items():
                bar = "█" * int(score // 5) + "░" * (20 - int(score // 5))
                print(f"  {cat:.<15} {bar} {score}%")
        
        if result['missing_keywords']:
            print(f"\n⚠️  Missing Keywords ({len(result['missing_keywords'])}):")
            print(f"  {', '.join(result['missing_keywords'][:10])}")
        
        if result['suggestions']:
            print(f"\n💡 Suggestions:")
            for s in result['suggestions']:
                print(f"  • {s}")
        
        print(f"\n📝 Word count: {result['word_count']}")
        print()

if __name__ == "__main__":
    main()