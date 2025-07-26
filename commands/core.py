"""
Command handlers for Linker CLI.
"""

import json
import re
import shutil
import sys
from io import StringIO
from contextlib import redirect_stdout
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# from state import CLIState
from dsm_utils import (
    count_http,
    load_spreadsheet,
    get_existing_url,
    get_proposed_url,
    get_row_data,
)
from page_extractor import retrieve_page_data, display_page_data
from migration import migrate
from spinner import Spinner

from constants import DOMAINS
from utils import debug_print, sync_debug_with_state, normalize_url
from commands.common import print_help_for_command, display_domains
from commands.cache import (
    _cache_page_data,
    _is_cache_valid_for_context,
    _update_cache_file_state,
)


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

    # Check if we have cached data that matches the current context
    if state.current_page_data:
        # Verify the cached data is for the current URL/context
        cache_file = state.get_variable("CACHE_FILE")
        is_valid, reason = _is_cache_valid_for_context(state, cache_file)

        if is_valid:
            print("📋 Using cached data")
            data = state.current_page_data
            from commands.report import _generate_summary_report

            _generate_summary_report(include_sidebar, data)
            print("💡 Use 'show page' to see detailed results")
            return
        else:
            debug_print(f"Cache validation failed: {reason}")

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

    _cache_page_data(state, url, data)

    if "error" in data:
        print(f"❌ Failed to extract data: {data['error']}")
        return

    from commands.report import _generate_summary_report

    _generate_summary_report(include_sidebar, data)
    print("💡 Use 'show page' to see detailed results")


def cmd_links(args, state):
    """Analyze all links on the current page for migration requirements."""
    from lookup_utils import analyze_page_links_for_migration

    analyze_page_links_for_migration(state)


def _open_file_in_default_app(file_path):
    system = platform.system()
    file_path = Path(file_path).resolve()
    if system == "Darwin":
        subprocess.run(["open", str(file_path)], check=True)
    elif system == "Windows":
        subprocess.run(["start", "", str(file_path)], shell=True, check=True)
    elif system == "Linux":
        subprocess.run(["xdg-open", str(file_path)], check=True)
    else:
        raise OSError(f"Unsupported operating system: {system}")


def _open_url_in_browser(url):
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", url], check=True)
    elif system == "Windows":
        subprocess.run(["start", "", url], shell=True, check=True)
    elif system == "Linux":
        subprocess.run(["xdg-open", url], check=True)
    else:
        raise OSError(f"Unsupported operating system: {system}")


def cmd_open(args, state):
    """Open different resources in their default applications."""
    if not args:
        return print_help_for_command("open", state)

    target = args[0].lower()

    if target == "dsm":
        dsm_file = state.get_variable("DSM_FILE")
        if not dsm_file:
            print(
                "❌ No DSM file loaded. Use 'load' command or set DSM_FILE variable first."
            )
            return

        dsm_path = Path(dsm_file)
        if not dsm_path.exists():
            print(f"❌ DSM file not found: {dsm_file}")
            return

        try:
            _open_file_in_default_app(dsm_path)
            print(f"✅ Opening DSM file: {dsm_file}")
        except Exception as e:
            print(f"❌ Failed to open DSM file: {e}")

    elif target in ["page", "url"]:
        url = state.get_variable("URL")
        if not url:
            print(
                "❌ No URL set. Use 'set URL <value>' or 'load <domain> <row>' first."
            )
            return

        try:
            _open_url_in_browser(url)
            print(f"✅ Opening URL in browser: {url}")
        except Exception as e:
            print(f"❌ Failed to open URL: {e}")

    elif target == "report":
        domain = state.get_variable("DOMAIN")
        row = state.get_variable("ROW")

        if not domain or not row:
            print("❌ No domain/row loaded. Use 'load <domain> <row>' first.")
            return

        # Generate the expected report filename
        clean_domain = re.sub(r"[^a-zA-Z0-9]", "_", domain.lower())
        report_file = Path(f"./reports/{clean_domain}_{row}.html")

        if not report_file.exists():
            print(f"❌ Report not found: {report_file}")
            print("💡 Generate a report first with: report")
            return

        try:
            _open_file_in_default_app(report_file)
            print(f"✅ Opening report: {report_file}")
        except Exception as e:
            print(f"❌ Failed to open report: {e}")

    else:
        print(f"❌ Unknown target: {target}")
        print("Available targets: dsm, page, url, report")


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

        # Update cache file state when URL is set
        elif var_name == "URL" and value:
            _update_cache_file_state(state, url=value)

        # Update cache file state when DOMAIN or ROW is set
        elif var_name in ["DOMAIN", "ROW"]:
            _update_cache_file_state(state)

    else:
        print(f"❌ Unknown variable: {var_name}")


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
