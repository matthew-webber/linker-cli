"""
Command handlers for Linker CLI.
"""

import json
import os
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
import re
import json

from constants import DOMAINS
from utils import debug_print, sync_debug_with_state, normalize_url

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _cache_page_data(state, url, data):
    # Use domain-row# format if available, fallback to URL
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")
    selector = state.get_variable("SELECTOR")
    include_sidebar = state.get_variable("INCLUDE_SIDEBAR")
    url = normalize_url(url)

    if domain and row:
        cache_filename = f"page_check_{domain}-{row}.json"
    else:
        # Fallback to sanitized URL if domain/row not available
        sanitized_url = re.sub(r"[^\w\-_.]", "_", url)[:50]
        cache_filename = f"page_check_{sanitized_url}.json"

    cache_file = CACHE_DIR / cache_filename

    # Create enhanced cache data with metadata
    cache_data = {
        "metadata": {
            "url": url,
            "domain": domain,
            "row": row,
            "timestamp": datetime.now().isoformat(),
            "cache_filename": cache_filename,
        },
        "page_data": data,
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)

    state.set_variable("CACHE_FILE", str(cache_file))
    print(f"✅ Data cached to {cache_file}")


def _load_cached_page_data(cache_file_path):
    """Load cached page data, handling both old and new cache formats.

    Returns a tuple of (metadata_dict, page_data_dict).
    For old format files, metadata will be empty dict.
    """
    try:
        with open(cache_file_path, "r", encoding="utf-8") as f:
            cached_content = json.load(f)

        # Check if it's the new format (has metadata and page_data keys)
        if (
            isinstance(cached_content, dict)
            and "metadata" in cached_content
            and "page_data" in cached_content
        ):
            return cached_content["metadata"], cached_content["page_data"]
        else:
            # Old format - the entire content is the page data
            return {}, cached_content

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        debug_print(f"Error loading cache file {cache_file_path}: {e}")
        return {}, {}


def _find_cache_file_for_domain_row(domain, row):
    """Find cache file matching a domain and row combination."""
    if not domain or not row:
        return None

    cache_filename = f"page_check_{domain}-{row}.json"
    cache_file = CACHE_DIR / cache_filename

    if cache_file.exists():
        debug_print(f"Found cache file for {domain}-{row}: {cache_file}")
        return str(cache_file)

    debug_print(f"No cache file found for {domain}-{row}")
    return None


def _find_cache_file_for_url(url):
    """Find cache file matching a URL by searching through existing cache files."""
    if not url:
        return None

    url = normalize_url(url)

    # Search through all cache files
    for cache_file in CACHE_DIR.glob("page_check_*.json"):
        try:
            metadata, _ = _load_cached_page_data(cache_file)
            cached_url = metadata.get("url")

            if cached_url and normalize_url(cached_url) == url:
                debug_print(f"Found cache file for URL {url}: {cache_file}")
                return str(cache_file)

        except Exception as e:
            debug_print(f"Error checking cache file {cache_file}: {e}")
            continue

    debug_print(f"No cache file found for URL: {url}")
    return None


def _update_cache_file_state(state, url=None, domain=None, row=None):
    """Update the CACHE_FILE state variable based on current URL/domain/row.

    This function will:
    1. Try to find a matching cache file for the current context
    2. Set CACHE_FILE if found, unset if not found or mismatched
    3. Load the cached page data if a matching file is found
    """
    current_cache_file = state.get_variable("CACHE_FILE")

    # Determine what we're looking for
    search_url = url or state.get_variable("URL")
    search_domain = domain or state.get_variable("DOMAIN")
    search_row = row or state.get_variable("ROW")

    found_cache_file = None

    # First try domain/row if we have both
    if search_domain and search_row:
        found_cache_file = _find_cache_file_for_domain_row(search_domain, search_row)

    # If no domain/row match, try URL
    if not found_cache_file and search_url:
        found_cache_file = _find_cache_file_for_url(search_url)

    # Check if current cache file is still valid
    if current_cache_file and found_cache_file != current_cache_file:
        debug_print(
            f"Current cache file {current_cache_file} doesn't match new context, unsetting"
        )
        state.set_variable("CACHE_FILE", "")
        state.current_page_data = None

    # Set new cache file if found
    if found_cache_file:
        state.set_variable("CACHE_FILE", found_cache_file)

        # Load the cached page data
        try:
            metadata, page_data = _load_cached_page_data(found_cache_file)
            if page_data:
                state.current_page_data = page_data
                print(f"📋 Loaded cached data from {Path(found_cache_file).name}")
            else:
                debug_print(
                    f"Cache file {found_cache_file} exists but contains no page data"
                )
        except Exception as e:
            debug_print(f"Error loading cached page data from {found_cache_file}: {e}")

    elif not found_cache_file and current_cache_file:
        # No matching cache file found, unset current one
        state.set_variable("CACHE_FILE", "")
        state.current_page_data = None
        debug_print("No matching cache file found, unset CACHE_FILE")


def _capture_migrate_page_mapping_output(state):
    """Capture the output from migrate page mapping functionality."""
    from migrate_hierarchy import print_hierarchy, print_proposed_hierarchy

    url = state.get_variable("URL")
    if not url:
        return "❌ No URL set for page mapping."

    output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = output

    try:
        print_hierarchy(url)
        proposed = state.get_variable("PROPOSED_PATH")
        if proposed:
            print_proposed_hierarchy(url, proposed)
        else:
            print("No proposed path set. Use 'set PROPOSED_PATH <path>' to set it.")
    finally:
        sys.stdout = old_stdout

    return output.getvalue()


def _capture_output(func, *args, **kwargs):
    """Capture stdout from a function call and return it as a string."""
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    try:
        func(*args, **kwargs)
        return captured_output.getvalue()
    finally:
        sys.stdout = old_stdout


def _generate_consolidated_section(state):
    """Generate the consolidated section with enhanced link display."""
    url = state.get_variable("URL")
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")
    proposed_path = state.get_variable("PROPOSED_PATH")

    if not state.current_page_data:
        return "<p>No page data available.</p>"

    # Get hierarchy information
    try:
        from migrate_hierarchy import get_sitecore_root

        root = get_sitecore_root(url)
        if url:
            # Parse existing hierarchy
            from urllib.parse import urlparse

            parsed = urlparse(url)
            existing_segments = [
                seg for seg in parsed.path.strip("/").split("/") if seg
            ]
        else:
            existing_segments = []

        # Parse proposed hierarchy
        if proposed_path:
            proposed_segments = [
                seg for seg in proposed_path.strip("/").split("/") if seg
            ]
        else:
            proposed_segments = []
    except Exception:
        root = "Sites"
        existing_segments = []
        proposed_segments = []

    # Build the consolidated HTML
    html = f"""
    <div class="consolidated-section">
        <div class="source-info">
            <h3>📍 Source Information</h3>
            <p><strong>URL:</strong> <a href="{url}" target="_blank">{url}</a></p>
            <p><strong>DSM Location:</strong> {domain} {row}</p>
        </div>
        
        <div class="hierarchy-info">
            <h3>🏗️ Directory Structure</h3>
            <div class="hierarchy-comparison">
                <div class="existing-hierarchy">
                    <h4>Current Structure</h4>
                    <div class="hierarchy-tree">
                        🏠 {root}<br>
    """

    # Add existing hierarchy
    for i, segment in enumerate(existing_segments):
        indent = "   " * (i + 1)
        html += f"{indent}|-- {segment}<br>"

    html += """
                    </div>
                </div>
                <div class="proposed-hierarchy">
                    <h4>Proposed Structure</h4>
                    <div class="hierarchy-tree">
    """

    if proposed_segments:
        html += f"                        🏠 {root}<br>"
        for i, segment in enumerate(proposed_segments):
            indent = "   " * (i + 1)
            html += f"{indent}|-- {segment}<br>"
    else:
        html += "                        <em>No proposed path set</em><br>"

    html += """
                    </div>
                </div>
            </div>
        </div>
        
        <div class="links-summary">
            <h3>🔗 Found Links & Resources</h3>
    """

    # Process links, PDFs, and embeds
    all_items = []

    # Add regular links
    for link in state.current_page_data.get("links", []):
        all_items.append(("link", link))

    # Add sidebar links if available
    for link in state.current_page_data.get("sidebar_links", []):
        all_items.append(("sidebar_link", link))

    # Add PDFs
    for pdf in state.current_page_data.get("pdfs", []):
        all_items.append(("pdf", pdf))

    # Add sidebar PDFs if available
    for pdf in state.current_page_data.get("sidebar_pdfs", []):
        all_items.append(("sidebar_pdf", pdf))

    # Add embeds
    for embed in state.current_page_data.get("embeds", []):
        all_items.append(("embed", embed))

    # Add sidebar embeds if available
    for embed in state.current_page_data.get("sidebar_embeds", []):
        all_items.append(("sidebar_embed", embed))

    if not all_items:
        html += "<p><em>No links or resources found.</em></p>"
    else:
        html += '<div class="links-list">'

        for item_type, item in all_items:
            text, href, status = item

            debug_print(
                f"Processing item: {item_type} - {text} ({href}) with status {status}"
            )

            # Convert http status code to integer
            try:
                status = int(status)
            except (ValueError, TypeError):
                debug_print(
                    f"Invalid status code for {href}: {status} <-- status rec'd"
                )
                status = 0

            # Determine status circle
            if status == 200:
                circle = "🟢"
            elif status == 404:
                circle = "🔴"
            elif status == 0:
                circle = "⚪"
            else:
                circle = f"🟡 [{status}]"

            # Generate copy value based on link type
            copy_value = _get_copy_value(href)

            # Check if it's an internal link for hierarchy display
            is_internal = _is_internal_link(href, url)
            internal_hierarchy = ""

            if is_internal:
                try:
                    from lookup_utils import lookup_link_in_dsm

                    lookup_result = lookup_link_in_dsm(href, state.excel_data, state)
                    hierarchy = (
                        lookup_result.get("proposed_hierarchy", {})
                        if lookup_result
                        else {}
                    )
                    segments = hierarchy.get("segments", [])
                    root_name = hierarchy.get("root", "Sites")
                    # Always add the arrow section, even if segments is empty
                    internal_hierarchy = (
                        f"<div class='internal-hierarchy'>   → {root_name}"
                    )
                    for segment in segments:
                        internal_hierarchy += f" / {segment}"
                    internal_hierarchy += "</div>"
                except Exception:
                    # Still show the arrow with just the root if lookup fails
                    internal_hierarchy = (
                        "<div class='internal-hierarchy'>   → Sites</div>"
                    )

            # Check if this is a tel: or mailto: link for special anchor copy button
            is_contact_link = href.startswith(("tel:", "mailto:"))
            anchor_copy_button = ""

            if is_contact_link:
                anchor_copy_button = f"""
                        <button class="copy-anchor-btn" onclick="copyAnchorToClipboard(event, '{copy_value}', '{text}')" title="Copy as HTML anchor">
                            &lt;/&gt;
                        </button>"""

            html += f"""
                <div class="link-item">
                    <div class="link-main">
                        {circle} <a href="{href}" target="_blank">{text}</a>
                        <button class="copy-btn" onclick="copyToClipboard(event, '{copy_value}')" title="Copy URL">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                            </svg>
                        </button>{anchor_copy_button}
                        <span class="item-type">[{item_type.replace('_', ' ').title()}]</span>
                    </div>
                    {internal_hierarchy}
                </div>
            """

        html += "</div>"

    html += """
        </div>
    </div>
    """

    return html


def _get_copy_value(href):
    """Transform the href for copying based on link type."""
    if href.startswith("tel:"):
        # Extract phone number and format
        phone = href.replace("tel:", "").strip()
        # Remove all non-digit characters
        digits_only = re.sub(r"[^\d]", "", phone)

        if len(digits_only) == 10:
            # 10 digits - add +1
            return f"tel:+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith("1"):
            # 11 digits starting with 1 - just add +
            return f"tel:+{digits_only}"
        else:
            # Something else - return as is
            return href

    elif href.lower().endswith(".pdf") or "/pdf/" in href.lower():
        # PDF link - remove domain part
        from urllib.parse import urlparse

        parsed = urlparse(href)
        return parsed.path

    else:
        # Regular link - return as is
        return href


def _get_report_template_dir():
    """Ensure report template directories exist."""
    template_dir = Path("templates/report")
    template_dir.mkdir(exist_ok=True)

    return template_dir


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


def _generate_html_report(
    domain, row, show_page_output, migrate_output, links_output, consolidated_output
):
    """Generate HTML report from template and captured outputs."""

    template_dir = _get_report_template_dir()

    # Read the template
    template_path = template_dir / "template.html"

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        print(f"⛔️ ERROR: Failed to read template:\n'{e}'")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return template.format(
        domain=domain,
        row=row,
        consolidated_output=consolidated_output,
        show_page_output=show_page_output.replace("<", "&lt;").replace(">", "&gt;"),
        migrate_output=migrate_output.replace("<", "&lt;").replace(">", "&gt;"),
        links_output=links_output.replace("<", "&lt;").replace(">", "&gt;"),
        timestamp=timestamp,
    )


def _generate_summary_report(include_sidebar, data):
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


def _is_internal_link(href, base_url):
    """Check if a link is internal to any of the migration domains."""
    from urllib.parse import urlparse
    from constants import DOMAIN_MAPPING

    try:
        parsed = urlparse(href)
        href_hostname = parsed.hostname

        # Check if it's a relative link (no hostname)
        if not href_hostname:
            return True

        # Check if the hostname is in our internal domains that need migration
        internal_domains = set(DOMAIN_MAPPING.keys())
        return href_hostname in internal_domains
    except Exception:
        return False


def _open_file_in_default_app(file_path):
    """Open a file in its default application based on the OS."""
    system = platform.system()
    file_path = Path(file_path).resolve()  # Get absolute path

    if system == "Darwin":  # macOS
        subprocess.run(["open", str(file_path)], check=True)
    elif system == "Windows":
        subprocess.run(["start", "", str(file_path)], shell=True, check=True)
    elif system == "Linux":
        subprocess.run(["xdg-open", str(file_path)], check=True)
    else:
        raise OSError(f"Unsupported operating system: {system}")


def _open_url_in_browser(url):
    """Open a URL in the default web browser."""
    system = platform.system()

    if system == "Darwin":  # macOS
        subprocess.run(["open", url], check=True)
    elif system == "Windows":
        subprocess.run(["start", "", url], shell=True, check=True)
    elif system == "Linux":
        subprocess.run(["xdg-open", url], check=True)
    else:
        raise OSError(f"Unsupported operating system: {system}")


def _sync_report_static_assets(reports_dir):
    """Copy template static files to reports output
    directory so they can be served with the HTML."""

    template_dir = _get_report_template_dir()

    # grab all .css and .js files from the template directory
    for file in template_dir.glob("*"):
        if file.suffix in {".css", ".js"}:
            dest = reports_dir / file.name
            shutil.copy(file, dest)


def print_help_for_command(command, state):
    # switch case for command help
    match command:
        case "set":
            print("Usage: set <VARIABLE> <value>")
            print("Available variables:")
            for var in state.variables.keys():
                print(f"  {var}")
            return
        case "bulk_check":
            print("Usage: bulk_check [csv_filename]")
            print()
            print("Process multiple pages from a CSV file and update with link counts.")
            print(
                "The CSV should have columns: domain, row, existing_url, no_links, no_pdfs, no_embeds"
            )
            print()
            print("If no filename is provided, uses 'bulk_check_progress.csv'")
            print(
                "Only processes rows where no_links, no_pdfs, and no_embeds are empty."
            )
            print()
            print("The command will:")
            print("  1. Create a template CSV if it doesn't exist")
            print("  2. Load each unprocessed row from the CSV")
            print("  3. Run the check command on each URL")
            print("  4. Update the CSV with link counts")
            print("  5. Cache the page data for faster report generation")
            return


def display_domains():
    for i, domain in enumerate([domain.get("full_name") for domain in DOMAINS], 1):
        print(f"  {i:2}. {domain}")


def cmd_bulk_check(args, state):
    """Process multiple pages from a CSV file and update with link counts."""

    # Default CSV filename
    csv_filename = "bulk_check_progress.csv"

    # Handle command arguments
    if args:
        if args[0] in ["-h", "--help", "help"]:
            print("Usage: bulk_check [csv_filename]")
            print()
            print("Process multiple pages from a CSV file and update with link counts.")
            print(
                "The CSV should have columns: domain, row, existing_url, no_links, no_pdfs, no_embeds"
            )
            print()
            print("If no filename is provided, uses 'bulk_check_progress.csv'")
            print(
                "Only processes rows where no_links, no_pdfs, and no_embeds are empty."
            )
            return
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

            print(
                f"\n🔄 Processing {i}/{len(rows_to_process)}: {domain_name} row {row_num}"
            )

            # Load the URL using existing load functionality
            try:
                success = _bulk_load_url(state, domain_name, row_num)
                if not success:
                    print(f"❌ Failed to load URL for {domain_name} row {row_num}")
                    continue

                url = state.get_variable("URL")
                selector = state.get_variable("SELECTOR")

                if not selector:
                    # Use default selector if none set
                    state.set_variable("SELECTOR", "#main")
                    selector = "#main"

                # Run the check
                print(f"  🔍 Checking: {url}")
                try:
                    data = retrieve_page_data(url, selector, include_sidebar=False)

                    if "error" in data:
                        print(f"  ❌ Error extracting data: {data['error']}")
                        continue

                    # Count items (excluding sidebar)
                    links_count = len(data.get("links", []))
                    pdfs_count = len(data.get("pdfs", []))
                    embeds_count = len(data.get("embeds", []))

                    print(
                        f"  📊 Found: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds"
                    )

                    # Cache the data
                    state.current_page_data = data
                    _cache_page_data(state, url, data)

                    # Update CSV with results
                    _update_bulk_check_csv(
                        csv_path,
                        domain_name,
                        row_num,
                        url,
                        links_count,
                        pdfs_count,
                        embeds_count,
                    )
                    processed_count += 1

                except Exception as e:
                    print(f"  ❌ Error during page check: {e}")
                    debug_print(f"Full error: {e}")
                    continue

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


def _create_bulk_check_template(csv_path):
    """Create a template CSV file for bulk checking."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["domain", "row", "existing_url", "no_links", "no_pdfs", "no_embeds"]
        )
        # Add a few example rows with comments
        writer.writerow(
            ["# Fill in domain and row, leave other columns empty", "", "", "", "", ""]
        )
        writer.writerow(["# Example: medicine.musc.edu", "42", "", "", "", ""])


def _load_bulk_check_csv(csv_path):
    """Load CSV file and return rows that need processing."""
    rows_to_process = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip comment rows and empty rows
            if row["domain"].startswith("#") or not row["domain"].strip():
                continue

            # Skip rows that already have data (all three count fields are filled)
            if (
                row.get("no_links", "").strip()
                and row.get("no_pdfs", "").strip()
                and row.get("no_embeds", "").strip()
            ):
                continue

            # Validate required fields
            if not row.get("domain", "").strip() or not row.get("row", "").strip():
                continue

            try:
                row_num = int(row["row"])
                rows_to_process.append(
                    {"domain": row["domain"].strip(), "row": row_num}
                )
            except ValueError:
                continue

    return rows_to_process


def _bulk_load_url(state, domain_name, row_num):
    """Load URL for bulk processing (simplified version of cmd_load)."""
    # Find the domain configuration
    domain = next(
        (d for d in DOMAINS if d.get("full_name", "").lower() == domain_name.lower()),
        None,
    )

    if not domain:
        debug_print(f"Domain '{domain_name}' not found")
        return False

    df_header_row = domain.get("worksheet_header_row", 4) if domain else 4
    df_header_row = df_header_row + 2

    try:
        df = state.excel_data.parse(
            sheet_name=domain.get("full_name"),
            header=domain.get("worksheet_header_row", 4),
        )
        url = get_existing_url(df, row_num - df_header_row)
        proposed = get_proposed_url(df, row_num - df_header_row)

        if not url:
            debug_print(f"Could not find URL for {domain_name} row {row_num}")
            return False

        # Set the variables
        state.set_variable("URL", url)
        state.set_variable("PROPOSED_PATH", proposed)
        state.set_variable("DOMAIN", domain.get("full_name", "Domain Placeholder"))
        state.set_variable("ROW", str(row_num))

        # Update cache file state for this new domain/row combination
        _update_cache_file_state(
            state, url=url, domain=domain.get("full_name"), row=str(row_num)
        )

        return True

    except Exception as e:
        debug_print(f"Error loading from spreadsheet: {e}")
        return False


def _update_bulk_check_csv(
    csv_path, domain_name, row_num, url, links_count, pdfs_count, embeds_count
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

    _generate_summary_report(include_sidebar, data)

    print("💡 Use 'show page' to see detailed results")


def cmd_clear(args):
    """Clear the screen."""
    os.system("clear" if os.name != "nt" else "cls")


def cmd_debug(args, state):
    """Toggle debug mode."""
    current_debug = state.get_variable("DEBUG")

    if not args:
        # Toggle current state
        new_debug = not current_debug
    else:
        arg = args[0].lower()
        if arg in ["on", "true", "1", "yes"]:
            new_debug = True
        elif arg in ["off", "false", "0", "no"]:
            new_debug = False
        else:
            print("Usage: debug [on|off]")
            return

    state.set_variable("DEBUG", "true" if new_debug else "false")
    sync_debug_with_state(state)  # Sync the cached value
    print(f"🐛 Debug mode: {'ON' if new_debug else 'OFF'}")


def cmd_sidebar(args, state):
    """Toggle sidebar inclusion in page extraction."""
    current_value = state.get_variable("INCLUDE_SIDEBAR")

    if not args:
        # Toggle current state
        new_value = not current_value
    else:
        arg = args[0].lower()
        if arg in ["on", "true", "1", "yes"]:
            new_value = True
        elif arg in ["off", "false", "0", "no"]:
            new_value = False
        else:
            print("Usage: sidebar [on|off]")
            return

    state.set_variable("INCLUDE_SIDEBAR", "true" if new_value else "false")
    print(f"🔲 Sidebar inclusion: {'ON' if new_value else 'OFF'}")


def cmd_help(args, state):
    """Show help information."""
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
    print("  bulk_check [csv]      Process multiple pages from CSV file")
    print("  migrate               Migrate the current URL")
    print()
    print("Link Migration:")
    print("  lookup <url>          Look up where a link should point on the new site")
    print("  links                 Analyze all links on current page for migration")
    print()
    print("Utility:")
    print("  help [command]        Show this help or help for specific command")
    print("  debug [on|off]        Toggle debug output")
    print("  open <target>         Open DSM file, current URL, or report")
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

    user_domain = " ".join(args[:-1])
    row_arg = args[-1]

    debug_print("Executing cmd_load with args:", args)

    # Find the actual domain name with case-insensitive lookup
    domain = next(
        (d for d in DOMAINS if d.get("full_name", "").lower() == user_domain.lower()),
        None,
    )

    df_header_row = domain.get("worksheet_header_row", 4) if domain else 4
    df_header_row = df_header_row + 2

    try:
        row_num = int(row_arg)
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

        # Update cache file state for this new domain/row combination
        _update_cache_file_state(
            state, url=url, domain=domain.get("full_name"), row=str(row_num)
        )

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


def cmd_open(args, state):
    """Open different resources in their default applications."""
    if not args:
        print("Usage: open <target>")
        print("Available targets:")
        print("  dsm        - Open the loaded DSM Excel file")
        print("  [page|url] - Open the current URL in browser")
        print("  report     - Open the latest report for current domain/row")
        return

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


def cmd_report(args, state):
    """Generate an HTML report containing page data, migration mapping, and links analysis."""

    # Check if we need to run 'check' to gather page data
    need_to_check = False

    if not state.current_page_data:
        need_to_check = True
        reason = "No page data available"
    else:
        # Check if current page data matches current URL/domain/row context
        current_url = state.get_variable("URL")
        current_domain = state.get_variable("DOMAIN")
        current_row = state.get_variable("ROW")
        cache_file = state.get_variable("CACHE_FILE")

        # If we have a cache file, verify it matches current context
        if cache_file:
            try:
                metadata, _ = _load_cached_page_data(cache_file)
                cached_url = metadata.get("url")
                cached_domain = metadata.get("domain")
                cached_row = metadata.get("row")

                # Check if cached data matches current context
                if (
                    (current_url and cached_url != normalize_url(current_url))
                    or (current_domain and cached_domain != current_domain)
                    or (current_row and cached_row != current_row)
                ):
                    need_to_check = True
                    reason = "Cached data doesn't match current context"

            except Exception as e:
                debug_print(f"Error validating cache file: {e}")
                need_to_check = True
                reason = "Error validating cached data"
        else:
            # No cache file but we have page data - this shouldn't normally happen
            # but let's check if we need fresh data anyway
            if current_url:
                need_to_check = True
                reason = "No cache file for current context"

    if need_to_check:
        print(f"🔄 Running 'check' to gather page data... ({reason})")
        cmd_check([], state)
        if not state.current_page_data:
            print("❌ Failed to gather page data. Cannot generate report.")
            return
    else:
        print("📋 Using existing cached page data for report")

    # Get domain and row for filename
    domain = state.get_variable("DOMAIN") or "unknown"
    row = state.get_variable("ROW") or "unknown"

    # Ensure the reports directory exists
    reports_dir = Path("./reports")
    reports_dir.mkdir(exist_ok=True)

    # Clean domain name for filename (remove spaces, special chars)
    clean_domain = re.sub(r"[^a-zA-Z0-9]", "_", domain.lower())
    filename = f"./reports/{clean_domain}_{row}.html"  # TODO: replace _ with -

    print(f"📊 Generating report: {filename}")

    # Capture output from each command
    print("  ▶ Capturing page data...")
    if state.current_page_data:
        show_page_output = _capture_output(display_page_data, state.current_page_data)
    else:
        show_page_output = "❌ No page data available. Run 'check' first."

    print("  ▶ Capturing migration mapping...")
    migrate_output = _capture_migrate_page_mapping_output(state)

    print("  ▶ Capturing links analysis...")
    from lookup_utils import analyze_page_links_for_migration

    links_output = _capture_output(analyze_page_links_for_migration, state)

    print("  ▶ Generating consolidated summary...")
    consolidated_output = _generate_consolidated_section(state)

    # Generate HTML
    print("  ▶ Generating HTML...")
    html_content = _generate_html_report(
        domain, row, show_page_output, migrate_output, links_output, consolidated_output
    )

    # Write to file
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Report saved to: {filename}")
        print(f"💡 Open the file in your browser to view the report")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")

    _sync_report_static_assets(reports_dir)

    open_report_now = (
        input("Do you want to open the report in your browser now? [Y/n]: ")
        .strip()
        .lower()
    )
    if open_report_now in ["", "y", "yes"]:
        try:
            cmd_open(["report"], state)
        except Exception as e:
            print(f"❌ Failed to open report: {e}")
            debug_print(f"Full error: {e}")


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
