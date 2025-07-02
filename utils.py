"""
Utility functions for Linker CLI.
"""

# Global debug flag
DEBUG = True


def debug_print(msg):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG:
        print(f"DEBUG: {msg}")


def set_debug(enabled):
    """Set the global debug flag."""
    global DEBUG
    DEBUG = enabled
