from commands.common import print_help_for_command


def cmd_sidebar(args, state):
    """Toggle sidebar inclusion in page extraction."""
    current_value = state.get_variable("INCLUDE_SIDEBAR")

    if not args:
        # Toggle current state
        new_value = not current_value
    else:
        arg = args[0].lower()
        if arg in ["on", "true", "1", "yes"]:
            new_value = True
        elif arg in ["off", "false", "0", "no"]:
            new_value = False
        else:
            return print_help_for_command("sidebar", state)

    state.set_variable("INCLUDE_SIDEBAR", "true" if new_value else "false")
    print(f"🔲 Sidebar inclusion: {'ON' if new_value else 'OFF'}")
