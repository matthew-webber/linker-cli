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
import csv

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

from constants import DOMAINS
from utils import debug_print, sync_debug_with_state, normalize_url
from commands.common import print_help_for_command, display_domains
from commands.cache import _cache_page_data, _is_cache_valid_for_context, _update_cache_file_state
from commands.load import _bulk_load_url






def cmd_bulk_check(args, state):
    """Process multiple pages from a CSV file and update with link counts."""

    # Default CSV filename
    csv_filename = "bulk_check_progress.csv"

    # Handle command arguments
    if args:
        if args[0] in ["-h", "--help", "help"]:
            return print_help_for_command("bulk_check", state)
        else:
            csv_filename = args[0]

    csv_path = Path(csv_filename)

    # Check if CSV exists, create template if not
    if not csv_path.exists():
        print(f"📝 Creating template CSV file: {csv_filename}")
        _create_bulk_check_template(csv_path)
        print(
            f"✅ Template created. Please fill in domain and row values, then run the command again."
        )
        return

    # Load CSV and process unscanned rows
    try:
        rows_to_process = _load_bulk_check_csv(csv_path)
        if not rows_to_process:
            print("✅ All rows in the CSV have already been processed!")
            return

        print(f"📊 Found {len(rows_to_process)} rows to process")

        # Ensure we have a DSM file loaded
        if not state.excel_data:
            dsm_file = get_latest_dsm_file()
            if not dsm_file:
                print(
                    "❌ No DSM file found. Set DSM_FILE manually or place a dsm-*.xlsx file in the directory."
                )
                return
            state.excel_data = load_spreadsheet(dsm_file)
            state.set_variable("DSM_FILE", dsm_file)
            print(f"📊 Loaded DSM file: {dsm_file}")

        # Process each row
        processed_count = 0
        for i, row_data in enumerate(rows_to_process, 1):
            domain_name = row_data["domain"]
            row_num = row_data["row"]
            kanban_id = row_data.get("kanban_id", "")

            print(
                f"\n🔄 Processing {i}/{len(rows_to_process)}: {domain_name} row {row_num}"
            )

            # Load the URL using existing load functionality
            try:
                success = _bulk_load_url(state, domain_name, row_num)
                if not success:
                    print(f"❌ Failed to load URL for {domain_name} row {row_num}")
                    continue

                # Set kanban_id in state for caching
                state.set_variable("KANBAN_ID", kanban_id)

                url = state.get_variable("URL")
                selector = state.get_variable("SELECTOR")

                if not selector:
                    # Use default selector if none set
                    state.set_variable("SELECTOR", "#main")
                    selector = "#main"

                # Check if we have cached data first
                if state.current_page_data:
                    print(f"  � Using cached data")
                    data = state.current_page_data
                else:
                    # Run the check
                    print(f"  🔍 Checking: {url}")
                    data = retrieve_page_data(url, selector, include_sidebar=False)

                    if "error" in data:
                        print(f"  ❌ Error extracting data: {data['error']}")
                        continue

                    # Cache the data
                    state.current_page_data = data
                    _cache_page_data(state, url, data)

                # Count items (excluding sidebar)
                links_count = len(data.get("links", []))
                pdfs_count = len(data.get("pdfs", []))
                embeds_count = len(data.get("embeds", []))

                # Calculate difficulty percentage
                difficulty_pct = _calculate_difficulty_percentage(data.get("links", []))

                print(
                    f"  📊 Found: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds, {difficulty_pct:.1%} difficulty"
                )

                # Update CSV with results
                _update_bulk_check_csv(
                    csv_path,
                    domain_name,
                    row_num,
                    url,
                    links_count,
                    pdfs_count,
                    embeds_count,
                    difficulty_pct,
                )
                processed_count += 1

            except Exception as e:
                print(f"❌ Error processing {domain_name} row {row_num}: {e}")
                debug_print(f"Full error: {e}")
                continue

        print(
            f"\n✅ Bulk check complete! Processed {processed_count}/{len(rows_to_process)} rows"
        )
        print(f"📋 Results saved to: {csv_filename}")

    except Exception as e:
        print(f"❌ Error processing CSV file: {e}")
        debug_print(f"Full error: {e}")


def _calculate_difficulty_percentage(links_data):
    """Calculate the difficulty percentage based on easy links (tel: and mailto:).

    Returns a float between 0 and 1, where:
    - 0 means all links are easy (tel: or mailto:)
    - 1 means no links are easy
    - 0.5 means half the links are easy
    """
    if not links_data:
        return 0.0

    total_links = len(links_data)
    if total_links == 0:
        return 0.0

    easy_links = 0
    for link in links_data:
        # link is a tuple of (text, href, status)
        href = link[1] if len(link) > 1 else ""
        if href.startswith(("tel:", "mailto:")):
            easy_links += 1

    # Calculate difficulty as (total - easy) / total
    difficulty = (total_links - easy_links) / total_links
    return difficulty


def _create_bulk_check_template(csv_path):
    """Create a template CSV file for bulk checking."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "kanban_id",
                "title",
                "domain",
                "row",
                "existing_url",
                "no_links",
                "no_pdfs",
                "no_embeds",
                "% difficulty",
            ]
        )
        # Add a few example rows with comments
        writer.writerow(
            [
                "# Kanban card ID",
                "# Page title here",
                "# Fill in domain and row, leave other columns empty",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )
        writer.writerow(
            [
                "# Example: abc123def456",
                "# Example: Department of Surgery",
                "# Example: medicine.musc.edu",
                "42",
                "",
                "",
                "",
                "",
                "",
            ]
        )


def _load_bulk_check_csv(csv_path):
    """Load CSV file and return rows that need processing."""
    rows_to_process = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip comment rows and empty rows
            debug_print(f"Processing row: {row}")
            debug_print(f"Row domain: {row['domain']}")
            if row["domain"].startswith("#") or not row["domain"].strip():
                continue

            # Skip rows that already have data (all count fields are filled)
            if (
                row.get("no_links", "")
                and row.get("no_pdfs", "")
                and row.get("no_embeds", "")
                and row.get("% difficulty", "")
            ):
                continue

            # Validate required fields
            if not row.get("domain", "") or not row.get("row", ""):
                continue

            try:
                row_num = int(row["row"])
                rows_to_process.append(
                    {
                        "kanban_id": row.get("kanban_id", "").lstrip("'"),
                        "title": row.get("title", "").strip(),
                        "domain": row["domain"].strip(),
                        "row": row_num,
                    }
                )
            except ValueError:
                continue

    return rows_to_process




def _update_bulk_check_csv(
    csv_path,
    domain_name,
    row_num,
    url,
    links_count,
    pdfs_count,
    embeds_count,
    difficulty_pct,
):
    """Update the CSV file with the results for a specific row."""
    # Read all rows
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Find and update the matching row
    for row in rows:
        if row["domain"].strip().lower() == domain_name.lower() and row[
            "row"
        ].strip() == str(row_num):
            row["existing_url"] = url
            row["no_links"] = str(links_count)
            row["no_pdfs"] = str(pdfs_count)
            row["no_embeds"] = str(embeds_count)
            row["% difficulty"] = str(difficulty_pct)
            break

    # Write back to file
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def cmd_lookup(args, state):
    """Look up a link URL in the DSM spreadsheet to find its new location."""
    if not args:
        return print_help_for_command("lookup", state)

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



def cmd_migrate(args, state):
    url = state.get_variable("URL")

    if not url:
        print("❌ No URL set. Use 'set URL <value>' first.")
        return

    migrate(state, url=url)


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
