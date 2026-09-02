#!/usr/bin/env python3
"""
GitHub Resource Finder — Discover repos for ops tools, templates, runbooks,
interview prep, and career resources.
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
RESOURCES_FILE = BASE_DIR / "logs" / "github_resources.json"

# Search queries that surface ops-career resources
SEARCH_QUERIES = [
    "operations runbook template",
    "business operations playbook",
    "incident management runbook",
    "postmortem template",
    "sre handbook",
    "ops dashboard template",
    "career change operations",
    "interview questions operations",
    "resume template operations",
    "ops metrics dashboard",
    "ITIL operations",
    "service level objective template",
    "on-call playbook",
    "business continuity plan",
    "operations checklist",
    "program manager resources",
    "technical program management",
    "customer success operations",
]

MIN_STARS = 20  # Only show repos with 20+ stars

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_resources() -> list:
    if RESOURCES_FILE.exists():
        with open(RESOURCES_FILE) as f:
            return json.load(f)
    return []


def save_resources(resources: list):
    with open(RESOURCES_FILE, "w") as f:
        json.dump(resources, f, indent=2)


def search_github(query: str) -> list:
    """Search GitHub for relevant repos using the search API."""
    import httpx
    
    url = f"https://api.github.com/search/repositories"
    params = {"q": f"{query} stars:>{MIN_STARS}", "sort": "stars", "order": "desc", "per_page": 5}
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "JobSearchBot/1.0"}
    
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            results = []
            for item in data.get("items", []):
                results.append({
                    "name": item["full_name"],
                    "title": item["name"],
                    "description": item.get("description", "") or "No description",
                    "stars": item["stargazers_count"],
                    "language": item.get("language", ""),
                    "url": item["html_url"],
                    "topics": item.get("topics", []),
                    "updated": item.get("updated_at", "")[:10],
                    "search_query": query,
                })
            return results
    except Exception as e:
        logger.warning(f"Search '{query}' failed: {e}")
        return []


def scan_all() -> list:
    """Run all searches and deduplicate."""
    all_repos = []
    seen_names = set()
    
    for query in SEARCH_QUERIES:
        print(f"  Searching: \"{query}\"...")
        results = search_github(query)
        for repo in results:
            if repo["name"] not in seen_names:
                seen_names.add(repo["name"])
                all_repos.append(repo)
        time.sleep(1.5)  # Rate limit: ~3 req/sec unauthed
    
    return all_repos


def format_category(repo) -> str:
    """Categorize a repo."""
    name = (repo.get("name", "") + " " + repo.get("description", "")).lower()
    query = repo.get("search_query", "").lower()
    
    if any(w in name for w in ["runbook", "playbook", "run book"]):
        return "📋 Runbooks & Playbooks"
    if any(w in name for w in ["template", "template"]):
        return "📝 Templates"
    if any(w in name for w in ["interview", "career", "resume"]):
        return "🎯 Career & Interview"
    if any(w in name for w in ["dashboard", "metrics", "monitor"]):
        return "📊 Dashboards & Metrics"
    if any(w in name for w in ["sre", "reliability", "incident"]):
        return "🔧 SRE & Reliability"
    if any(w in name for w in ["automation", "script", "tool"]):
        return "🤖 Automation & Tools"
    return "📦 Other Resources"


def main():
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description="GitHub Resource Finder")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("scan", help="Scan GitHub for ops resources")
    sub.add_parser("browse", help="Browse saved resources")
    sub.add_parser("category", help="Browse by category")
    sub.add_parser("search", help="Search for a specific topic")
    sub.add_parser("stats", help="Show stats")
    
    args = parser.parse_args()
    
    if args.action == "scan":
        print(f"\n🔍 Searching GitHub for ops resources...")
        new_repos = scan_all()
        
        existing = load_resources()
        existing_names = {r.get("name") for r in existing}
        
        added = []
        for repo in new_repos:
            if repo["name"] not in existing_names:
                existing.append(repo)
                added.append(repo)
        
        save_resources(existing)
        
        if added:
            print(f"\n✅ Found {len(added)} new resources (total: {len(existing)})\n")
            for repo in added[:20]:
                cat = format_category(repo)
                print(f"  {cat}")
                print(f"  ⭐ {repo['stars']} | {repo['name']}")
                print(f"  {repo['description'][:100]}")
                print(f"  {repo['url']}")
                print()
        else:
            print("\n  No new resources found.")
    
    elif args.action == "browse":
        resources = load_resources()
        if not resources:
            print("No resources yet. Run: python3 github_resources.py scan")
            return
        
        print(f"\n📚 GitHub Resources ({len(resources)} total)\n")
        for repo in resources[:30]:
            cat = format_category(repo)
            print(f"  {cat}")
            print(f"  ⭐ {repo['stars']} | {repo['name']}")
            print(f"  {repo['description'][:100]}")
            if repo.get("language"):
                print(f"  Language: {repo['language']}")
            print(f"  {repo['url']}")
            print()
    
    elif args.action == "category":
        resources = load_resources()
        if not resources:
            print("No resources yet. Run: python3 github_resources.py scan")
            return
        
        categories = {}
        for repo in resources:
            cat = format_category(repo)
            categories.setdefault(cat, []).append(repo)
        
        print(f"\n📚 Resources by Category\n")
        for cat, repos in sorted(categories.items()):
            print(f"\n  {cat} ({len(repos)} repos)")
            print(f"  {'─'*40}")
            for repo in sorted(repos, key=lambda x: x.get("stars", 0), reverse=True)[:5]:
                print(f"    ⭐ {repo['stars']:>5} | {repo['name']}")
                print(f"           {repo['description'][:80]}")
                print(f"           {repo['url']}")
        print()
    
    elif args.action == "search":
        topic = input("  Search topic: ").strip()
        if not topic:
            return
        
        results = search_github(topic)
        if results:
            print(f"\n🔍 Results for \"{topic}\"\n")
            for repo in results:
                cat = format_category(repo)
                print(f"  {cat}")
                print(f"  ⭐ {repo['stars']} | {repo['name']}")
                print(f"  {repo['description'][:100]}")
                print(f"  {repo['url']}")
                print()
        else:
            print("\n  No results found.")
    
    elif args.action == "stats":
        resources = load_resources()
        print(f"\n📊 GitHub Resources Stats")
        print(f"   Total resources: {len(resources)}")
        
        if resources:
            lang_count = {}
            for r in resources:
                lang = r.get("language", "Unknown")
                lang_count[lang] = lang_count.get(lang, 0) + 1
            
            if lang_count:
                print(f"\n   By Language:")
                for lang, count in sorted(lang_count.items(), key=lambda x: x[1], reverse=True):
                    print(f"     {lang}: {count}")
            
            avg_stars = sum(r.get("stars", 0) for r in resources) / len(resources)
            print(f"\n   Avg stars: {avg_stars:.0f}")
        print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()