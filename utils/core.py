"""
Utility functions for Linker CLI.
"""

import requests
from urllib.parse import urlparse

DEBUG = False


def sync_debug_with_state(state):
    """Sync the cached DEBUG value with the state."""
    global DEBUG
    DEBUG = state.get_variable("DEBUG")


def debug_print(*msg):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG and len(msg) == 1:
        print(f"DEBUG: {msg[0]}")
    elif DEBUG and len(msg) > 1:
        print("DEBUG:", " ".join(str(m) for m in msg))


def set_debug(enabled, state):
    """Set the global debug flag."""
    # Update state variable
    state.set_variable("DEBUG", "true" if enabled else "false")
    # Immediately sync the module-global DEBUG flag
    sync_debug_with_state(state)
    # Print debug message only if debugging is enabled
    if DEBUG:
        debug_print(f"Debugging is {'enabled' if enabled else 'disabled'}")


def check_status_code(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return str(response.status_code)
    except requests.RequestException:
        return "0"


def normalize_url(url):
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url
