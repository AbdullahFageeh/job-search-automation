#!/usr/bin/env python3
"""
Salary Research Tool — Estimate salary ranges for roles and companies.
Scrapes public salary data from multiple sources.
"""

import re
import json
from pathlib import Path
from datetime import datetime
from web_scraper import fetch_page

BASE_DIR = Path(__file__).parent

def research_salary(role: str, location: str = "remote", company: str = None) -> dict:
    """Research salary ranges from public sources."""
    results = {
        "role": role,
        "location": location,
        "company": company,
        "researched_at": datetime.now().isoformat(),
        "sources": {},
    }
    
    # 1. Glassdoor salary
    role_slug = role.lower().replace(" ", "-").replace("/", "-")
    glassdoor_url = f"https://www.glassdoor.com/Salaries/{role_slug}-salary-EI_IE.11,16.htm"
    print(f"  Fetching Glassdoor salary data...")
    try:
        gd = fetch_page(glassdoor_url, timeout=10)
        if "error" not in gd:
            text = gd.get("text", "")
            # Extract salary numbers
            salaries = re.findall(r'\$?(\d{3,4}(?:,\d{3})*(?:\.\d{2})?)', text)
            if salaries:
                nums = [int(float(s.replace(',', ''))) for s in salaries[:4]]
                results["sources"]["glassdoor"] = {
                    "url": glassdoor_url,
                    "salary_range": f"${min(nums):,} - ${max(nums):,}" if len(nums) >= 2 else f"${nums[0]:,}",
                    "median": f"${sum(nums) // len(nums):,}",
                    "sample_count": len(nums),
                }
            else:
                results["sources"]["glassdoor"] = {"status": "no_salary_found"}
        else:
            results["sources"]["glassdoor"] = {"error": gd.get("error", "fetch failed")}
    except Exception as e:
        results["sources"]["glassdoor"] = {"error": str(e)}
    
    # 2. Levels.fyi (for tech roles)
    levels_url = f"https://www.levels.fyi/search?q={role.replace(' ', '+')}"
    print(f"  Fetching Levels.fyi data...")
    try:
        lv = fetch_page(levels_url, timeout=10)
        if "error" not in lv:
            text = lv.get("text", "")
            salaries = re.findall(r'\$?(\d{3,4}(?:,\d{3})*(?:\.\d{2})?)', text)
            if salaries:
                nums = [int(float(s.replace(',', ''))) for s in salaries[:6]]
                results["sources"]["levels_fyi"] = {
                    "url": levels_url,
                    "salary_range": f"${min(nums):,} - ${max(nums):,}" if len(nums) >= 2 else f"${nums[0]:,}",
                    "median": f"${sum(nums) // len(nums):,}",
                }
            else:
                results["sources"]["levels_fyi"] = {"status": "no_salary_found"}
        else:
            results["sources"]["levels_fyi"] = {"error": lv.get("error", "fetch failed")}
    except Exception as e:
        results["sources"]["levels_fyi"] = {"error": str(e)}
    
    # 3. Built In salary data
    builtin_url = f"https://www.builtin.com/data/salaries/{role_slug}"
    print(f"  Fetching Built In data...")
    try:
        bi = fetch_page(builtin_url, timeout=10)
        if "error" not in bi:
            text = bi.get("text", "")
            salaries = re.findall(r'\$?(\d{3,4}(?:,\d{3})*(?:\.\d{2})?)', text)
            if salaries:
                nums = [int(float(s.replace(',', ''))) for s in salaries[:4]]
                results["sources"]["builtin"] = {
                    "url": builtin_url,
                    "salary_range": f"${min(nums):,} - ${max(nums):,}" if len(nums) >= 2 else f"${nums[0]:,}",
                    "median": f"${sum(nums) // len(nums):,}",
                }
            else:
                results["sources"]["builtin"] = {"status": "no_salary_found"}
        else:
            results["sources"]["builtin"] = {"error": bi.get("error", "fetch failed")}
    except Exception as e:
        results["sources"]["builtin"] = {"error": str(e)}
    
    # 4. Comparably
    comparably_url = f"https://www.comparably.com/company-salaries?q={role.replace(' ', '+')}"
    try:
        comp = fetch_page(comparably_url, timeout=10)
        if "error" not in comp:
            text = comp.get("text", "")
            salaries = re.findall(r'\$?(\d{3,4}(?:,\d{3})*(?:\.\d{2})?)', text)
            if salaries:
                nums = [int(float(s.replace(',', ''))) for s in salaries[:4]]
                results["sources"]["comparably"] = {
                    "url": comparably_url,
                    "salary_range": f"${min(nums):,} - ${max(nums):,}" if len(nums) >= 2 else f"${nums[0]:,}",
                    "median": f"${sum(nums) // len(nums):,}",
                }
            else:
                results["sources"]["comparably"] = {"status": "no_salary_found"}
        else:
            results["sources"]["comparably"] = {"error": comp.get("error", "fetch failed")}
    except Exception as e:
        results["sources"]["comparably"] = {"error": str(e)}
    
    # Estimate range
    all_nums = []
    for source, data in results["sources"].items():
        if "median" in data:
            try:
                all_nums.append(int(data["median"].replace("$", "").replace(",", "")))
            except:
                pass
    
    if all_nums:
        results["estimated_range"] = {
            "min": f"${min(all_nums) - 10000:,}",
            "mid": f"${sum(all_nums) // len(all_nums):,}",
            "max": f"${max(all_nums) + 10000:,}",
        }
    
    return results

def format_output(result: dict) -> str:
    """Format salary results for display."""
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"  Salary Research: {result['role']}")
    output.append(f"  Location: {result['location']}" + (f" | Company: {result['company']}" if result['company'] else ""))
    output.append(f"{'='*60}\n")
    
    for source, data in result["sources"].items():
        output.append(f"📊 {source.upper().replace('_', ' ')}")
        if "error" in data:
            output.append(f"   ⚠️ {data['error']}")
        elif "salary_range" in data:
            output.append(f"   Range: {data['salary_range']}")
            output.append(f"   Median: {data['median']}")
        elif "status" in data:
            output.append(f"   {data['status']}")
        output.append("")
    
    if "estimated_range" in result:
        er = result["estimated_range"]
        output.append(f"💰 ESTIMATED RANGE")
        output.append(f"   Low:   {er['min']}")
        output.append(f"   Mid:   {er['mid']}")
        output.append(f"   High:  {er['max']}")
        output.append(f"\n   💡 Negotiation tip: Aim for the mid-high range")
        output.append(f"   Consider total comp (base + bonus + equity)")
    
    return "\n".join(output)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Salary Research Tool")
    parser.add_argument("role", help="Job title (e.g., 'Business Operations Manager')")
    parser.add_argument("--location", "-l", default="remote", help="Location")
    parser.add_argument("--company", "-c", help="Company name")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    args = parser.parse_args()
    
    result = research_salary(args.role, args.location, args.company)
    
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_output(result))

if __name__ == "__main__":
    main()