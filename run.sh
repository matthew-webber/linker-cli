#!/usr/bin/env python3
"""
Proof-of-concept CLI for Linker workflow with debug logging.
"""
import os
import re
import glob
import pandas as pd
import argparse
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from migrate_hierarchy import print_hierarchy, print_proposed_hierarchy


import requests
from bs4 import BeautifulSoup

# Toggle debugging at top level (default: on)
DEBUG = True


# State Management System
class CLIState:
    """Global state manager for the CLI application."""

    def __init__(self):
        self.variables = {
            "URL": "",
            "DOMAIN": "",
            "ROW": "",
            "SELECTOR": "#main",
            "DSM_FILE": "",
            "CACHE_FILE": "",
            "PROPOSED_PATH": "",
        }
        self.excel_data = None
        self.current_page_data = None

    def set_variable(self, name, value):
        """Set a variable in the state."""
        name = name.upper()
        if name in self.variables:
            old_value = self.variables[name]
            self.variables[name] = str(value) if value is not None else ""
            debug_print(
                f"Variable {name} changed from '{old_value}' to '{self.variables[name]}'"
            )
            return True
        else:
            debug_print(f"Unknown variable: {name}")
            return False

    def get_variable(self, name):
        """Get a variable from the state."""
        name = name.upper()
        return self.variables.get(name, "")

    def list_variables(self):
        """List all variables and their current values."""
        print("\n" + "=" * 50)
        print("CURRENT VARIABLES")
        print("=" * 50)
        for name, value in self.variables.items():
            status = "✅ SET" if value else "❌ UNSET"
            display_value = value[:40] + "..." if len(value) > 40 else value
            print(f"{name:12} = {display_value:40} [{status}]")
        print("=" * 50)

    def validate_required_vars(self, required_vars):
        """Check if required variables are set."""
        missing = []
        for var in required_vars:
            if not self.get_variable(var):
                missing.append(var)
        return missing


# Global state instance
state = CLIState()

DOMAINS = [
    "Enterprise",
    "Adult Health",
    "Hollings Cancer",
    "Education",
    "Research",
    "Childrens Health",
    "CDM",
    "CGS",
    "CHP",
    "COM",
    "CON",
    "COP",
    "MUSC Giving",
]

# Constants for Excel parsing
HEADER_ROW = 3  # zero-based index where actual header resides
ROW_OFFSET = HEADER_ROW + 2  # number of rows before data starts

# Directory where DSM files live
DSM_DIR = Path(".")
CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def debug_print(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")


def get_latest_dsm_file():
    """
    Find the latest DSM file matching dsm-*.xlsx (MMDD) based on date in filename.
    """
    pattern = str(DSM_DIR / "dsm-*.xlsx")
    files = glob.glob(pattern)
    debug_print(f"Searching for DSM files with pattern: {pattern}")
    debug_print(f"Found files: {files}")
    latest = None
    latest_date = None
    for f in files:
        basename = os.path.basename(f)
        m = re.match(r"dsm-(\d{4})\.xlsx", basename)
        if m:
            dt = m.group(1)
            try:
                month = int(dt[:2])
                day = int(dt[2:])
                date = (month, day)
                if latest_date is None or date > latest_date:
                    latest_date = date
                    latest = f
                    debug_print(f"New latest DSM candidate: {f} (date {date})")
            except ValueError:
                debug_print(f"Skipping invalid DSM filename: {basename}")
                continue
    debug_print(f"Selected latest DSM file: {latest}")
    return latest


def list_domains(workbook):
    """
    Return list of sheet names (domains) from the workbook.
    """
    debug_print(f"Using predefined domains: {DOMAINS}")
    return DOMAINS


def load_spreadsheet(path):
    """
    Load DSM into pandas.ExcelFile
    """
    debug_print(f"Loading spreadsheet: {path}")
    return pd.ExcelFile(path)


def get_column_value(sheet_df, excel_row, column_name):
    """
    Extract any column value from the DataFrame given an Excel row number and column name.
    Adjusts for HEADER_ROW offset and handles case-insensitive column lookup.

    Args:
        sheet_df: DataFrame from the Excel sheet
        excel_row: Excel row number (1-based)
        column_name: Name of the column to retrieve (case-insensitive)

    Returns:
        String value of the cell, or empty string if not found/error
    """
    debug_print(f"Attempting to extract '{column_name}' from Excel row {excel_row}")

    # Determine DataFrame index
    df_idx = excel_row - ROW_OFFSET
    debug_print(f"Adjusted DataFrame index: {df_idx}")

    # Find column name case-insensitively
    cols = list(sheet_df.columns)
    debug_print(f"Columns available: {cols}")

    target_col = next(
        (
            c
            for c in cols
            if isinstance(c, str) and c.strip().upper() == column_name.upper()
        ),
        None,
    )
    if not target_col:
        debug_print(f"Column '{column_name}' not found in sheet")
        return ""

    try:
        row = sheet_df.iloc[df_idx]
        debug_print(f"Row values: {row.to_dict()}")
        value = row[target_col]
        debug_print(f"Extracted {column_name}: {value}")
        return str(value) if pd.notna(value) else ""
    except IndexError:
        debug_print(f"Row index {df_idx} out of range")
        return ""
    except Exception as e:
        debug_print(f"Error retrieving {column_name}: {e}")
        return ""


def get_existing_url(sheet_df, excel_row):
    """
    Extract the 'Existing URL' field from the DataFrame given an Excel row number.
    """
    return get_column_value(sheet_df, excel_row, "EXISTING URL")


def get_proposed_url(sheet_df, excel_row):
    """
    Extract the 'Proposed URL' field from the DataFrame given an Excel row number.
    """
    return get_column_value(sheet_df, excel_row, "PROPOSED URL")


def get_row_data(sheet_df, excel_row, columns=None):
    """
    Extract multiple column values from the same row.

    Args:
        sheet_df: DataFrame from the Excel sheet
        excel_row: Excel row number (1-based)
        columns: List of column names to retrieve (case-insensitive)
                If None, returns all available columns

    Returns:
        Dictionary with column names as keys and values as strings
    """
    debug_print(f"Extracting row data from Excel row {excel_row}")

    if columns is None:
        columns = ["EXISTING URL", "PROPOSED URL"]  # Default columns of interest

    result = {}
    for col in columns:
        result[col.upper()] = get_column_value(sheet_df, excel_row, col)

    debug_print(f"Extracted row data: {result}")
    return result


def count_http(url):
    cnt = url.count("http")
    debug_print(f"Counted {cnt} occurrences of 'http' in URL")
    return cnt


def retrieve_page_data(url, selector="#main"):
    """
    Fetch page, parse links, PDFs, embeds.
    """
    debug_print(f"Retrieving page data for URL: {url}")

    try:
        # Normalize the URL
        url = normalize_url(url)

        # Get the page content
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract links and PDFs using the specified selector
        links, pdfs = extract_links_from_page(url, selector)

        # Extract embedded content from the same container
        embeds = extract_embeds_from_page(soup, selector)

        data = {
            "url": url,
            "links": links,
            "pdfs": pdfs,
            "embeds": embeds,
            "selector_used": selector,
        }

        debug_print(
            f"Extracted {len(links)} links, {len(pdfs)} PDFs, {len(embeds)} embeds"
        )
        return data

    except Exception as e:
        debug_print(f"Error retrieving page data: {e}")
        return {
            "url": url,
            "links": [],
            "pdfs": [],
            "embeds": [],
            "error": str(e),
            "selector_used": selector,
        }


def display_page_data(data):
    """Display detailed information about extracted page data."""
    print("\n" + "=" * 60)
    print("EXTRACTED PAGE DATA")
    print("=" * 60)

    if "error" in data:
        print(f"❌ Error occurred: {data['error']}")
        return

    print(f"📄 Source URL: {data.get('url', 'Unknown')}")
    print(f"🎯 CSS Selector: {data.get('selector_used', 'Unknown')}")
    print()

    # Display links
    links = data.get("links", [])
    print(f"🔗 LINKS FOUND: {len(links)}")
    if links:
        print("-" * 40)
        # for i, (text, href, status) in enumerate(links[:10], 1):  # Show first 10
        for i, (text, href, status) in enumerate(links, 1):
            status_icon = (
                "✅" if status.startswith("2") else "❌" if status != "0" else "⚠️"
            )
            print(f"{i:2}. {status_icon} [{status}] {text[:50]}")
            print(f"    → {href}")
        # if len(links) > 10:
        #     print(f"    ... and {len(links) - 10} more links")
    print()

    # Display PDFs
    pdfs = data.get("pdfs", [])
    print(f"📄 PDF FILES: {len(pdfs)}")
    if pdfs:
        print("-" * 40)
        for i, (text, href, status) in enumerate(pdfs, 1):
            status_icon = (
                "✅" if status.startswith("2") else "❌" if status != "0" else "⚠️"
            )
            print(f"{i:2}. {status_icon} [{status}] {text[:50]}")
            print(f"    → {href}")
    print()

    # Display embeds
    embeds = data.get("embeds", [])
    print(f"🎬 VIMEO EMBEDS: {len(embeds)}")
    if embeds:
        print("-" * 40)
        for i, (embed_type, title, src) in enumerate(embeds, 1):
            print(f"{i:2}. [VIMEO] {title[:50]}")
            print(f"    → {src}")
    print()

    print("=" * 60)


def check_page_workflow(excel):
    """Legacy workflow function - maintained for compatibility."""
    print(
        "⚠️  This is the legacy workflow. Consider using the new state-based commands:"
    )
    print("   1. set URL <your_url>")
    print("   2. check")
    print("   3. show page")
    print()

    choice = input("Continue with legacy workflow? (y/n) > ").strip().lower()
    if choice != "y":
        print("💡 Use 'help' to see new commands")
        return

    choice = input("Choose source: (u) Page URL, (s) Spreadsheet > ").strip().lower()
    debug_print(f"User chose source: {choice}")
    if choice == "s":
        sheets = list_domains(excel)
        for i, name in enumerate(sheets, start=1):
            print(f"({i}) {name}")
        idx = int(input("Select domain by number > ").strip())
        domain = sheets[idx - 1]
        debug_print(f"Selected domain: {domain}")
        df = excel.parse(domain, header=HEADER_ROW)
        debug_print(f"Loaded DataFrame with shape: {df.shape}")
        row_num = int(input("Enter row number > ").strip())
        url = get_existing_url(df, row_num)
        if not url:
            print("Could not find URL for that row.")
            return
        warn = count_http(url) > 1
        print(f"URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        if warn:
            print("WARNING: Multiple URLs detected in this cell.")
        action = (
            input("Options: (g) Get page data, (m) More details > ").strip().lower()
        )
        debug_print(f"User selected action: {action}")
        if action == "g":
            # Ask for CSS selector
            selector = input("CSS selector (default: #main): ").strip() or "#main"
            print(f"Loading page data using selector '{selector}'...")

            try:
                data = retrieve_page_data(url, selector)
                cache_file = CACHE_DIR / f"page_{domain}_{row_num}.json"

                # Save to JSON file with proper formatting
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(f"✅ Data cached to {cache_file}")

                if "error" in data:
                    print(f"❌ Failed to extract data: {data['error']}")
                    return

                # Show summary
                links_count = len(data.get("links", []))
                pdfs_count = len(data.get("pdfs", []))
                embeds_count = len(data.get("embeds", []))

                print(
                    f"📊 Summary: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds found"
                )

                next_act = (
                    input("Options: (s) Show page data, (m) Migrate page > ")
                    .strip()
                    .lower()
                )
                debug_print(f"Next action: {next_act}")
                if next_act == "s":
                    display_page_data(data)
                elif next_act == "m":
                    print("Migrating page...")
                    migrate(url, data, domain, row_num)
            except Exception as e:
                print(f"❌ Error during page extraction: {e}")
                debug_print(f"Full error: {e}")
        else:
            print("Detail view not implemented.")
    else:
        # Direct URL input
        url = input("Enter page URL > ").strip()
        if not url:
            print("No URL provided.")
            return

        url = normalize_url(url)
        warn = count_http(url) > 1
        print(f"URL: {url[:60]}{'...' if len(url) > 60 else ''}")
        if warn:
            print("WARNING: Multiple URLs detected in this input.")

        selector = input("CSS selector (default: #main): ").strip() or "#main"
        print(f"Loading page data using selector '{selector}'...")

        try:
            data = retrieve_page_data(url, selector)

            # Create a simple cache filename for direct URLs
            url_safe = re.sub(r"[^\w\-_.]", "_", url)[:50]
            cache_file = CACHE_DIR / f"page_direct_{url_safe}.json"

            # Save to JSON file with proper formatting
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"✅ Data cached to {cache_file}")

            if "error" in data:
                print(f"❌ Failed to extract data: {data['error']}")
                return

            # Show summary
            links_count = len(data.get("links", []))
            pdfs_count = len(data.get("pdfs", []))
            embeds_count = len(data.get("embeds", []))

            print(
                f"📊 Summary: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds found"
            )

            next_act = (
                input("Options: (s) Show page data, (m) Migrate page > ")
                .strip()
                .lower()
            )
            if next_act == "s":
                display_page_data(data)
            elif next_act == "m":
                print("Migrating page...")
                migrate(url, data, domain, row_num)
        except Exception as e:
            print(f"❌ Error during page extraction: {e}")
            debug_print(f"Full error: {e}")


def normalize_url(url):
    """Ensure the URL has a scheme."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url


def check_status_code(url):
    """Check the HTTP status code of a URL."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return str(response.status_code)
    except requests.RequestException:
        return "0"


def extract_links_from_page(url, selector="#main"):
    """
    Fetch the page, parse HTML, and return list of (text, absolute href, status_code).
    Also separates PDF links from regular links.
    """
    debug_print(f"Fetching page: {url}")
    debug_print(f"Using CSS selector: {selector}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.select_one(selector)

        if not container:
            debug_print(
                f"Warning: No element found matching selector '{selector}', falling back to entire page"
            )
            container = soup

        anchors = container.find_all("a", href=True)
        debug_print(f"Found {len(anchors)} anchor tags")

        links = []
        pdfs = []

        for a in anchors:
            text = a.get_text(strip=True)
            href = urljoin(response.url, a["href"])
            debug_print(
                f"Processing link: {text[:50]}{'...' if len(text) > 50 else ''} -> {href}"
            )
            status_code = check_status_code(href)

            # Check if this is a PDF link
            if href.lower().endswith(".pdf"):
                pdfs.append((text, href, status_code))
                debug_print(f"  -> Categorized as PDF")
            else:
                links.append((text, href, status_code))
                debug_print(f"  -> Categorized as regular link")

        return links, pdfs

    except requests.RequestException as e:
        debug_print(f"Error fetching page: {e}")
        raise


def extract_embeds_from_page(soup, selector="#main"):
    """Extract Vimeo embedded content from within the specified container."""
    embeds = []

    # Get the same container used for link extraction
    container = soup.select_one(selector)
    if not container:
        debug_print(
            f"Warning: No element found matching selector '{selector}', falling back to entire page for embeds"
        )
        container = soup

    # Find iframes with Vimeo content only
    for iframe in container.find_all("iframe", src=True):
        src = iframe.get("src", "")
        if "vimeo" in src.lower():
            title = (
                iframe.get("title", "") or iframe.get_text(strip=True) or "Vimeo Video"
            )
            embeds.append(("vimeo", title, src))
            debug_print(f"Found Vimeo embed: {title}")

    return embeds


def migrate(**kwargs):
    """Migrate page data to a new format or system.
    This is a placeholder for the actual migration logic."""

    url = kwargs.get("url") or state.get_variable("URL")

    if not url:
        print("❌ No URL set. Use 'set URL <value>' or provide URL as parameter.")
        return

    debug_print(f"🔄 Migrating page: {url}")
    print_hierarchy(url)

    proposed = state.get_variable("PROPOSED_PATH")
    if proposed:
        debug_print(f"📋 Using saved proposed path: {proposed}")
        print_proposed_hierarchy(url, proposed)
    else:
        proposed = input("Enter Proposed URL path (e.g. foo/bar/baz) > ").strip()
        if proposed:
            state.set_variable("PROPOSED_PATH", proposed)
            print_proposed_hierarchy(url, proposed)
        else:
            debug_print("No proposed URL provided.")


# Command Handlers
def cmd_set(args):
    """Handle the 'set' command for variables."""
    if len(args) < 2:
        print("Usage: set <VARIABLE> <value>")
        print("Available variables:")
        for var in state.variables.keys():
            print(f"  {var}")
        return

    var_name = args[0].upper()
    value = " ".join(args[1:])  # Join remaining args as value

    if state.set_variable(var_name, value):
        print(f"✅ {var_name} => {value}")

        # Auto-load DSM file if DSM_FILE is set
        if var_name == "DSM_FILE" and value:
            try:
                state.excel_data = load_spreadsheet(value)
                print(f"📊 DSM file loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load DSM file: {e}")
    else:
        print(f"❌ Unknown variable: {var_name}")


def cmd_show(args):
    """Handle the 'show' command."""
    if not args:
        # Show all variables if no specific target
        state.list_variables()
        return

    target = args[0].lower()

    if target == "variables" or target == "vars":
        state.list_variables()
    elif target == "domains":
        if not state.excel_data:
            print("❌ No DSM file loaded. Set DSM_FILE first.")
            return
        domains = list_domains(state.excel_data)
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


def cmd_check(args):
    """Handle the 'check' command to analyze a page."""
    url = state.get_variable("URL")
    selector = state.get_variable("SELECTOR")

    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return

    print(f"🔍 Checking page: {url}")
    print(f"🎯 Using selector: {selector}")

    try:
        data = retrieve_page_data(url, selector)
        state.current_page_data = data

        # Auto-cache the data
        url_safe = re.sub(r"[^\w\-_.]", "_", url)[:50]
        cache_file = CACHE_DIR / f"page_check_{url_safe}.json"

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        state.set_variable("CACHE_FILE", str(cache_file))
        print(f"✅ Data cached to {cache_file}")

        if "error" in data:
            print(f"❌ Failed to extract data: {data['error']}")
            return

        # Show summary
        links_count = len(data.get("links", []))
        pdfs_count = len(data.get("pdfs", []))
        embeds_count = len(data.get("embeds", []))

        print(
            f"📊 Summary: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds found"
        )
        print("💡 Use 'show page' to see detailed results")

    except Exception as e:
        print(f"❌ Error during page check: {e}")
        debug_print(f"Full error: {e}")


def cmd_migrate(args):
    """Handle the 'migrate' command."""
    url = state.get_variable("URL")

    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return

    migrate(url=url)


def cmd_load(args):
    """Handle the 'load' command for loading URLs from spreadsheet."""
    if not args or len(args) < 2:
        print("Usage: load <domain> <row_number>")
        if state.excel_data:
            print("Available domains:")
            domains = list_domains(state.excel_data)
            for i, domain in enumerate(domains, 1):
                print(f"  {i:2}. {domain}")
        return

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
    domains = list_domains(state.excel_data)
    domain = next((d for d in domains if d.lower() == user_domain.lower()), None)

    if not domain:
        print(f"❌ Domain '{user_domain}' not found.")
        print("Available domains:")
        for i, d in enumerate(domains, 1):
            print(f"  {i:2}. {d}")
        return

    # Load the domain sheet
    try:
        df = state.excel_data.parse(domain, header=HEADER_ROW)
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


def cmd_help(args):
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


# Command registry
COMMANDS = {
    "set": cmd_set,
    "show": cmd_show,
    "check": cmd_check,
    "migrate": cmd_migrate,
    "load": cmd_load,
    "help": cmd_help,
    "debug": cmd_debug,
    "clear": cmd_clear,
    "legacy": cmd_legacy,
    # Aliases
    "vars": lambda args: cmd_show(["variables"]),
    "ls": lambda args: cmd_show(["variables"]),
    "exit": lambda args: exit(0),
    "quit": lambda args: exit(0),
    "q": lambda args: exit(0),
}


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
            if DEBUG:
                import traceback

                traceback.print_exc()
    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Type 'help' for available commands")


def main():
    global DEBUG
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
    parser.set_defaults(debug=True)
    args = parser.parse_args()
    DEBUG = args.debug
    debug_print(f"Debugging is {'enabled' if DEBUG else 'disabled'}")

    # Set initial state from command line args
    if args.url:
        state.set_variable("URL", args.url)
    if args.selector:
        state.set_variable("SELECTOR", args.selector)

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
            # Create a prompt similar to Metasploit
            url_indicator = (
                f"({state.get_variable('URL')[:30]}...)"
                if state.get_variable("URL")
                else "(no url)"
            )
            prompt = f"linker {url_indicator} > "

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
