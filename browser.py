"""
Shared Browser Launcher — Uses Comet by default, falls back to Playwright Chromium.
"""
import os
from pathlib import Path

# Prefer Comet if available, otherwise use Playwright's bundled Chromium
COMET_PATH = "/Applications/Comet.app/Contents/MacOS/Comet"
USE_COMET = Path(COMET_PATH).exists()

def get_browser_options(headless=False, slow_mo=100):
    """Return Playwright launch options configured for Comet or Chromium."""
    opts = {
        "headless": headless,
        "slow_mo": slow_mo,
    }
    if USE_COMET and not headless:
        # Use Comet for visible automation (better stealth)
        opts["executable_path"] = COMET_PATH
    return opts

def get_user_agent():
    """Return a standard desktop user agent."""
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Comet/120.0.0.0 Safari/537.36"