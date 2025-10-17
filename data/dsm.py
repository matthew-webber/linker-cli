"""
DSM/Spreadsheet utilities for Linker CLI.
"""

import os
import re
import glob
from urllib.parse import urlparse
import pandas as pd
from pathlib import Path
from time import perf_counter

from constants import DOMAINS

from utils.core import debug_print


class CachedExcelFile:
    """Wrapper around :class:`pandas.ExcelFile` that memoises parsed worksheets."""

    def __init__(self, excel_file):
        self._excel_file = excel_file
        self._cache = {}

    def parse(self, sheet_name=None, header=0, **kwargs):
        """Parse a worksheet, caching the resulting DataFrame by parameters."""

        def _make_hashable(value):
            if isinstance(value, dict):
                return tuple(
                    sorted((k, _make_hashable(v)) for k, v in value.items())
                )
            if isinstance(value, (list, tuple, set)):
                return tuple(_make_hashable(v) for v in value)
            return value

        cache_key = (
            _make_hashable(sheet_name),
            _make_hashable(header),
            tuple(
                sorted((k, _make_hashable(v)) for k, v in kwargs.items())
            )
            if kwargs
            else (),
        )

        if cache_key not in self._cache:
            label = f"parse[{sheet_name or 'default'}]"
            self._cache[cache_key] = _time_execution(
                label,
                self._excel_file.parse,
                sheet_name=sheet_name,
                header=header,
                **kwargs,
            )
        else:
            debug_print(f"⚡ Using cached dataframe for {sheet_name or 'default'}")

        return self._cache[cache_key]

    def clear_cache(self):
        """Clear any cached worksheets."""
        self._cache.clear()

    def close(self):
        """Close the underlying Excel file handle."""
        self._cache.clear()
        return self._excel_file.close()

    def __getattr__(self, attr):
        return getattr(self._excel_file, attr)

    def __enter__(self):
        self._excel_file.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._excel_file.__exit__(exc_type, exc_value, traceback)

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
    return CachedExcelFile(pd.ExcelFile(path))


def _time_execution(label, func, *args, **kwargs):
    """Execute ``func`` and log how long it took for manual performance checks."""
    start = perf_counter()
    try:
        return func(*args, **kwargs)
    finally:
        duration_ms = (perf_counter() - start) * 1000
        debug_print(f"⏱️  {label} completed in {duration_ms:.2f} ms")


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


def get_existing_urls(sheet_df, excel_row, col_name="EXISTING URL"):
    """Return all URLs found in the ``EXISTING URL`` cell.

    DSM cells can contain multiple URLs separated by whitespace or
    punctuation.  Previously only the first URL was returned which broke
    scenarios where a single proposed page consolidates multiple legacy
    URLs.  This function now returns *all* detected URLs in the cell.

    Parameters
    ----------
    sheet_df: pandas.DataFrame
        Data frame representing the worksheet.
    excel_row: int
        Zero-based index of the row to inspect.
    col_name: str, optional
        Column header to read from.  Defaults to ``"EXISTING URL"``.

    Returns
    -------
    list[str]
        A list of all URLs found in the cell.  Returns an empty list if
        no URLs are present.
    """

    raw_value = get_column_value(sheet_df, excel_row, col_name)
    if not raw_value:
        return []

    value = str(raw_value)
    matches = re.findall(r"https?://[^\s,;]+", value, flags=re.IGNORECASE)
    if matches:
        return [m.strip() for m in matches]

    cleaned = value.strip()
    return [cleaned] if cleaned else []


def get_existing_url(sheet_df, excel_row, col_name="EXISTING URL"):
    """Backward compatible wrapper returning the first existing URL."""

    urls = get_existing_urls(sheet_df, excel_row, col_name)
    return urls[0] if urls else ""


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
    """Locate a link's destination within the DSM spreadsheet.

    The function normalizes the supplied ``link_url`` and searches every
    domain sheet for a matching entry. A regex pattern is used so the URL can
    appear anywhere within the cell and optional trailing slashes are handled.

    Args:
        link_url: URL to search for in the DSM.
        excel_data: Pre-loaded Excel data; ``state.excel_data`` is used when
            this argument is ``None``.
        state: State object providing ``excel_data`` when ``excel_data`` is not
            supplied.

    Returns:
        dict: Details about the match including ``domain``, ``row``,
        ``existing_url``, ``proposed_url`` and ``proposed_hierarchy``. If no
        match is found ``{"found": False}`` is returned.
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

                existing_urls = get_existing_urls(df, excel_row, existing_url_col_name)

                if not existing_urls:
                    continue

                # Use regex to check if the target URL exists anywhere in the cell
                matched_url = next(
                    (
                        u
                        for u in existing_urls
                        if re.search(url_pattern, u, re.IGNORECASE)
                    ),
                    None,
                )

                if matched_url:
                    proposed_url = get_proposed_url(
                        df, excel_row, proposed_url_col_name
                    )
                    debug_print(f"Found match! Proposed URL: {proposed_url}")

                    # Generate the proposed hierarchy using existing functions
                    try:
                        from utils.sitecore import get_sitecore_root

                        root = get_sitecore_root(matched_url)
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
                        "existing_url": matched_url,
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
