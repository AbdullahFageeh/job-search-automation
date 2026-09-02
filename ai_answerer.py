#!/usr/bin/env python3
"""
AI Application Question Answerer
=================================
Generates intelligent answers for job application form questions using LLM.

Features:
  - Answers text questions based on your profile + job description
  - Answers numeric questions (years of experience, salary, etc.)
  - Chooses from dropdown/radio options
  - Generates cover letters tailored to each job
  - Scores job suitability before applying
  - Caches answers to avoid redundant LLM calls

Usage:
    # Standalone
    python3 ai_answerer.py answer "Tell me about your leadership experience"
    python3 ai_answerer.py numeric "How many years of experience with Python?"
    python3 ai_answerer.py choose "What's your preferred work style?" "Remote, Hybrid, On-site"
    python3 ai_answerer.py suitability --job logs/entry_level_jobs.json --index 0
    python3 ai_answerer.py cover_letter --job logs/entry_level_jobs.json --index 0

    # As module (imported by auto_apply.py)
    from ai_answerer import AIAnswerer
    answerer = AIAnswerer("sk-proj-...")  # OpenAI API key
    answer = answerer.answer_text("Tell me about yourself")
"""

import json
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

import yaml
from openai import OpenAI

# Try Anthropic as fallback
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
ANSWERS_CACHE = BASE_DIR / "answers.json"
PROFILE_FILE = BASE_DIR / "profile.yaml"

# Lightweight, cheap model for answering questions
DEFAULT_MODEL = "gpt-4o-mini"


class AIAnswerer:
    """AI-powered application question answerer."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        Initialize the AI answerer.

        Args:
            api_key: OpenAI or Anthropic API key (falls back to env vars)
            provider: "openai" or "anthropic"
        """
        self.provider = provider
        self.profile = self._load_profile()
        self.resume_text = self._load_resume_text()
        self.answers_cache = self._load_cache()

        if provider == "openai":
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        elif provider == "anthropic" and HAS_ANTHROPIC:
            self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        else:
            raise ValueError(f"Provider '{provider}' not supported or not installed")

        self.current_job_description = ""
        self.current_company = ""

    # ─── Initialization ───────────────────────────────────────────────────

    @staticmethod
    def _load_profile():
        """Load structured profile from YAML."""
        if PROFILE_FILE.exists():
            with open(PROFILE_FILE) as f:
                return yaml.safe_load(f)
        print("⚠️  profile.yaml not found. Create one for better answers.")
        return {}

    def _load_resume_text(self):
        """Load default resume as plain text for context."""
        resume_path = BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Ladders_BizOps.md"
        if resume_path.exists():
            return resume_path.read_text()
        return ""

    @staticmethod
    def _load_cache():
        """Load cached answers from JSON."""
        if ANSWERS_CACHE.exists():
            try:
                with open(ANSWERS_CACHE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    @staticmethod
    def _save_cache(cache):
        """Save answers cache to JSON."""
        with open(ANSWERS_CACHE, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)

    def set_job(self, company: str, description: str):
        """Set the current job context for answer generation."""
        self.current_company = company
        self.current_job_description = description

    # ─── Caching ──────────────────────────────────────────────────────────

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for cache lookup."""
        return re.sub(r'\s+', ' ', text.lower().strip()).replace('"', '').replace('\\', '')

    def _find_cached(self, question: str, q_type: str) -> Optional[str]:
        """Look for a cached answer (fuzzy match on normalized text)."""
        norm = self._normalize(question)
        for entry in self.answers_cache:
            if self._normalize(entry["question"]) == norm and entry.get("type") == q_type:
                return entry["answer"]
        return None

    def _cache_answer(self, question: str, answer: str, q_type: str):
        """Cache an answer for future reuse."""
        # Don't cache company-specific answers
        if self.current_company and self.current_company.lower() in answer.lower():
            return

        norm_q = self._normalize(question)
        # Update existing or append
        for entry in self.answers_cache:
            if self._normalize(entry["question"]) == norm_q and entry.get("type") == q_type:
                entry["answer"] = answer
                entry["updated"] = datetime.now().isoformat()
                self._save_cache(self.answers_cache)
                return

        self.answers_cache.append({
            "question": question,
            "normalized": norm_q,
            "answer": answer,
            "type": q_type,
            "cached_at": datetime.now().isoformat()
        })
        self._save_cache(self.answers_cache)

    # ─── LLM Calls ────────────────────────────────────────────────────────

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM with given prompts."""
        try:
            if self.provider == "openai":
                resp = self.client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
                return resp.choices[0].message.content.strip()
            else:  # Anthropic
                resp = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.3,
                    max_tokens=500,
                )
                return resp.content[0].text.strip()
        except Exception as e:
            print(f"  ⚠️  LLM error: {e}")
            return ""

    # ─── Core Answering Methods ───────────────────────────────────────────

    def answer_text(self, question: str) -> str:
        """
        Answer a free-text application question.

        Routes to the appropriate prompt template based on the question type.
        Checks cache first.
        """
        cached = self._find_cached(question, "text")
        if cached:
            print(f"  📋 Cached: {question[:60]}...")
            return cached

        # Determine which prompt template to use
        q_lower = question.lower()

        if "cover letter" in q_lower or "why do you want" in q_lower or "why should we" in q_lower:
            answer = self._answer_cover_letter(question)
        elif "salary" in q_lower or "compensation" in q_lower or "expectation" in q_lower:
            answer = self._answer_salary(question)
        elif "years" in q_lower or "how long" in q_lower or "experience" in q_lower:
            answer = self._answer_numeric(question)
        else:
            answer = self._answer_general(question)

        self._cache_answer(question, answer, "text")
        return answer

    def answer_numeric(self, question: str) -> str:
        """Answer a numeric question (years of experience, salary number, etc.)."""
        cached = self._find_cached(question, "numeric")
        if cached:
            return cached

        system_prompt = """You help a job applicant answer numeric questions for job applications.
Answer with ONLY a number. No explanation, no units, no text. Just the number.
If the question asks for years, give a reasonable number based on the resume."""

        user_prompt = f"""My resume:
{self.resume_text}

Profile summary: {self.profile.get('experience_details', {}).get('summary', '')}

Question: {question}

Answer with only a number:"""

        answer = self._call_llm(system_prompt, user_prompt)
        # Extract number from response
        match = re.search(r'\d+', answer)
        if match:
            num = match.group()
            self._cache_answer(question, num, "numeric")
            return num
        return "3"  # Fallback

    def answer_choice(self, question: str, options: list[str]) -> str:
        """
        Choose the best option from a list for a given question.

        Args:
            question: The question being asked
            options: List of possible answers

        Returns:
            The best matching option (exact string from the list)
        """
        cached = self._find_cached(question, "choice")
        if cached:
            # Verify cached answer is still a valid option
            if cached in options:
                return cached

        system_prompt = f"""You help a job applicant choose the best answer from a list of options.
You MUST return exactly one of the provided options. Do not modify, paraphrase, or create new options.
Consider the applicant's profile and pick the most accurate, favorable option."""

        profile_summary = json.dumps(self.profile, indent=2)
        user_prompt = f"""My profile:
{profile_summary}

Job description (if available):
{self.current_job_description[:1000] if self.current_job_description else "Not provided"}

Question: {question}

Available options (return EXACTLY one of these):
{chr(10).join(f'- "{o}"' for o in options)}

Your choice (return only the exact text of one option, nothing else):"""

        answer = self._call_llm(system_prompt, user_prompt)

        # Find best match among options
        answer_clean = answer.strip().strip('"').strip()

        # Exact match first
        if answer_clean in options:
            self._cache_answer(question, answer_clean, "choice")
            return answer_clean

        # Case-insensitive match
        for opt in options:
            if answer_clean.lower() == opt.lower():
                self._cache_answer(question, opt, "choice")
                return opt

        # Fuzzy match — find closest option
        best = min(options, key=lambda o: self._levenshtein(answer_clean.lower(), o.lower()))
        self._cache_answer(question, best, "choice")
        return best

    def generate_cover_letter(self) -> str:
        """Generate a tailored cover letter for the current job."""
        system_prompt = """You are a professional cover letter writer. Write a concise, compelling cover letter
that connects the applicant's experience directly to the job requirements. Maximum 3 paragraphs.
No greeting, no sign-off — just the body of the letter. Be specific, use numbers and metrics from the resume.
Write naturally, not robotic. Avoid buzzwords like "passionate" and "thrilled"."""

        user_prompt = f"""Company: {self.current_company}

Job Description:
{self.current_job_description[:2000] if self.current_job_description else "Not available"}

My Resume:
{self.resume_text}

Write a cover letter (max 3 paragraphs, no greeting, no sign-off):"""

        return self._call_llm(system_prompt, user_prompt)

    def score_suitability(self, job_description: str, min_score: int = 5) -> tuple[bool, int, str]:
        """
        Score whether a job is suitable for the applicant.

        Returns:
            (is_suitable, score 1-10, reasoning)
        """
        system_prompt = """You are an HR expert evaluating whether a candidate is suitable for a job.
Analyze the match between the resume and job description. Consider:
- Hard requirements (experience level, skills, education)
- Soft requirements (culture fit, work style)
- Remote vs on-site compatibility (candidate prefers remote)
- Career stage (candidate is entry-level / early-career)

Score 1-10 where 1=not suitable, 10=perfect match.
Be strict about experience level mismatches — if the job requires senior/10+ years, score low."""

        profile_summary = json.dumps(self.profile, indent=2)
        user_prompt = f"""Job Description:
{job_description[:3000]}

Candidate Profile:
{profile_summary}

Candidate Resume:
{self.resume_text[:2000]}

Respond in this exact format:
Score: [1-10]
Reasoning: [2-3 sentences]"""

        response = self._call_llm(system_prompt, user_prompt)

        # Parse score
        score_match = re.search(r'Score:\s*(\d+)', response)
        reasoning_match = re.search(r'Reasoning:\s*(.+)', response, re.DOTALL)

        score = int(score_match.group(1)) if score_match else 5
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"

        return (score >= min_score, score, reasoning)

    # ─── Specialized Answerers ────────────────────────────────────────────

    def _answer_general(self, question: str) -> str:
        """Answer a general text question."""
        system_prompt = """You are helping a job applicant fill out an application form.
Answer the question directly and concisely based on the provided resume and profile.
Keep answers under 140 characters unless the question clearly requires more detail.
Be honest, confident, and professional. If you don't know, say "I'm willing to learn" rather than lying."""

        profile_summary = json.dumps(self.profile, indent=2)
        user_prompt = f"""My resume:
{self.resume_text[:1500]}

My profile data:
{profile_summary}

Job I'm applying to: {self.current_company or "Unknown company"}
{f"Job description: {self.current_job_description[:800]}" if self.current_job_description else ""}

Question: {question}

Answer:"""

        return self._call_llm(system_prompt, user_prompt)

    def _answer_cover_letter(self, question: str) -> str:
        """Answer a cover letter or "why this company" question."""
        return self.generate_cover_letter()

    def _answer_salary(self, question: str) -> str:
        """Answer salary expectation questions."""
        system_prompt = """Answer salary questions based on the profile. Return just the number or range, no currency symbol unless specified."""

        salary_info = self.profile.get('salary_expectations', {})
        user_prompt = f"""Profile salary info: {json.dumps(salary_info)}

Question: {question}

Answer (just the number/range):"""

        return self._call_llm(system_prompt, user_prompt)

    # ─── Utilities ────────────────────────────────────────────────────────

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        """Simple Levenshtein distance for fuzzy matching."""
        if len(s1) < len(s2):
            return AIAnswerer._levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)
        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row
        return prev_row[-1]


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Application Question Answerer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # answer command
    p_answer = subparsers.add_parser("answer", help="Answer a text question")
    p_answer.add_argument("question", type=str)

    # numeric command
    p_numeric = subparsers.add_parser("numeric", help="Answer a numeric question")
    p_numeric.add_argument("question", type=str)

    # choose command
    p_choose = subparsers.add_parser("choose", help="Choose from options")
    p_choose.add_argument("question", type=str)
    p_choose.add_argument("options", nargs="+")

    # suitability command
    p_suit = subparsers.add_parser("suitability", help="Score job suitability")
    p_suit.add_argument("--job", default="logs/entry_level_jobs.json")
    p_suit.add_argument("--index", type=int, default=0)

    # cover_letter command
    p_cl = subparsers.add_parser("cover_letter", help="Generate cover letter")
    p_cl.add_argument("--job", default="logs/entry_level_jobs.json")
    p_cl.add_argument("--index", type=int, default=0)

    # cache command
    p_cache = subparsers.add_parser("cache", help="Manage answer cache")
    p_cache.add_argument("action", choices=["show", "clear", "count"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Load API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set. Add to .env file.")
        sys.exit(1)

    answerer = AIAnswerer(api_key)

    if args.command == "answer":
        print(f"\nQ: {args.question}")
        print(f"A: {answerer.answer_text(args.question)}")

    elif args.command == "numeric":
        print(f"\nQ: {args.question}")
        print(f"A: {answerer.answer_numeric(args.question)}")

    elif args.command == "choose":
        print(f"\nQ: {args.question}")
        print(f"Options: {args.options}")
        print(f"A: {answerer.answer_choice(args.question, args.options)}")

    elif args.command == "suitability":
        jobs_file = Path(args.job)
        if jobs_file.exists():
            with open(jobs_file) as f:
                jobs = json.load(f)
            if args.index < len(jobs):
                job = jobs[args.index]
                desc = job.get("description", "")
                company = job.get("company", "Unknown")
                answerer.set_job(company, desc)
                suitable, score, reasoning = answerer.score_suitability(desc)
                print(f"\n📋 {job.get('title', '')} at {company}")
                print(f"   Score: {score}/10 {'✅' if suitable else '❌'}")
                print(f"   Reasoning: {reasoning}")

    elif args.command == "cover_letter":
        jobs_file = Path(args.job)
        if jobs_file.exists():
            with open(jobs_file) as f:
                jobs = json.load(f)
            if args.index < len(jobs):
                job = jobs[args.index]
                answerer.set_job(job.get("company", ""), job.get("description", ""))
                print(f"\n📝 Cover Letter for {job.get('title', '')} at {job.get('company', '')}:")
                print("=" * 50)
                print(answerer.generate_cover_letter())

    elif args.command == "cache":
        if args.action == "show":
            for a in answerer.answers_cache[:20]:
                print(f"  {a['type']:6} | {a['question'][:60]:60} → {a['answer'][:40]}")
        elif args.action == "clear":
            answerer.answers_cache = []
            answerer._save_cache([])
            print("  Cache cleared")
        elif args.action == "count":
            print(f"  Cached answers: {len(answerer.answers_cache)}")


if __name__ == "__main__":
    main()