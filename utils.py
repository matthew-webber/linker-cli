"""
Utility functions for Linker CLI.
"""


def sync_debug_with_state(state):
    """Sync the cached DEBUG value with the state."""
    global DEBUG
    DEBUG = state.get_variable("DEBUG").lower() in ["true", "1", "yes", "on"]


def debug_print(*msg):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG and len(msg) == 1:
        print(f"DEBUG: {msg[0]}")
    elif DEBUG and len(msg) > 1:
        print("DEBUG:", " ".join(str(m) for m in msg))


def set_debug(enabled):
    """Set the global debug flag."""
    # Import here to avoid circular imports
    from main import state

    state.set_variable("DEBUG", "true" if enabled else "false")
    debug_print(f"Debugging is {'enabled' if enabled else 'disabled'}")
