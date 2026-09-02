#!/usr/bin/env python3
"""
Company Research Tool — Deep dive into a company (culture, reviews, tech stack, funding).
"""

import re
import json
from pathlib import Path
from datetime import datetime
from web_scraper import fetch_page

BASE_DIR = Path(__file__).parent

def research_company(name: str, use_js: bool = False) -> dict:
    """Research a company across multiple sources."""
    results = {
        "company": name,
        "researched_at": datetime.now().isoformat(),
        "sources": {},
    }
    
    # 1. Glassdoor reviews
    glassdoor_url = f"https://www.glassdoor.com/Reviews/{name.replace(' ', '-')}-Reviews-E1.htm"
    print(f"  Fetching Glassdoor reviews...")
    try:
        gd = fetch_page(glassdoor_url)
        if "error" not in gd:
            text = gd.get("text", "")
            # Extract ratings
            rating = re.search(r'(\d\.?\d?)\s*out of 5', text)
            CEO = re.search(r'CEO Approval[^0-9]*([\d]+)%', text, re.I)
            recommend = re.search(r'([\d]+)%.*recommend', text, re.I)
            
            results["sources"]["glassdoor"] = {
                "url": glassdoor_url,
                "rating": rating.group(1) if rating else "N/A",
                "ceo_approval": f"{CEO.group(1)}%" if CEO else "N/A",
                "recommend_rate": f"{recommend.group(1)}%" if recommend else "N/A",
                "snippet": text[:1500],
            }
    except Exception as e:
        results["sources"]["glassdoor"] = {"error": str(e)}
    
    # 2. Crunchbase (funding info)
    crunchbase_url = f"https://www.crunchbase.com/organization/{name.lower().replace(' ', '-')}"
    print(f"  Fetching Crunchbase...")
    try:
        cb = fetch_page(crunchbase_url, timeout=10)
        if "error" not in cb:
            text = cb.get("text", "")
            funding = re.findall(r'([\$]\d[\d,.]+(?:M|B|K))', text)
            results["sources"]["crunchbase"] = {
                "url": crunchbase_url,
                "funding": funding or ["N/A"],
                "snippet": text[:1000],
            }
    except:
        results["sources"]["crunchbase"] = {"status": "unavailable"}
    
    # 3. LinkedIn company page
    linkedin_url = f"https://www.linkedin.com/company/{name.lower().replace(' ', '-')}"
    print(f"  Fetching LinkedIn...")
    try:
        li = fetch_page(linkedin_url, timeout=10)
        if "error" not in li:
            text = li.get("text", "")
            employees = re.search(r'(\d[\d,]*)\s*\w+\s*employees', text, re.I)
            results["sources"]["linkedin"] = {
                "url": linkedin_url,
                "employees": employees.group(1) if employees else "N/A",
                "snippet": text[:1000],
            }
    except:
        results["sources"]["linkedin"] = {"status": "unavailable"}
    
    # 4. Company careers page
    careers_urls = [
        f"https://{name.lower().replace(' ', '')}.com/careers",
        f"https://www.{name.lower().replace(' ', '')}.com/jobs",
        f"https://{name.lower().replace(' ', '')}.com/jobs",
    ]
    for url in careers_urls:
        print(f"  Checking {url}...")
        try:
            careers = fetch_page(url, timeout=5)
            if "error" not in careers and careers.get("status") == 200:
                results["sources"]["careers_page"] = {
                    "url": url,
                    "title": careers.get("title", ""),
                    "snippet": careers.get("text", "")[:1000],
                }
                break
        except:
            continue
    else:
        results["sources"]["careers_page"] = {"status": "not_found"}
    
    # 5. Wellfound (AngelList) jobs
    wellfound_url = f"https://wellfound.com/company/{name.lower().replace(' ', '-')}"
    try:
        wf = fetch_page(wellfound_url, timeout=5)
        if "error" not in wf:
            text = wf.get("text", "")
            open_roles = re.findall(r'(\d+)\s*open\s*(?:roles|positions|jobs)', text, re.I)
            results["sources"]["wellfound"] = {
                "url": wellfound_url,
                "open_roles": open_roles[0] if open_roles else "N/A",
                "snippet": text[:800],
            }
    except:
        results["sources"]["wellfound"] = {"status": "unavailable"}
    
    return results

def format_output(result: dict) -> str:
    """Format research results for display."""
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"  Company Research: {result['company']}")
    output.append(f"  Researched: {result['researched_at'][:19]}")
    output.append(f"{'='*60}\n")
    
    # Glassdoor
    if "glassdoor" in result["sources"]:
        gd = result["sources"]["glassdoor"]
        output.append("⭐ GLASSDOOR REVIEWS")
        if "error" not in gd:
            output.append(f"   Rating: {gd.get('rating', 'N/A')}/5")
            output.append(f"   CEO Approval: {gd.get('ceo_approval', 'N/A')}")
            output.append(f"   Would Recommend: {gd.get('recommend_rate', 'N/A')}")
        else:
            output.append(f"   Error: {gd['error']}")
        output.append("")
    
    # Crunchbase
    if "crunchbase" in result["sources"]:
        cb = result["sources"]["crunchbase"]
        output.append("💰 FUNDING (Crunchbase)")
        if "error" not in cb and cb.get("funding"):
            output.append(f"   Total Funding: {', '.join(cb['funding'][:3])}")
        else:
            output.append("   Not available")
        output.append("")
    
    # LinkedIn
    if "linkedin" in result["sources"]:
        li = result["sources"]["linkedin"]
        output.append("👥 LINKEDIN")
        if "error" not in li:
            output.append(f"   Employees: {li.get('employees', 'N/A')}")
            output.append(f"   URL: {li.get('url', '')}")
        output.append("")
    
    # Careers
    if "careers_page" in result["sources"]:
        cp = result["sources"]["careers_page"]
        output.append("💼 CAREERS PAGE")
        if "error" not in cp and cp.get("url"):
            output.append(f"   URL: {cp['url']}")
            output.append(f"   Title: {cp.get('title', 'N/A')}")
        else:
            output.append("   Not found")
        output.append("")
    
    # Wellfound
    if "wellfound" in result["sources"]:
        wf = result["sources"]["wellfound"]
        output.append("🚀 WELLFOUND (AngelList)")
        if "error" not in wf:
            output.append(f"   Open Roles: {wf.get('open_roles', 'N/A')}")
            output.append(f"   URL: {wf.get('url', '')}")
        output.append("")
    
    return "\n".join(output)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Company Research Tool")
    parser.add_argument("company", help="Company name")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    
    args = parser.parse_args()
    
    result = research_company(args.company)
    
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_output(result))

if __name__ == "__main__":
    main()