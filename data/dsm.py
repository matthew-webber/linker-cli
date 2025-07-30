"""
DSM/Spreadsheet utilities for Linker CLI.
"""

import os
import re
import glob
from urllib.parse import urlparse
import pandas as pd
from pathlib import Path

from constants import DOMAINS

from utils.core import debug_print

DSM_DIR = Path(".")


def get_latest_dsm_file():
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


def load_spreadsheet(path):
    debug_print(f"Loading spreadsheet: {path}")
    return pd.ExcelFile(path)


def get_column_value(sheet_df, excel_row, column_name):
    df_idx = excel_row

    target_col = next(
        (
            c
            for c in sheet_df.columns
            if isinstance(c, str) and c.strip().upper() == column_name.upper()
        ),
        None,
    )

    if not target_col:
        debug_print(f"Column '{column_name}' not found in sheet")
        return ""

    try:
        row = sheet_df.iloc[df_idx]
        value = row[target_col]
        return str(value) if pd.notna(value) else ""

    except IndexError:
        debug_print(f"Row index {df_idx} out of range")
        return ""

    except Exception as e:
        debug_print(f"Error retrieving {column_name}: {e}")
        return ""


def get_existing_url(sheet_df, excel_row, col_name="EXISTING URL"):
    return get_column_value(sheet_df, excel_row, col_name)


def get_proposed_url(sheet_df, excel_row, col_name="PROPOSED URL"):
    return get_column_value(sheet_df, excel_row, col_name)


def get_row_data(sheet_df, excel_row, columns=None):
    debug_print(f"Extracting row data from Excel row {excel_row}")
    if columns is None:
        columns = ["EXISTING URL", "PROPOSED URL"]
    result = {}
    for col in columns:
        result[col.upper()] = get_column_value(sheet_df, excel_row, col)
    debug_print(f"Extracted row data: {result}")
    return result


def count_http(url):
    cnt = url.count("http")
    debug_print(f"Counted {cnt} occurrences of 'http' in URL")
    return cnt


def lookup_link_in_dsm(link_url, excel_data=None, state=None):
    """
    Look up a link URL in the DSM spreadsheet to find its proposed new location.

    Args:
        link_url: The URL to look up (from a link on a page being migrated)
        excel_data: Loaded Excel data (optional, will use state if not provided)
        state: State object to get excel_data from if not provided

    Returns:
        dict with keys: 'found', 'domain', 'row', 'existing_url', 'proposed_url', 'proposed_hierarchy'
        Returns {'found': False} if not found
    """
    debug_print(f"Looking up link in DSM: {link_url}")

    if not excel_data and state:
        excel_data = state.excel_data

    if not excel_data:
        debug_print("No Excel data available for lookup")
        return {"found": False, "error": "No DSM data loaded"}

    # Normalize the URL for comparison (remove trailing slashes and fragments/anchors)
    parsed_url = urlparse(link_url)
    # Reconstruct URL without fragment (anchor)
    normalized_link = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

    if parsed_url.query:
        normalized_link += f"?{parsed_url.query}"
    # Remove trailing slash
    normalized_link = normalized_link.rstrip("/")

    debug_print(f"Original link: {link_url}")
    debug_print(f"Normalized link for lookup: {normalized_link}")

    # Create a regex pattern to find the URL anywhere in the cell
    # Escape special regex characters in the URL and allow for optional trailing slash
    escaped_url = re.escape(normalized_link)
    url_pattern = rf"(?:^|\s){escaped_url}/?(?:\s|$)"

    debug_print(f"🔎🔠 Using regex pattern for lookup: {url_pattern}")

    bonus_domains = [
        {
            "full_name": "News Content",
            "worksheet_name": "News Content",
            "sitecore_domain_name": "none_defined",
            "url": "example.com",
            "worksheet_header_row": 0,
        }
    ]

    for domain in DOMAINS + bonus_domains:
        try:
            df = excel_data.parse(
                domain.get("worksheet_name", domain["full_name"]),
                header=domain.get("worksheet_header_row", 4),
            )

            existing_url_col_name = domain.get("existing_url_col_name", "EXISTING URL")
            proposed_url_col_name = domain.get("proposed_url_col_name", "PROPOSED URL")

            # Search through all rows in this domain
            for idx in range(len(df)):
                excel_row = idx
                if domain["full_name"].lower() == "news content":
                    existing_url_col_name = "Current URLs"
                    proposed_url_col_name = "Path"

                existing_url = get_existing_url(df, excel_row, existing_url_col_name)

                if not existing_url:
                    continue

                # Use regex to check if the target URL exists anywhere in the cell
                if re.search(url_pattern, existing_url, re.IGNORECASE):
                    proposed_url = get_proposed_url(
                        df, excel_row, proposed_url_col_name
                    )
                    debug_print(f"Found match! Proposed URL: {proposed_url}")

                    # Generate the proposed hierarchy using existing functions
                    try:
                        from utils.sitecore import get_sitecore_root

                        root = get_sitecore_root(existing_url)
                    except ImportError:
                        root = "Sites"  # Default fallback

                    proposed_segments = (
                        [seg for seg in proposed_url.strip("/").split("/") if seg]
                        if proposed_url
                        else []
                    )

                    return {
                        "found": True,
                        "domain": domain["full_name"],
                        "row": excel_row,
                        "existing_url": existing_url,
                        "proposed_url": proposed_url,
                        "proposed_hierarchy": {
                            "root": root,
                            "segments": proposed_segments,
                        },
                    }

        except Exception as e:
            debug_print(f"Error searching domain {domain}: {e}")
            continue

    debug_print("Link not found in any domain")
    return {"found": False}
