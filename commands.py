"""
Command handlers for Linker CLI.
"""

from state import CLIState
from dsm_utils import (
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

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


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
        from constants import DOMAINS

        domains = DOMAINS
        print(f"\n📋 Available domains ({len(domains)}):")
        for i, domain in enumerate(domains, 1):
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


# ...and so on for other command handlers...
