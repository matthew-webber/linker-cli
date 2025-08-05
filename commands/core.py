"""
Command handlers for Linker CLI.
"""

import re
from io import StringIO
from contextlib import redirect_stdout
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# from state import CLIState
from data.dsm import (
    load_spreadsheet,
)
from utils.core import display_page_data

from constants import DOMAINS
from commands.common import print_help_for_command, display_domains
from utils.cache import (
    _update_state_from_cache,
)


def cmd_links(args, state):
    """Analyze all links on the current page for migration requirements."""
    from utils.core import output_internal_links_analysis_detail

    output_internal_links_analysis_detail(state)


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
            _update_state_from_cache(state, url=value)

        # Update cache file state when DOMAIN or ROW is set
        elif var_name in ["DOMAIN", "ROW"]:
            _update_state_from_cache(state)

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
    elif target == "profile":
        if len(args) < 2:
            print(
                "❌ Missing profile target. Use 'show profile before' or 'show profile after'."
            )
            return
        which = args[1].lower()
        if which not in ("before", "after"):
            print(f"❌ Unknown profile target: {which}")
            print("Available profile targets: before, after")
            return
        file_path = Path("update_provider_profile_urls") / f"{which}.html"
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        try:
            subprocess.run(
                [
                    "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl",
                    str(file_path),
                ],
                check=True,
            )
        except Exception:
            try:
                _open_file_in_default_app(file_path)
            except Exception as e:
                print(f"❌ Failed to open file: {e}")
                return
        print(f"✅ Opening profile {which}: {file_path}")
    else:
        print(f"❌ Unknown show target: {target}")
        print("Available targets: variables, domains, page, profile")
