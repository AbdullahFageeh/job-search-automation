"""
Shared browser configuration.
Uses Comet browser with Comet's saved profile — all logins (LinkedIn, Gmail, etc.) persist!
"""
import os
from pathlib import Path

# Browser configuration
COMET_PATH = "/Applications/Comet.app/Contents/MacOS/Comet"
COMET_PROFILE = "/Users/abdullah/Library/Application Support/Comet/Default"
USE_COMET = Path(COMET_PATH).exists()

def get_browser_options(headless=False, slow_mo=50):
    """Get Playwright launch options with Comet browser + saved profile."""
    opts = {
        "headless": headless,
        "slow_mo": slow_mo,
    }
    if USE_COMET and not headless:
        opts["executable_path"] = COMET_PATH
        # Use Comet's profile directory — inherits all saved logins/cookies!
        opts["user_data_dir"] = COMET_PROFILE
    return opts

def get_user_agent():
    """Return a realistic desktop user agent."""
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def is_comet_available():
    """Check if Comet browser is available."""
    return USE_COMET

if __name__ == "__main__":
    print(f"Comet available: {USE_COMET}")
    if USE_COMET:
        print(f"Comet path: {COMET_PATH}")
        print(f"Comet profile: {COMET_PROFILE}")
        print(f"Profile exists: {Path(COMET_PROFILE).exists()}")
    else:
        print("Comet not found, will use default Playwright browser")
    print(f"User Agent: {get_user_agent()}")