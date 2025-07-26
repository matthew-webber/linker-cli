import os


def cmd_clear(args):
    """Clear the terminal screen."""
    os.system("clear" if os.name != "nt" else "cls")
