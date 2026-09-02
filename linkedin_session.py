#!/usr/bin/env python3
"""
LinkedIn Session Manager — Handles persistent login sessions for LinkedIn.
Saves/loads cookies so you only need to log in once.
"""

import json
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
from browser_config import get_browser_options, get_user_agent, is_comet_available

logger = logging.getLogger("linkedin_session")

COOKIE_DIR = BASE_DIR / "logs" / "linkedin_cookies"
STORAGE_STATE = COOKIE_DIR / "state.json"

def ensure_cookie_dir():
    """Create cookie storage directory."""
    COOKIE_DIR.mkdir(exist_ok=True)

def load_session(browser):
    """Try to load an existing LinkedIn session from cookies."""
    if not STORAGE_STATE.exists():
        return None
    
    try:
        logger.info("📂 Loading saved LinkedIn session...")
        return browser.new_persistent_context(
            user_data_dir=str(COOKIE_DIR),
            user_agent=get_user_agent(),
        )
    except Exception as e:
        logger.warning(f"Could not load session: {e}")
        return None

def save_session(context):
    """Save the current browser session (cookies + storage)."""
    try:
        context.storage_state(path=str(STORAGE_STATE))
        logger.info("💾 LinkedIn session saved")
    except Exception as e:
        logger.warning(f"Could not save session: {e}")

def is_logged_in(page):
    """Check if LinkedIn session is active."""
    url = page.url.lower()
    title = page.title().lower()
    
    # Check if we're on a logged-in page
    if any(kw in url for kw in ["feed", "messaging", "linkedin.com/in/"]):
        return True
    if "my network" in title or "homepage" in title:
        return True
    
    # Check for login indicators in page content
    try:
        if page.is_visible('text="Start a post"', timeout=2000):
            return True
        if page.is_visible('text="My Network"', timeout=2000):
            return True
    except:
        pass
    
    return False

def login_with_prompt(page, email, password):
    """Login to LinkedIn with manual verification if needed."""
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    
    import os
    email = email or os.getenv("LINKEDIN_EMAIL")
    password = password or os.getenv("LINKEDIN_PASSWORD")
    
    logger.info("🔐 Navigating to LinkedIn login...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)
    
    if is_logged_in(page):
        logger.info("✅ Already logged in!")
        return True
    
    try:
        # Fill credentials
        page.fill('input[name="session_key"]', email)
        time.sleep(1)
        page.fill('input[name="session_password"]', password)
        time.sleep(1)
        page.click('button[type="submit"]')
        
        # Wait for navigation
        page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(3)
        
        if is_logged_in(page):
            logger.info("✅ Login successful!")
            return True
        else:
            logger.warning("⚠️ Login may have failed. Check browser window.")
            logger.info("👉 Please complete login manually if prompted (CAPTCHA, 2FA)")
            input("Press Enter after you've logged in manually...")
            return is_logged_in(page)
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        logger.info("👉 Please log in manually in the browser window")
        input("Press Enter after you've logged in...")
        return is_logged_in(page)

def get_authenticated_context(email=None, password=None):
    """Get a browser context authenticated with LinkedIn.
    
    Returns (context, page, is_fresh_login) tuple.
    """
    ensure_cookie_dir()
    
    p = sync_playwright().start()
    browser = p.chromium.launch(**get_browser_options(headless=False, slow_mo=50))
    
    # Try to load existing session
    context = load_session(browser)
    is_fresh = False
    
    if context:
        page = context.new_page()
        page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        
        if not is_logged_in(page):
            logger.info("🔓 Session expired, logging in...")
            if login_with_prompt(page, email, password):
                save_session(context)
                is_fresh = True
    else:
        # First time — create fresh context
        context = browser.new_context(user_agent=get_user_agent())
        page = context.new_page()
        if login_with_prompt(page, email, password):
            # Save session for next time
            context.close()
            browser.close()
            p.stop()
            
            # Reopen with persistent context
            context = load_session(browser) or browser.new_context(user_agent=get_user_agent())
            page = context.new_page()
            is_fresh = True
    
    return browser, context, page, is_fresh

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    print("🔐 LinkedIn Session Manager")
    print(f"   Cookie dir: {COOKIE_DIR}")
    print(f"   State file exists: {STORAGE_STATE.exists()}")
    
    browser, context, page, is_fresh = get_authenticated_context(email, password)
    
    if is_logged_in(page):
        print(f"\n✅ LinkedIn session active!")
        print(f"   Current URL: {page.url}")
        print(f"   Fresh login: {is_fresh}")
        save_session(context)
        input("\nPress Enter to close browser...")
    else:
        print("\n❌ Login failed")
    
    context.close()
    browser.close()