#!/usr/bin/env python3
"""
Resume Matcher — Calculates match percentage between your resume and job descriptions
using lightweight TF-IDF cosine similarity. No heavy ML dependencies required.
"""

import re
import math
from collections import Counter
import string
from pathlib import Path

BASE_DIR = Path(__file__).parent
RESUME_DIR = BASE_DIR / "resumes"

def preprocess(text: str) -> list:
    """Clean and tokenize text for matching."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'are', 'was', 'were', 'be', 'to', 'of', 'in', 'on', 'at', 'from', 'by', 'a', 'an', 'is', 'it', 'we', 'you', 'they', 'have', 'has', 'had', 'will', 'can', 'could', 'would', 'should'}
    return [w for w in text.split() if len(w) > 2 and w not in stopwords and w not in string.punctuation]

def cosine_similarity(vec1: dict, vec2: dict) -> float:
    """Calculate cosine similarity between two term frequency vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    if not intersection:
        return 0.0
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    sum1 = math.sqrt(sum(v**2 for v in vec1.values()))
    sum2 = math.sqrt(sum(v**2 for v in vec2.values()))
    return numerator / (sum1 * sum2) if (sum1 * sum2) > 0 else 0.0

def load_resume(resume_path: str) -> str:
    """Load resume text (supports .md and .txt)."""
    path = Path(resume_path)
    if not path.exists():
        # Try resumes directory
        path = RESUME_DIR / resume_path
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {resume_path}")
    return path.read_text(encoding="utf-8", errors="ignore")

def score_resume(resume_path: str, job_text: str) -> dict:
    """Score resume against job description. Returns match % and key missing skills."""
    resume_text = load_resume(resume_path)
    
    resume_vec = Counter(preprocess(resume_text))
    job_vec = Counter(preprocess(job_text))
    
    score = cosine_similarity(resume_vec, job_vec) * 100
    
    # Find top missing keywords from job that aren't in resume
    job_terms = set(job_vec.keys())
    resume_terms = set(resume_vec.keys())
    missing = sorted([t for t in job_terms if t not in resume_terms], key=lambda x: job_vec[x], reverse=True)[:5]
    
    return {
        "match_percentage": round(score, 1),
        "rating": "🟢 Excellent" if score >= 75 else "🟡 Good" if score >= 50 else "🔴 Low",
        "missing_keywords": missing,
        "resume_used": str(resume_path)
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 resume_matcher.py <resume_file.md> <job_description.txt>")
        sys.exit(1)
    
    result = score_resume(sys.argv[1], open(sys.argv[2]).read())
    print(f"\n📊 Match Score: {result['match_percentage']}% ({result['rating']})")
    if result['missing_keywords']:
        print(f"🔑 Missing keywords: {', '.join(result['missing_keywords'])}")
    print(f"📄 Resume used: {result['resume_used']}")