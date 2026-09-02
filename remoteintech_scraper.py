#!/usr/bin/env python3
"""
Remoteintech Company Directory Scanner
=======================================
Builds a database of 884+ remote-friendly tech companies from:
https://github.com/remoteintech/remote-jobs (40.8k stars)

Features:
  - Clones repo locally for instant parsing (no API rate limits)
  - Parses frontmatter (careers URL, tech stack, size, region, etc.)
  - Builds searchable company database
  - Filters by tech stack, size, region, remote policy
  - Exports to CSV for targeted LinkedIn/company searches

Usage:
    python3 remoteintech_scraper.py sync      # Clone repo + parse all companies
    python3 remoteintech_scraper.py list      # List all companies
    python3 remoteintech_scraper.py search <keyword>  # Search companies
    python3 remoteintech_scraper.py stats     # Show statistics
    python3 remoteintech_scraper.py export    # Export to CSV
    python3 remoteintech_scraper.py careers  # List companies with careers URLs
    python3 remoteintech_scraper.py filter --policy remote --size small  # Filter
"""

import json
import csv
import sys
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

COMPANIES_FILE = LOGS_DIR / "remoteintech_companies.json"
REPO_DIR = Path("/tmp/remoteintech-repo")
COMPANIES_SRC = REPO_DIR / "src" / "companies"


def load_companies():
    if COMPANIES_FILE.exists():
        with open(COMPANIES_FILE) as f:
            return json.load(f)
    return []


def save_companies(companies):
    with open(COMPANIES_FILE, "w") as f:
        json.dump(companies, f, indent=2)


def parse_frontmatter(text):
    """Parse YAML-like frontmatter from markdown file."""
    if not text.startswith("---"):
        return {}

    parts = text.split("---")
    if len(parts) < 2:
        return {}

    fm_text = parts[1].strip()
    frontmatter = {}
    current_key = None
    current_list = None

    for line in fm_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key and current_list is not None:
                current_list.append(stripped[2:].strip().strip('"'))
        elif ":" in stripped:
            # Save previous list if any
            if current_key and current_list is not None:
                frontmatter[current_key] = current_list

            current_key, _, value = stripped.partition(":")
            current_key = current_key.strip().lower()
            value = value.strip().strip('"')

            if value:
                frontmatter[current_key] = value
                current_list = None
            else:
                current_list = []

    # Save last list
    if current_key and current_list is not None:
        frontmatter[current_key] = current_list

    return frontmatter


def parse_company_file(filepath):
    """Parse a single company markdown file."""
    slug = filepath.stem
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    fm = parse_frontmatter(text)

    return {
        "slug": slug,
        "name": fm.get("title", slug.replace("-", " ").title()),
        "website": fm.get("website", ""),
        "careers_url": fm.get("careers_url", ""),
        "remote_policy": fm.get("remote_policy", ""),
        "company_size": fm.get("company_size", ""),
        "region": fm.get("region", ""),
        "technologies": fm.get("technologies", []) if isinstance(fm.get("technologies"), list) else [],
        "hiring_status": fm.get("hiring_status", ""),
        "updated_at": fm.get("updatedat", fm.get("updated_at", "")),
    }


def sync_companies():
    """Clone repo and parse all companies locally."""
    print("🔄 Syncing remoteintech company directory...\n")

    # Clone repo if not present
    if not COMPANIES_SRC.exists():
        print("  ⬇️  Cloning remoteintech/remote-jobs repo...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/remoteintech/remote-jobs.git", str(REPO_DIR)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ❌ Clone failed: {result.stderr}")
            return False
        print("  ✅ Repo cloned\n")

    # Parse all company files
    md_files = sorted(COMPANIES_SRC.glob("*.md"))
    print(f"  📁 Found {len(md_files)} company files\n")

    companies = []
    for i, filepath in enumerate(md_files):
        company = parse_company_file(filepath)
        if company:
            companies.append(company)
        if (i + 1) % 200 == 0:
            print(f"  ⏳ Processed {i+1}/{len(md_files)}...")

    # Sort by name
    companies.sort(key=lambda c: c["name"].lower())

    save_companies(companies)

    print(f"\n  ✅ Synced {len(companies)} companies → {COMPANIES_FILE}")
    return True


def list_companies(limit=50):
    """List companies with basic info."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    print(f"\n  {'Name':<30} {'Policy':<12} {'Size':<10} {'Region':<12}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*12}")

    for c in companies[:limit]:
        print(f"  {c['name']:<30} {c['remote_policy']:<12} {c['company_size']:<10} {c['region']:<12}")

    if len(companies) > limit:
        print(f"\n  ... and {len(companies) - limit} more. Use 'search <keyword>' to find specific ones.")


def search_companies(query):
    """Search companies by name, tech, region, or policy."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    q = query.lower()
    results = [
        c for c in companies
        if q in c["name"].lower()
        or q in c.get("region", "").lower()
        or any(q in t.lower() for t in c.get("technologies", []))
        or q in c.get("remote_policy", "").lower()
        or q in c.get("company_size", "").lower()
    ]

    if not results:
        print(f"  ❌ No companies matching '{query}'")
        return

    print(f"\n  Found {len(results)} companies matching '{query}':\n")
    print(f"  {'Name':<30} {'Policy':<12} {'Size':<10} {'Region':<12} {'Careers URL'}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*12} {'-'*30}")

    for c in results[:50]:
        careers = c.get("careers_url", "")[:50]
        print(f"  {c['name']:<30} {c['remote_policy']:<12} {c['company_size']:<10} {c['region']:<12} {careers}")

    if len(results) > 50:
        print(f"\n  ... and {len(results) - 50} more results.")


def show_stats():
    """Show company database statistics."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    policies = Counter(c.get("remote_policy", "unknown") for c in companies)
    sizes = Counter(c.get("company_size", "unknown") for c in companies)
    regions = Counter(c.get("region", "unknown") for c in companies)
    has_careers = sum(1 for c in companies if c.get("careers_url"))
    has_tech = sum(1 for c in companies if c.get("technologies"))

    # Collect all technologies
    all_techs = []
    for c in companies:
        all_techs.extend(c.get("technologies", []))
    tech_counts = Counter(all_techs).most_common(15)

    print(f"\n  📊 Remoteintech Company Database Stats")
    print(f"  {'='*40}")
    print(f"  Total companies: {len(companies)}")
    print(f"  With careers URLs: {has_careers}")
    print(f"  With tech stacks: {has_tech}")
    print(f"\n  Remote Policy Breakdown:")
    for policy, count in policies.most_common():
        print(f"    {policy:<20} {count}")
    print(f"\n  Company Size Breakdown:")
    for size, count in sizes.most_common():
        print(f"    {size:<20} {count}")
    print(f"\n  Region Breakdown:")
    for region, count in regions.most_common(10):
        print(f"    {region:<20} {count}")
    print(f"\n  Top Technologies:")
    for tech, count in tech_counts:
        print(f"    {tech:<20} {count}")


def export_csv():
    """Export companies to CSV."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    csv_path = LOGS_DIR / "remoteintech_companies.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "name", "slug", "website", "careers_url", "remote_policy",
            "company_size", "region", "technologies", "hiring_status", "updated_at"
        ])
        writer.writeheader()
        for c in companies:
            row = c.copy()
            row["technologies"] = "; ".join(c.get("technologies", []))
            writer.writerow(row)

    print(f"  ✅ Exported {len(companies)} companies → {csv_path}")


def list_careers():
    """List companies with careers URLs."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    with_careers = [c for c in companies if c.get("careers_url")]
    print(f"\n  Companies with careers pages: {len(with_careers)}/{len(companies)}\n")

    for c in with_careers[:100]:
        print(f"  {c['name']:<30} → {c['careers_url']}")

    if len(with_careers) > 100:
        print(f"\n  ... and {len(with_careers) - 100} more.")


def filter_companies(policy=None, size=None, region=None, tech=None):
    """Filter companies by criteria."""
    companies = load_companies()
    if not companies:
        print("  ⚠️  No data. Run 'sync' first.")
        return

    results = companies
    if policy:
        results = [c for c in results if policy.lower() in c.get("remote_policy", "").lower()]
    if size:
        results = [c for c in results if size.lower() in c.get("company_size", "").lower()]
    if region:
        results = [c for c in results if region.lower() in c.get("region", "").lower()]
    if tech:
        results = [c for c in results if any(tech.lower() in t.lower() for t in c.get("technologies", []))]

    print(f"\n  Found {len(results)} companies matching filters:\n")
    print(f"  {'Name':<30} {'Policy':<12} {'Size':<10} {'Region':<12}")
    print(f"  {'-'*30} {'-'*12} {'-'*10} {'-'*12}")

    for c in results[:50]:
        print(f"  {c['name']:<30} {c['remote_policy']:<12} {c['company_size']:<10} {c['region']:<12}")

    if len(results) > 50:
        print(f"\n  ... and {len(results) - 50} more.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "sync":
        sync_companies()
    elif cmd == "list":
        list_companies()
    elif cmd == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not query:
            print("  Usage: python3 remoteintech_scraper.py search <keyword>")
        else:
            search_companies(query)
    elif cmd == "stats":
        show_stats()
    elif cmd == "export":
        export_csv()
    elif cmd == "careers":
        list_careers()
    elif cmd == "filter":
        policy = size = region = tech = None
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--policy" and i+1 < len(sys.argv):
                policy = sys.argv[i+1]; i += 2
            elif sys.argv[i] == "--size" and i+1 < len(sys.argv):
                size = sys.argv[i+1]; i += 2
            elif sys.argv[i] == "--region" and i+1 < len(sys.argv):
                region = sys.argv[i+1]; i += 2
            elif sys.argv[i] == "--tech" and i+1 < len(sys.argv):
                tech = sys.argv[i+1]; i += 2
            else:
                i += 1
        filter_companies(policy, size, region, tech)
    else:
        print(f"  Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
