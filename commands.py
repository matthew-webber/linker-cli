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
from utils import debug_print

DEBUG = True

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def cmd_check(args, state):
    # TODO add ability to run check with args like --url, --selector, --include-sidebar
    url = state.get_variable("URL")
    selector = state.get_variable("SELECTOR")
    include_sidebar = state.get_variable("INCLUDE_SIDEBAR")

    # Validate required variables
    required_vars = ["URL", "SELECTOR"]
    missing_vars, invalid_vars = state.validate_required_vars(required_vars)

    if missing_vars or invalid_vars:
        return

    print(f"🔍 Checking page: {url}")
    print(f"🎯 Using selector: {selector}")
    if include_sidebar:
        print("🔲 Including sidebar content")

    spinner = Spinner(f"🔄 Please wait...")
    spinner.start()

    try:
        data = retrieve_page_data(url, selector, include_sidebar)
    except Exception as e:
        print(f"❌ Error during page check: {e}")
        debug_print(f"Full error: {e}")
        return
    finally:
        spinner.stop()

    state.current_page_data = data

    cache_page_data(state, url, data)

    if "error" in data:
        print(f"❌ Failed to extract data: {data['error']}")
        return

    generate_summary_report(include_sidebar, data)

    print("💡 Use 'show page' to see detailed results")


def generate_summary_report(include_sidebar, data):
    links_count = len(data.get("links", []))
    pdfs_count = len(data.get("pdfs", []))
    embeds_count = len(data.get("embeds", []))

    # Include sidebar counts in summary
    sidebar_links_count = len(data.get("sidebar_links", []))
    sidebar_pdfs_count = len(data.get("sidebar_pdfs", []))
    sidebar_embeds_count = len(data.get("sidebar_embeds", []))

    total_links = links_count + sidebar_links_count
    total_pdfs = pdfs_count + sidebar_pdfs_count
    total_embeds = embeds_count + sidebar_embeds_count

    if include_sidebar and (
        sidebar_links_count > 0 or sidebar_pdfs_count > 0 or sidebar_embeds_count > 0
    ):
        print(
            f"📊 Main content: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds"
        )
        print(
            f"📊 Sidebar content: {sidebar_links_count} links, {sidebar_pdfs_count} PDFs, {sidebar_embeds_count} embeds"
        )
        print(
            f"📊 Total: {total_links} links, {total_pdfs} PDFs, {total_embeds} embeds"
        )
    else:
        print(
            f"📊 Summary: {total_links} links, {total_pdfs} PDFs, {total_embeds} embeds found"
        )


def cache_page_data(state, url, data):
    sanitized_url = re.sub(r"[^\w\-_.]", "_", url)[:50]
    cache_file = CACHE_DIR / f"page_check_{sanitized_url}.json"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    state.set_variable("CACHE_FILE", str(cache_file))
    print(f"✅ Data cached to {cache_file}")


def cmd_clear(args):
    """Clear the screen."""
    os.system("clear" if os.name != "nt" else "cls")


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


def cmd_help(args, state):
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


def cmd_links(args, state):
    """Analyze all links on the current page for migration requirements."""
    from lookup_utils import analyze_page_links_for_migration

    analyze_page_links_for_migration(state)


def cmd_lookup(args, state):
    """Look up a link URL in the DSM spreadsheet to find its new location."""
    if not args:
        print("Usage: lookup <url>")
        print("Example: lookup https://medicine.musc.edu/departments/surgery")
        return

    if not state.excel_data:
        from dsm_utils import get_latest_dsm_file, load_spreadsheet

        dsm_file = get_latest_dsm_file()
        if not dsm_file:
            print(
                "❌ No DSM file found. Set DSM_FILE manually or place a dsm-*.xlsx file in the directory."
            )
            return
        try:
            state.excel_data = load_spreadsheet(dsm_file)
            state.set_variable("DSM_FILE", dsm_file)
            print(f"📊 Loaded DSM file: {dsm_file}")
        except Exception as e:
            print(f"❌ Failed to load DSM file: {e}")
            return

    link_url = args[0]
    from lookup_utils import lookup_link_in_dsm, display_link_lookup_result

    result = lookup_link_in_dsm(link_url, state.excel_data, state)
    display_link_lookup_result(result)


def cmd_load(args, state):
    """Handle the 'load' command for loading URLs from spreadsheet."""

    # Help text
    if not args or len(args) < 2:
        print("Usage: load <domain> <row_number>")
        if state.excel_data:
            print("Available domains:")
            for i, domain in enumerate(
                [domain.get("full_name") for domain in DOMAINS], 1
            ):
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

    # Find the actual domain name with case-insensitive lookup
    domain = next(
        (d for d in DOMAINS if d.get("full_name", "").lower() == user_domain.lower()),
        None,
    )

    df_header_row = domain.get("worksheet_header_row", 4) if domain else 4
    df_header_row = df_header_row + 2

    try:
        row_num = int(args[1])
    except ValueError:
        print("❌ Row number must be an integer")
        return

    if not domain:
        print(f"❌ Domain '{user_domain}' not found.")
        print("Available domains:")
        for i, domain in enumerate([domain.get("full_name") for domain in DOMAINS], 1):
            print(f"  {i:2}. {domain}")
        return

    # Load the domain sheet
    try:
        df = state.excel_data.parse(
            sheet_name=domain.get("full_name"),
            header=domain.get("worksheet_header_row", 4),
        )
        url = get_existing_url(df, row_num - df_header_row)
        proposed = get_proposed_url(df, row_num - df_header_row)

        if not url:
            print(f"❌ Could not find URL for {domain} row {row_num}")
            return

        # Set the variables
        state.set_variable("URL", url)
        state.set_variable("PROPOSED_PATH", proposed)
        state.set_variable("DOMAIN", domain.get("full_name", "Domain Placeholder"))
        state.set_variable("ROW", str(row_num))

        warn = count_http(url) > 1
        print(f"✅ Loaded URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        if warn:
            print("⚠️  WARNING: Multiple URLs detected in this cell.")

    except Exception as e:
        print(f"❌ Error loading from spreadsheet: {e}")
        debug_print(f"Full error: {e}")


def cmd_migrate(args, state):
    url = state.get_variable("URL")

    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return

    migrate(state, url=url)


def cmd_set(args, state):
    if len(args) < 2:
        return print_help_for_command("set", state)
    var_name = args[0].upper()
    value = " ".join(args[1:])
    if state.set_variable(var_name, value):
        print(f"✅ {var_name} => {value}")

        # Special handling for certain variables

        # Automatically load DSM_FILE if set
        if var_name == "DSM_FILE" and value:
            try:
                state.excel_data = load_spreadsheet(value)
                print(f"📊 DSM file loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load DSM file: {e}")
    else:
        print(f"❌ Unknown variable: {var_name}")


def print_help_for_command(command, state):
    # switch case for command help
    match command:
        case "set":
            print("Usage: set <VARIABLE> <value>")
            print("Available variables:")
            for var in state.variables.keys():
                print(f"  {var}")
            return


def cmd_show(args, state):
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
        display_domains()
    elif target == "page" or target == "data":
        if state.current_page_data:
            display_page_data(state.current_page_data)
        else:
            print("❌ No page data loaded. Run 'check' first.")
    else:
        print(f"❌ Unknown show target: {target}")
        print("Available targets: variables, domains, page")


def _get_var_description(var):
    """Get description for a variable."""
    descriptions = {
        "URL": "Target URL to analyze/migrate",
        "DOMAIN": "Current spreadsheet domain",
        "ROW": "Current spreadsheet row number",
        "SELECTOR": "CSS selector for content extraction",
        "DSM_FILE": "Path to the DSM Excel file",
        "CACHE_FILE": "Last cached data file path",
        "PROPOSED_PATH": "Proposed URL path for migration (e.g. /foo/bar/baz)",
    }
    return descriptions.get(var, "User-defined variable")


def display_domains():
    for i, domain in enumerate([domain.get("full_name") for domain in DOMAINS], 1):
        print(f"  {i:2}. {domain}")
