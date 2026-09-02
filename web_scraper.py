#!/usr/bin/env python3
"""
Web Scraper — Fetch and parse webpages for job details, company info, etc.
Supports both static (requests) and dynamic (Playwright) pages.
"""

import re
import json
import time
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---- Static Fetcher (fast, no browser) ----

def fetch_page(url: str, timeout: int = 15) -> dict:
    """Fetch a webpage and return parsed content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(separator="\n", strip=True)
            title = soup.title.string.strip() if soup.title else ""
            return {
                "url": url,
                "status": resp.status_code,
                "title": title,
                "text": text[:20000],  # cap at 20K chars
                "html": resp.text,
                "links": extract_links(soup, url),
                "emails": extract_emails(text),
            }
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "error": str(e)}


def extract_links(soup: BeautifulSoup, base_url: str) -> list:
    """Extract all hyperlinks from a page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        text = a.get_text(strip=True)
        if text:
            links.append({"text": text, "url": href})
    return links[:200]  # cap


def extract_emails(text: str) -> list:
    """Extract email addresses from text."""
    return list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)))


def extract_job_details(url: str) -> dict:
    """Extract job posting details from a URL."""
    page = fetch_page(url)
    if "error" in page:
        return page

    text = page["text"]
    title = page["title"]

    # Extract key fields from text
    def find_field(patterns):
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE | re.DOTALL)
            if m:
                return m.group(1).strip()[:500]
        return None

    return {
        "url": url,
        "title": title,
        "company": find_field([r"(?:company|employer)[\s:]+([^\n]+)"]),
        "location": find_field([r"(?:location|location:|based in|remote)[\s:]+([^\n]+)"]),
        "salary": find_field([r"(?:salary|pay|compensation|salary range)[\s:]+([^\n]+)"]),
        "description": text[:3000],
        "requirements": find_field([r"(?:requirements|qualifications|qualify|must have)[\s:]+(.*?)(?:responsibilities|duties|what you|benefits|$)", re.DOTALL]),
        "emails": page["emails"],
        "scraped_at": datetime.now().isoformat(),
    }


# ---- Dynamic Fetcher (Playwright for JS-rendered pages) ----

def fetch_page_js(url: str, wait: float = 3.0) -> dict:
    """Fetch a page using Playwright (for JS-rendered content)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"url": url, "error": "Playwright not installed. Run: playwright install chromium"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(wait)  # wait for JS to render
            content = page.content()
            title = page.title()
            text = page.inner_text("body")
            soup = BeautifulSoup(content, "lxml")
            return {
                "url": url,
                "title": title,
                "text": text[:20000],
                "html": content,
                "links": extract_links(soup, url),
                "emails": extract_emails(text),
            }
        except Exception as e:
            logger.error(f"Playwright fetch failed for {url}: {e}")
            return {"url": url, "error": str(e)}
        finally:
            browser.close()


# ---- Company Research ----

def research_company(company_name: str) -> dict:
    """Quick company research via web search + fetch."""
    search_url = f"https://www.google.com/search?q={company_name}+company+remote+jobs"
    page = fetch_page(search_url)
    if "error" in page:
        # fallback: try LinkedIn
        search_url = f"https://www.linkedin.com/company/{company_name.replace(' ', '-')}"
        page = fetch_page(search_url)

    text = page.get("text", "")
    return {
        "company": company_name,
        "page_title": page.get("title", ""),
        "snippet": text[:1500],
        "emails_found": page.get("emails", []),
        "scraped_at": datetime.now().isoformat(),
    }


# ---- CLI ----

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Web Scraper for job search")
    sub = parser.add_subparsers(dest="action")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch and parse a webpage")
    p_fetch.add_argument("url", help="URL to fetch")
    p_fetch.add_argument("--js", action="store_true", help="Use Playwright for JS pages")

    # job
    p_job = sub.add_parser("job", help="Extract job details from a posting URL")
    p_job.add_argument("url", help="Job posting URL")

    # company
    p_company = sub.add_parser("company", help="Research a company")
    p_company.add_argument("name", help="Company name")

    args = parser.parse_args()

    if args.action == "fetch":
        result = fetch_page_js(args.url) if args.js else fetch_page(args.url)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "job":
        result = extract_job_details(args.url)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "company":
        result = research_company(args.name)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()