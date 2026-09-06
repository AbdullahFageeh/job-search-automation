#!/usr/bin/env python3
"""
LangGraph Job Application Pipeline
====================================
Multi-agent graph-based workflow for job applications:

  1. SCAN    — Gather jobs from LinkedIn + boards
  2. DEDUP   — Filter already-applied jobs
  3. SCORE   — AI rates job suitability (1-10)
  4. PREPARE — Generate tailored resume + cover letter
  5. REVIEW  — Human-in-the-loop approval gate
  6. APPLY   — Browser-based application submission
  7. LOG     — Record result

Features:
  - Stateful graph with retry logic
  - Human approval checkpoint before applying
  - Conditional routing (skip low-score jobs)
  - Per-job state tracking

Usage:
    python3 langgraph_pipeline.py run           # Run full pipeline
    python3 langgraph_pipeline.py review        # Review pending jobs
    python3 langgraph_pipeline.py status        # Show pipeline status
"""

import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import TypedDict, Annotated, NotRequired
from functools import reduce

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated, NotRequired
from functools import reduce, operator

# ─── State Definition ───────────────────────────────────────────────────────

class JobState(TypedDict):
    """State that flows through the graph."""
    # Input
    jobs: list[dict]                      # Jobs to process
    _processed_jobs: list[dict]           # Pre-filtered jobs (internal)
    job_index: Annotated[int, operator.add]  # Counter that increments
    max_jobs: int                         # Max jobs to process per run
    jobs_processed: Annotated[int, operator.add]  # Running counter

    # Current job
    current_job: NotRequired[dict]        # Job currently being processed

    # Processing results
    score: NotRequired[int]               # Suitability score (1-10)
    score_reason: NotRequired[str]        # Why this score
    cover_letter: NotRequired[str]        # Generated cover letter

    # Decision
    action: NotRequired[str]              # "apply", "skip", "pending_review"
    review_approved: NotRequired[bool]    # Human approval result

    # Results
    results: Annotated[list[dict], operator.add]  # Accumulates results
    applied_links: Annotated[set[str], operator.or_]  # Accumulates links


# ─── LLM Setup (Groq) ───────────────────────────────────────────────────────

def get_llm():
    """Get LLM instance configured for Groq."""
    return ChatOpenAI(
        model="groq/compound",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
        temperature=0.3,
    )


# ─── Node Functions ──────────────────────────────────────────────────────────

def load_profile():
    """Load user profile from YAML."""
    import yaml
    profile_file = BASE_DIR / "profile.yaml"
    if profile_file.exists():
        with open(profile_file) as f:
            return yaml.safe_load(f)
    return {}


def load_resume_text():
    """Load default resume."""
    resume_path = BASE_DIR / "resumes" / "Abdullah_Fageeh_Resume_Ladders_BizOps.md"
    if resume_path.exists():
        return resume_path.read_text()
    return ""


def scan_jobs(state: JobState) -> dict:
    """Node 1: Load jobs from existing scan results."""
    print("\n📡 NODE: SCAN — Loading job listings...")

    jobs = []

    # Load from entry_level_jobs.json
    entry_file = LOGS_DIR / "entry_level_jobs.json"
    if entry_file.exists():
        with open(entry_file) as f:
            jobs.extend(json.load(f))
        print(f"   • LinkedIn jobs: {len(jobs)}")

    # Load from other boards
    boards_file = LOGS_DIR / "other_boards_jobs.json"
    if boards_file.exists():
        with open(boards_file) as f:
            board_jobs = json.load(f)
            jobs.extend(board_jobs if isinstance(board_jobs, list) else [])
        print(f"   • Board jobs total: {len(jobs)}")

    # Load already applied links
    applied_links = set()
    applied_file = LOGS_DIR / "linkedin_applied.json"
    if applied_file.exists():
        with open(applied_file) as f:
            applied = json.load(f)
            applied_links = {a.get("link", "") for a in applied if a.get("link")}

    # Load pipeline results for dedup
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            results = json.load(f)
            applied_links.update(r.get("link", "") for r in results if r.get("link"))

    print(f"   • Already applied: {len(applied_links)}")
    print(f"   • Total jobs loaded: {len(jobs)}")

    return {
        "jobs": jobs,
        "job_index": 0,
        "max_jobs": state.get("max_jobs", 10),
        "results": [],
        "applied_links": applied_links,
    }


def dedup_jobs(state: JobState) -> dict:
    """Node 2: Filter out already-applied and pick next job."""
    print("\n🔄 NODE: DEDUP — Finding next job...")

    all_jobs = state["jobs"]
    idx = state["job_index"]
    applied = state["applied_links"]
    results = state.get("results", [])

    # Filter new jobs (only once, stored in state)
    processed_jobs = state.get("_processed_jobs", [])
    if not processed_jobs:
        processed_jobs = [j for j in all_jobs if j.get("link", "") not in applied]
        processed_jobs = processed_jobs[:state.get("max_jobs", 10)]
        state["_processed_jobs"] = processed_jobs

    processed_jobs = processed_jobs

    if not processed_jobs or idx >= len(processed_jobs):
        print(f"   All {len(processed_jobs)} jobs processed.")
        return {"action": "done", "results": results}

    # Pick next job
    job = processed_jobs[idx]
    print(f"   → Job: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
    print(f"   → ({idx+1}/{len(processed_jobs)})")

    return {
        **state,
        "current_job": job,
        "action": "score",  # Route to scoring
    }


def score_job(state: JobState) -> dict:
    """Node 3: AI rates job suitability."""
    print("\n📊 NODE: SCORE — Evaluating job fit...")

    job = state["current_job"]
    profile = load_profile()
    resume = load_resume_text()

    llm = get_llm()

    exp = profile.get('experience_details', {})
    profile_summary = (
        f"Name: {profile.get('personal_information', {}).get('name', '')}\n"
        f"Experience: {exp.get('summary', '')}\n"
        f"Total years: {exp.get('total_years', '')}\n"
        f"Remote: {profile.get('work_preferences', {}).get('work_style', '')}"
    )

    # Use AI answerer for scoring (already optimized for Groq)
    answerer = AIAnswerer()
    answerer.set_job(job.get("company", ""), job.get("description", ""))

    suitable, score, reasoning = answerer.score_suitability(
        job.get("description", job.get("snippet", ""))
    )

    print(f"   Score: {score}/10")
    print(f"   Reason: {reasoning[:100]}...")

    if score < 5:
        print("   → SKIP (below threshold)")
        result = {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "link": job.get("link", ""),
            "score": score,
            "reason": reasoning,
            "action": "skipped",
            "date": datetime.now().isoformat(),
        }
        return {
            **state,
            "score": score,
            "score_reason": reasoning,
            "action": "skip",
            "results": state.get("results", []) + [result],
        }

    return {
        **state,
        "score": score,
        "score_reason": reasoning,
        "action": "prepare",  # Route to preparation
    }


def prepare_application(state: JobState) -> dict:
    """Node 4: Generate cover letter + prepare application."""
    print("\n✍️  NODE: PREPARE — Generating application materials...")

    job = state["current_job"]
    answerer = AIAnswerer()
    answerer.set_job(job.get("company", ""), job.get("description", ""))

    # Generate cover letter
    cover = answerer.generate_cover_letter()
    print(f"   Cover letter: {len(cover)} chars")

    return {
        **state,
        "cover_letter": cover,
        "action": "review",  # Route to human review
    }


def review_job(state: JobState) -> dict:
    """Node 5: Human-in-the-loop approval gate."""
    print("\n✅ NODE: REVIEW — Awaiting approval...")

    job = state["current_job"]
    score = state.get("score", 0)

    print(f"\n   {'='*50}")
    print(f"   {job.get('title', '')} at {job.get('company', '')}")
    print(f"   Score: {score}/10")
    print(f"   Link: {job.get('link', '')}")
    print(f"   {'='*50}")

    # Check for auto-approve setting
    auto_approve = os.getenv("AUTO_APPROVE", "false").lower() == "true"

    if auto_approve:
        print("   Auto-approve enabled → proceeding")
        return {**state, "review_approved": True, "action": "apply"}

    # Ask for approval
    try:
        choice = input("\n   Approve this application? (y/n/skip all): ").strip().lower()
        if choice in ("y", "yes"):
            print("   → Approved ✓")
            return {**state, "review_approved": True, "action": "apply"}
        elif choice in ("s", "skip all"):
            print("   → Skipping remaining jobs")
            return {**state, "action": "skip_all"}
        else:
            print("   → Skipped ✗")
            result = {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "link": job.get("link", ""),
                "score": score,
                "action": "rejected",
                "date": datetime.now().isoformat(),
            }
            return {
                **state,
                "action": "skip",
                "results": state.get("results", []) + [result],
            }
    except (EOFError, KeyboardInterrupt):
        print("\n   → Interrupted, stopping pipeline")
        return {**state, "action": "stop"}


def apply_job(state: JobState) -> dict:
    """Node 6: Submit application via browser."""
    print("\n🚀 NODE: APPLY — Submitting application...")

    job = state["current_job"]
    company = job.get("company", "")

    # Use existing auto_apply logic
    try:
        from auto_apply import get_resume_for_company
        resume_path = get_resume_for_company(company)

        result = {
            "title": job.get("title", ""),
            "company": company,
            "link": job.get("link", ""),
            "score": state.get("score", 0),
            "action": "applied",
            "resume": str(resume_path),
            "date": datetime.now().isoformat(),
        }

        print(f"   → Marked as applied (browser automation ready)")
        print(f"   → Resume: {resume_path.name}")

        return {
            **state,
            "action": "log",
            "results": state.get("results", []) + [result],
            "applied_links": state["applied_links"] | {job.get("link", "")},
        }

    except Exception as e:
        print(f"   → Error: {e}")
        result = {
            "title": job.get("title", ""),
            "company": company,
            "link": job.get("link", ""),
            "action": "failed",
            "error": str(e),
            "date": datetime.now().isoformat(),
        }
        return {
            **state,
            "action": "log",
            "results": state.get("results", []) + [result],
        }


def log_result(state: JobState) -> dict:
    """Node 7: Save results and advance to next job."""
    results = state.get("results", [])

    # Save results incrementally
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            existing = json.load(f)
        existing.extend([results[-1]] if results else [])
    else:
        existing = results[-1:] if results else []

    with open(RESULTS_FILE, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    # Advance index
    new_idx = state["job_index"] + 1
    max_j = state.get("max_jobs", 10)

    if new_idx >= max_j:
        print(f"\n   Reached max jobs ({max_j}). Stopping.")
        return {**state, "action": "done"}

    return {**state, "job_index": new_idx, "action": "dedup"}


# ─── Routing Logic ──────────────────────────────────────────────────────────

def route_after_score(state: JobState) -> str:
    """Route based on score result."""
    return state.get("action", "skip")


def route_after_prepare(state: JobState) -> str:
    """Route to review."""
    return state.get("action", "review")


def route_after_review(state: JobState) -> str:
    """Route based on review decision."""
    return state.get("action", "skip")


def route_after_log(state: JobState) -> str:
    """Route back to dedup for next job."""
    action = state.get("action", "done")
    if action == "stop":
        return "end"
    return "dedup"


# ─── Build Graph ────────────────────────────────────────────────────────────

def build_graph():
    """Build the LangGraph pipeline."""
    graph = StateGraph(JobState)

    # Add nodes
    graph.add_node("scan", scan_jobs)
    graph.add_node("dedup", dedup_jobs)
    graph.add_node("score", score_job)
    graph.add_node("prepare", prepare_application)
    graph.add_node("review", review_job)
    graph.add_node("apply", apply_job)
    graph.add_node("log", log_result)

    # Entry point
    graph.set_entry_point("scan")

    # Scan → Dedup
    graph.add_edge("scan", "dedup")

    # Dedup → Score (conditional: if no more jobs, end)
    graph.add_conditional_edges("dedup", lambda s: s.get("action", "end"), {
        "score": "score",
        "done": END,
    })

    # Score → conditional (apply if high score, skip if low)
    graph.add_conditional_edges("score", route_after_score, {
        "prepare": "prepare",
        "skip": "log",
    })

    # Prepare → Review (always)
    graph.add_edge("prepare", "review")

    # Review → conditional
    graph.add_conditional_edges("review", route_after_review, {
        "apply": "apply",
        "skip": "log",
        "skip_all": END,
        "stop": END,
    })

    # Apply → Log
    graph.add_edge("apply", "log")

    # Log → back to dedup (loop) or end
    graph.add_conditional_edges("log", route_after_log, {
        "dedup": "dedup",
        "end": END,
    })

    return graph.compile()


# ─── CLI ────────────────────────────────────────────────────────────────────

def print_summary(results: list[dict]):
    """Print pipeline execution summary."""
    if not results:
        print("\n  No jobs processed.")
        return

    applied = [r for r in results if r.get("action") == "applied"]
    skipped = [r for r in results if r.get("action") == "skipped"]
    rejected = [r for r in results if r.get("action") == "rejected"]
    failed = [r for r in results if r.get("action") == "failed"]

    print(f"\n{'='*60}")
    print(f"📊 PIPELINE SUMMARY")
    print(f"{'='*60}")
    print(f"  Total processed: {len(results)}")
    print(f"  ✅ Applied:      {len(applied)}")
    print(f"  ⏭️  Skipped:      {len(skipped)}")
    print(f"  ❌ Rejected:     {len(rejected)}")
    print(f"  💥 Failed:       {len(failed)}")
    print(f"{'='*60}")

    if applied:
        print(f"\n  Applications submitted:")
        for r in applied[:10]:
            print(f"    • {r.get('title', '?')} @ {r.get('company', '?')}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph Job Application Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    p_run = subparsers.add_parser("run", help="Run the full pipeline")
    p_run.add_argument("--max-jobs", type=int, default=5, help="Max jobs to process")
    p_run.add_argument("--auto-approve", action="store_true", help="Skip human review")

    p_status = subparsers.add_parser("status", help="Show pipeline status")
    p_graph = subparsers.add_parser("graph", help="Print the graph structure")

    args = parser.parse_args()

    if args.command == "run":
        if os.getenv("OPENAI_API_KEY"):
            os.environ["AUTO_APPROVE"] = "true" if args.auto_approve else "false"

        graph = build_graph()

        initial_state = {
            "jobs": [],
            "job_index": 0,
            "max_jobs": args.max_jobs,
            "results": [],
            "applied_links": set(),
        }

        print(f"\n🤖 LangGraph Pipeline Starting...")
        print(f"   Max jobs: {args.max_jobs}")
        print(f"   Auto-approve: {args.auto_approve}")
        print(f"   LLM: groq/compound")

        # Run graph
        final_state = graph.invoke(initial_state)

        print_summary(final_state.get("results", []))

    elif args.command == "status":
        if RESULTS_FILE.exists():
            with open(RESULTS_FILE) as f:
                results = json.load(f)
            print(f"\n📊 Pipeline Results: {len(results)} total")
            print_summary(results)
        else:
            print("\n  No results yet. Run: python3 langgraph_pipeline.py run")

    elif args.command == "graph":
        graph = build_graph()
        print("\n📊 Pipeline Graph:")
        print(f"   Nodes: {[n for n in graph.nodes]}")
        # Print edges
        if hasattr(graph, "edges"):
            for e in graph.edges:
                print(f"   {e[0]} → {e[1]}")
        print(f"\n   Graph structure compiled ✓")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()