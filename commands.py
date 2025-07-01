"""
Command handlers for Linker CLI.
"""

import os

# from state import CLIState
from dsm_utils import (
    count_http,
    get_latest_dsm_file,
    load_spreadsheet,
    get_existing_url,
    get_proposed_url,
    get_row_data,
)
from page_extractor import retrieve_page_data, display_page_data
from migration import migrate
from spinner import Spinner
import re
import json
from pathlib import Path

from constants import DOMAINS


# def parse_command(input_line):
#     """Parse command line input into command and arguments."""
#     parts = input_line.strip().split()
#     if not parts:
#         return None, []

#     command = parts[0].lower()
#     args = parts[1:] if len(parts) > 1 else []
#     return command, args


# def execute_command(command, args, DEBUG):
#     """Execute a command with given arguments."""
#     if command in COMMANDS:
#         try:
#             COMMANDS[command](args)
#         except KeyboardInterrupt:
#             print("\n⚠️  Command interrupted")
#         except Exception as e:
#             print(f"❌ Command error: {e}")
#             if DEBUG:
#                 import traceback

#                 traceback.print_exc()
#     else:
#         print(f"❌ Unknown command: {command}")
#         print("💡 Type 'help' for available commands")


CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def cmd_help(args, state, debug_print=None):
    """Show help information."""
    if args and args[0] in COMMANDS:
        cmd_name = args[0]
        cmd_func = COMMANDS[cmd_name]
        print(f"\nHelp for '{cmd_name}':")
        print(cmd_func.__doc__ or "No help available.")
        return

    print("\n" + "=" * 60)
    print("LINKER CLI - COMMAND REFERENCE")
    print("=" * 60)
    print("State Management:")
    print("  set <VAR> <value>     Set a variable (URL, DOMAIN, SELECTOR, etc.)")
    print("  show [target]         Show variables, domains, or page data")
    print()
    print("Data Operations:")
    print("  load <domain> <row>   Load URL from spreadsheet")
    print("  check                 Analyze the current URL")
    print("  migrate               Migrate the current URL")
    print()
    print("Link Migration:")
    print("  lookup <url>          Look up where a link should point on the new site")
    print("  links                 Analyze all links on current page for migration")
    print()
    print("Utility:")
    print("  help [command]        Show this help or help for specific command")
    print("  debug [on|off]        Toggle debug output")
    print("  clear                 Clear the screen")
    print("  exit, quit            Exit the application")
    print()
    print("Variables:")
    for var in state.variables.keys():
        print(f"  {var:12} - {_get_var_description(var)}")
    print("=" * 60)


def cmd_set(args, state, debug_print=None):
    if len(args) < 2:
        print("Usage: set <VARIABLE> <value>")
        print("Available variables:")
        for var in state.variables.keys():
            print(f"  {var}")
        return
    var_name = args[0].upper()
    value = " ".join(args[1:])
    if state.set_variable(var_name, value):
        print(f"✅ {var_name} => {value}")
        if var_name == "DSM_FILE" and value:
            try:
                state.excel_data = load_spreadsheet(value, debug_print=debug_print)
                print(f"📊 DSM file loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load DSM file: {e}")
    else:
        print(f"❌ Unknown variable: {var_name}")


def cmd_show(args, state, debug_print=None):
    if not args:
        state.list_variables()
        return
    target = args[0].lower()
    if target == "variables" or target == "vars":
        state.list_variables()
    elif target == "domains":
        if not state.excel_data:
            print("❌ No DSM file loaded. Set DSM_FILE first.")
            return
        print(f"\n📋 Available domains ({len(DOMAINS)}):")
        for i, domain in enumerate(DOMAINS, 1):
            print(f"  {i:2}. {domain}")
    elif target == "page" or target == "data":
        if state.current_page_data:
            display_page_data(state.current_page_data)
        else:
            print("❌ No page data loaded. Run 'check' first.")
    else:
        print(f"❌ Unknown show target: {target}")
        print("Available targets: variables, domains, page")


def cmd_check(args, state, debug_print=None):
    url = state.get_variable("URL")
    selector = state.get_variable("SELECTOR")
    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return
    print(f"🔍 Checking page: {url}")
    print(f"🎯 Using selector: {selector}")
    spinner = Spinner(f"🔄 Please wait...")
    spinner.start()
    try:
        data = retrieve_page_data(url, selector, debug_print=debug_print)
    except Exception as e:
        print(f"❌ Error during page check: {e}")
        if debug_print:
            debug_print(f"Full error: {e}")
        return
    finally:
        spinner.stop()
    state.current_page_data = data
    url_safe = re.sub(r"[^\w\-_.]", "_", url)[:50]
    cache_file = CACHE_DIR / f"page_check_{url_safe}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    state.set_variable("CACHE_FILE", str(cache_file))
    print(f"✅ Data cached to {cache_file}")
    if "error" in data:
        print(f"❌ Failed to extract data: {data['error']}")
        return
    links_count = len(data.get("links", []))
    pdfs_count = len(data.get("pdfs", []))
    embeds_count = len(data.get("embeds", []))
    print(
        f"📊 Summary: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds found"
    )
    print("💡 Use 'show page' to see detailed results")


def cmd_migrate(args, state, debug_print=None):
    url = state.get_variable("URL")
    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return
    migrate(state, url=url, debug_print=debug_print)


def cmd_load(args, state, debug_print=None):
    """Handle the 'load' command for loading URLs from spreadsheet."""

    # Help text
    if not args or len(args) < 2:
        print("Usage: load <domain> <row_number>")
        if state.excel_data:
            print("Available domains:")
            for i, domain in enumerate(DOMAINS, 1):
                print(f"  {i:2}. {domain}")
        return

    # Load the DSM file if not already loaded
    if not state.excel_data:
        dsm_file = get_latest_dsm_file()
        if not dsm_file:
            print("❌ No DSM file found. Set DSM_FILE manually.")
            return
        state.excel_data = load_spreadsheet(dsm_file)
        state.set_variable("DSM_FILE", dsm_file)

    user_domain = args[0]

    try:
        row_num = int(args[1])
    except ValueError:
        print("❌ Row number must be an integer")
        return

    # Find the actual domain name with case-insensitive lookup
    domain = next((d for d in DOMAINS if d.lower() == user_domain.lower()), None)

    if not domain:
        print(f"❌ Domain '{user_domain}' not found.")
        print("Available domains:")
        for i, d in enumerate(DOMAINS, 1):
            print(f"  {i:2}. {d}")
        return

    # Load the domain sheet
    try:
        df = state.excel_data.parse(sheet_name=domain, header=HEADER_ROW)
        url = get_existing_url(df, row_num)
        proposed = get_proposed_url(df, row_num)

        if not url:
            print(f"❌ Could not find URL for {domain} row {row_num}")
            return

        # Set the variables
        state.set_variable("URL", url)
        state.set_variable("PROPOSED_PATH", proposed)
        state.set_variable("DOMAIN", domain)
        state.set_variable("ROW", str(row_num))

        warn = count_http(url) > 1
        print(f"✅ Loaded URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        if warn:
            print("⚠️  WARNING: Multiple URLs detected in this cell.")

    except Exception as e:
        print(f"❌ Error loading from spreadsheet: {e}")
        debug_print(f"Full error: {e}")


def cmd_debug(args):
    """Toggle debug mode."""
    global DEBUG
    if not args:
        DEBUG = not DEBUG
    else:
        arg = args[0].lower()
        if arg in ["on", "true", "1", "yes"]:
            DEBUG = True
        elif arg in ["off", "false", "0", "no"]:
            DEBUG = False
        else:
            print("Usage: debug [on|off]")
            return

    print(f"🐛 Debug mode: {'ON' if DEBUG else 'OFF'}")


def cmd_clear(args):
    """Clear the screen."""
    os.system("clear" if os.name != "nt" else "cls")


def cmd_legacy(args):
    """Access the legacy workflow system."""
    dsm_file = state.get_variable("DSM_FILE") or get_latest_dsm_file()
    if not dsm_file:
        print("❌ No DSM file found. Set DSM_FILE first.")
        return

    if not state.excel_data:
        try:
            state.excel_data = load_spreadsheet(dsm_file)
            state.set_variable("DSM_FILE", dsm_file)
        except Exception as e:
            print(f"❌ Failed to load DSM file: {e}")
            return

    check_page_workflow(state.excel_data)
