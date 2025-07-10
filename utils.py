"""
Utility functions for Linker CLI.
"""

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
