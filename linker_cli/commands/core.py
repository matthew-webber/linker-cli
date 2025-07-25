"""Core command registry for Linker CLI."""

from typing import Callable, Dict, List


def get_commands(state) -> Dict[str, Callable[[List[str]], None]]:
    """Dynamically load and return the COMMANDS dictionary."""
    from commands import (
        cmd_bulk_check,
        cmd_check,
        cmd_clear,
        cmd_debug,
        cmd_help,
        cmd_links,
        cmd_load,
        cmd_lookup,
        cmd_migrate,
        cmd_open,
        cmd_report,
        cmd_set,
        cmd_sidebar,
        cmd_show,
    )

    return {
        "bulk_check": lambda args: cmd_bulk_check(args, state),
        "bulk": lambda args: cmd_bulk_check(args, state),  # Alias for bulk
        "check": lambda args: cmd_check(args, state),
        "clear": lambda args: cmd_clear(args),
        "debug": lambda args: cmd_debug(args, state),
        "help": lambda args: cmd_help(args, state),
        "links": lambda args: cmd_links(args, state),
        "load": lambda args: cmd_load(args, state),
        "lookup": lambda args: cmd_lookup(args, state),
        "migrate": lambda args: cmd_migrate(args, state),
        "open": lambda args: cmd_open(args, state),
        "report": lambda args: cmd_report(args, state),
        "set": lambda args: cmd_set(args, state),
        "sidebar": lambda args: cmd_sidebar(args, state),
        "show": lambda args: cmd_show(args, state),
        # Aliases
        "vars": lambda args: cmd_show(["variables"], state),
        "ls": lambda args: cmd_show(["variables"], state),
        "exit": lambda args: exit(0),
        "quit": lambda args: exit(0),
        "q": lambda args: exit(0),
    }
