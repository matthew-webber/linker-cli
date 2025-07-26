import csv
from commands.cache import _cache_page_data
from commands.common import print_help_for_command
from commands.load import _bulk_load_url
from dsm_utils import get_latest_dsm_file, load_spreadsheet
from page_extractor import retrieve_page_data
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
