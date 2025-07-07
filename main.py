import argparse
import warnings
from pathlib import Path
from urllib.parse import urljoin, urlparse

from constants import get_commands
from state import CLIState

from dsm_utils import (
    get_latest_dsm_file,
    load_spreadsheet,
)
from page_extractor import (
    check_status_code,
)
import requests
from bs4 import BeautifulSoup

from utils import debug_print, set_debug

# Toggle debugging at top level (default: on)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Global state instance
state = CLIState()

# Get commands from constants
COMMANDS = get_commands(state)

# Constants for Excel parsing
HEADER_ROW = 3  # zero-based index where actual header resides

# Directory where DSM files live
DSM_DIR = Path(".")
CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def normalize_url(url):
    """Ensure the URL has a scheme."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url


# Command parsing and execution
def parse_command(input_line):
    """Parse command line input into command and arguments."""
    parts = input_line.strip().split()
    if not parts:
        return None, []

    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    return command, args


def execute_command(command, args):
    """Execute a command with given arguments."""
    if command in COMMANDS:
        try:
            COMMANDS[command](args)
        except KeyboardInterrupt:
            print("\n⚠️  Command interrupted")
        except Exception as e:
            print(f"❌ Command error: {e}")
            from utils import DEBUG

            if DEBUG:
                import traceback

                traceback.print_exc()
    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Type 'help' for available commands")


def main():
    parser = argparse.ArgumentParser(
        description="Linker CLI POC - State-based Framework"
    )
    parser.add_argument(
        "--debug", dest="debug", action="store_true", help="Enable debug output"
    )
    parser.add_argument(
        "--no-debug", dest="debug", action="store_false", help="Disable debug output"
    )
    parser.add_argument("--url", help="Set initial URL")
    parser.add_argument("--selector", default="#main", help="Set initial CSS selector")
    parser.add_argument(
        "--include-sidebar",
        action="store_true",
        help="Include sidebar in page extraction",
    )
    parser.set_defaults(debug=True)
    args = parser.parse_args()

    # Set debug mode in utils
    set_debug(args.debug)
    debug_print(f"Debugging is {'enabled' if args.debug else 'disabled'}")

    # Set initial state from command line args
    if args.url:
        state.set_variable("URL", args.url)
    if args.selector:
        state.set_variable("SELECTOR", args.selector)
    if args.include_sidebar:
        state.set_variable("INCLUDE_SIDEBAR", "true")
        debug_print("Include sidebar: TRUE")
    else:
        state.set_variable("INCLUDE_SIDEBAR", "false")

    # Try to auto-load the latest DSM file
    dsm_file = get_latest_dsm_file()
    if dsm_file:
        try:
            state.excel_data = load_spreadsheet(dsm_file)
            state.set_variable("DSM_FILE", dsm_file)
            debug_print(f"Auto-loaded DSM file: {dsm_file}")
        except Exception as e:
            debug_print(f"Failed to auto-load DSM file: {e}")

    print("🔗 Welcome to Linker CLI v2.0 - State-based Framework")
    print("💡 Type 'help' for available commands")

    # Show initial state if any variables are set
    if any(state.variables.values()):
        print("\n📋 Initial state:")
        state.list_variables()

    while True:
        try:
            # Create prompt showing loaded URL (e.g. )
            url_indicator = (
                f"({state.get_variable('URL')[:30]}...)"
                if state.get_variable("URL")
                else "(no url)"
            )
            prompt = f"linker_user {url_indicator} > "

            user_input = input(prompt).strip()
            if not user_input:
                continue

            command, args = parse_command(user_input)
            if command:
                debug_print(f"Executing command: {command} with args: {args}")
                execute_command(command, args)

        except KeyboardInterrupt:
            print("\n⚠️  Use 'exit' or 'quit' to leave the application")
        except EOFError:
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    main()
