"""
Shared browser configuration.
Uses Comet browser with persistent profile — all logins (LinkedIn, etc.) persist automatically!
"""
import os
from pathlib import Path

COMET_PATH = "/Applications/Comet.app/Contents/MacOS/Comet"
COMET_PROFILE = "/Users/abdullah/Library/Application Support/Comet/Default"
USE_COMET = Path(COMET_PATH).exists()

def get_persistent_options():
    """Options for launch_persistent_context — reuses saved cookies/logins."""
    if not USE_COMET:
        raise RuntimeError("Comet browser not found!")
    return {
        "user_data_dir": COMET_PROFILE,
        "executable_path": COMET_PATH,
        "headless": False,
        "slow_mo": 50,
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

def get_user_agent():
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

if __name__ == "__main__":
    print(f"Comet available: {USE_COMET}")
    if USE_COMET:
        print(f"Profile: {COMET_PROFILE}")
        print(f"Cookies exist: {Path(COMET_PROFILE)/'Cookies'}.exists()")
