import pandas as pd
from constants import DOMAINS
from utils.cache import (
    _cache_page_data,
    _update_state_from_cache,
    _is_cache_valid_for_context,
)
from commands.common import print_help_for_command
from data.dsm import (
    get_existing_url,
    get_latest_dsm_file,
    get_proposed_url,
    load_spreadsheet,
)
from utils.scraping import retrieve_page_data
from utils.core import debug_print


from pathlib import Path


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


def _create_bulk_check_template(xlsx_path):
    """Create a template Excel file for bulk checking."""
    data = {
        "kanban_id": ["# Kanban card ID", "# Example: abc123def456"],
        "title": ["# Page title here", "# Example: Department of Surgery"],
        "domain": [
            "# Fill in domain and row, leave other columns empty",
            "# Example: medicine.musc.edu",
        ],
        "row": ["", 42],
        "existing_url": ["", ""],
        "no_links": ["", ""],
        "no_pdfs": ["", ""],
        "no_embeds": ["", ""],
        "% difficulty": ["", ""],
    }

    df = pd.DataFrame(data)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")


def _load_bulk_check_xlsx(xlsx_path):
    """Load Excel file and return rows that need processing."""
    rows_to_process = []

    # Read the Excel file
    df = pd.read_excel(xlsx_path, engine="openpyxl")

    for index, row in df.iterrows():
        # Skip comment rows and empty rows
        debug_print(f"Processing row: {row.to_dict()}")
        domain_val = str(row.get("domain", "")).strip()
        debug_print(f"Row domain: {domain_val}")

        if domain_val.startswith("#") or not domain_val:
            continue

        # Skip rows that already have data (all count fields are filled)
        if (
            pd.notna(row.get("no_links", ""))
            and str(row.get("no_links", "")).strip()
            and pd.notna(row.get("no_pdfs", ""))
            and str(row.get("no_pdfs", "")).strip()
            and pd.notna(row.get("no_embeds", ""))
            and str(row.get("no_embeds", "")).strip()
            and pd.notna(row.get("% difficulty", ""))
            and str(row.get("% difficulty", "")).strip()
        ):
            continue

        # Validate required fields
        row_val = row.get("row", "")
        if not domain_val or pd.isna(row_val) or str(row_val).strip() == "":
            continue

        try:
            row_num = int(
                float(str(row_val))
            )  # Handle potential float values from Excel
            rows_to_process.append(
                {
                    "kanban_id": str(row.get("kanban_id", "")).lstrip("'").strip(),
                    "title": str(row.get("title", "")).strip(),
                    "domain": domain_val,
                    "row": row_num,
                }
            )
        except (ValueError, TypeError):
            continue

    return rows_to_process


def _update_bulk_check_xlsx(
    xlsx_path,
    domain_name,
    row_num,
    url,
    links_count,
    pdfs_count,
    embeds_count,
    difficulty_pct,
):
    """Update the Excel file with the results for a specific row."""
    # Read the Excel file
    df = pd.read_excel(xlsx_path, engine="openpyxl")

    # Find and update the matching row
    for index, row in df.iterrows():
        domain_val = str(row.get("domain", "")).strip()
        row_val = row.get("row", "")

        if domain_val.lower() == domain_name.lower() and str(row_val).strip() == str(
            row_num
        ):
            df.at[index, "existing_url"] = url
            df.at[index, "no_links"] = links_count
            df.at[index, "no_pdfs"] = pdfs_count
            df.at[index, "no_embeds"] = embeds_count
            df.at[index, "% difficulty"] = difficulty_pct
            break

    # Write back to Excel file
    df.to_excel(xlsx_path, index=False, engine="openpyxl")


def _bulk_load_url(state, domain_name, row_num):
    """
    Loads URL and related information from an Excel spreadsheet for a given domain and row number.

    This function retrieves data from an Excel sheet based on the provided domain name and row number.
    It sets various state variables, including the URL, proposed path, domain name, and row number.
    If the domain or URL cannot be found, or if an error occurs during processing, the function
    returns `False`.

    Args:
        state (object): The state object containing the Excel data and methods to set variables.
        domain_name (str): The name of the domain to search for in the spreadsheet.
        row_num (int): The row number in the spreadsheet to retrieve data from.

    Returns:
        bool: `True` if the URL and related data were successfully loaded and state variables were set,
              `False` otherwise.

    Notes:
        - The function assumes the presence of a global `DOMAINS` list, where each domain is a dictionary
          containing metadata such as `full_name` and `worksheet_header_row`.
        - The `state.excel_data.parse` method is used to parse the Excel sheet.
        - The `get_existing_url` and `get_proposed_url` functions are used to extract URL data from the
          spreadsheet.
    """

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

        state.set_variable("URL", url)
        state.set_variable("PROPOSED_PATH", proposed)
        state.set_variable("DOMAIN", domain.get("full_name", "Domain Placeholder"))
        state.set_variable("ROW", str(row_num))

        _update_state_from_cache(
            state, url=url, domain=domain.get("full_name"), row=str(row_num)
        )

        return True

    except Exception as e:
        debug_print(f"Error loading from spreadsheet: {e}")
        return False


def cmd_bulk_check(args, state):
    """Process multiple pages from an Excel file and update with link counts."""

    # Default Excel filename
    xlsx_filename = "bulk_check_progress.xlsx"

    # Handle command arguments
    if args:
        if args[0] in ["-h", "--help", "help"]:
            return print_help_for_command("bulk_check", state)
        else:
            xlsx_filename = args[0]

    xlsx_path = Path(xlsx_filename)

    # Check if Excel file exists, create template if not
    if not xlsx_path.exists():
        print(f"📝 Creating template Excel file: {xlsx_filename}")
        _create_bulk_check_template(xlsx_path)
        print(
            f"✅ Template created. Please fill in domain and row values, then run the command again."
        )
        return

    # Load Excel file and process unscanned rows
    try:
        rows_to_process = _load_bulk_check_xlsx(xlsx_path)
        if not rows_to_process:
            print("✅ All rows in the Excel file have already been processed!")
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
                f"\n🔄 Processing {i}/{len(rows_to_process)}: {domain_name} row {row_num}, kanban_id: {kanban_id}"
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

                # Check if we have cached data and if it's valid
                use_cache = False
                if state.current_page_data:
                    cache_file = state.get_variable("CACHE_FILE")
                    is_valid, reason = _is_cache_valid_for_context(state, cache_file)

                    if is_valid:
                        print(f"  🗂️ Using cached data")
                        data = state.current_page_data
                        use_cache = True
                    else:
                        print(f"  🔄 Cache invalid ({reason}), will regenerate")
                        state.current_page_data = None
                        state.set_variable("CACHE_FILE", "")

                if not use_cache:
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

                # Update Excel file with results
                _update_bulk_check_xlsx(
                    xlsx_path,
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
        print(f"📋 Results saved to: {xlsx_filename}")

    except Exception as e:
        print(f"❌ Error processing Excel file: {e}")
        debug_print(f"Full error: {e}")
