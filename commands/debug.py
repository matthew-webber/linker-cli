from utils import sync_debug_with_state
from commands.common import print_help_for_command


def cmd_debug(args, state):
    """Toggle debug mode."""
    current_debug = state.get_variable("DEBUG")

    if not args:
        # Toggle current state
        new_debug = not current_debug
    else:
        arg = args[0].lower()
        if arg in ["on", "true", "1", "yes"]:
            new_debug = True
        elif arg in ["off", "false", "0", "no"]:
            new_debug = False
        else:
            return print_help_for_command("debug", state)

    state.set_variable("DEBUG", "true" if new_debug else "false")
    sync_debug_with_state(state)  # Sync the cached value
    print(f"🐛 Debug mode: {'ON' if new_debug else 'OFF'}")
