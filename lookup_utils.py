"""
Link lookup and analysis utilities for Linker CLI.
"""

import re
from urllib.parse import urlparse
from constants import DOMAINS, DOMAIN_MAPPING
from dsm_utils import get_existing_url, get_proposed_url
from utils import debug_print
from migrate_hierarchy import format_hierarchy


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

            # Hacky workaround for News Content domain
            # to handle different column names for the time being
            # TODO: add existing/proposed URL col values to the domain mapping
            existing_url_col = None
            proposed_url_col = None

            # Search through all rows in this domain
            for idx in range(len(df)):
                excel_row = idx
                if domain["full_name"].lower() == "news content":
                    existing_url_col = "Current URLs"
                    proposed_url_col = "Path"

                existing_url = get_existing_url(
                    df, excel_row, existing_url_col or "EXISTING URL"
                )

                if not existing_url:
                    continue

                # Use regex to check if the target URL exists anywhere in the cell
                if re.search(url_pattern, existing_url, re.IGNORECASE):
                    proposed_url = get_proposed_url(
                        df, excel_row, proposed_url_col or "PROPOSED URL"
                    )
                    debug_print(f"Found match! Proposed URL: {proposed_url}")

                    # Generate the proposed hierarchy using existing functions
                    try:
                        from migrate_hierarchy import get_sitecore_root

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


def output_internal_links_analysis_detail(state):
    """Output detailed analysis of internal links and the new paths they should take if available."""
    debug_print("Analyzing internal links...")
    debug_print(f"Current page data: {state.current_page_data}")
    if not state.current_page_data:
        print(
            "❌ No page data available. Run 'check' first to analyze the current page."
        )
        return

    links = [
        *state.current_page_data.get("links", []),
        *state.current_page_data.get("sidebar_links", []),
    ]
    pdfs = [
        *state.current_page_data.get("pdfs", []),
        *state.current_page_data.get("sidebar_pdfs", []),
    ]

    if not links and not pdfs:
        print("No links found on the current page.")
        return

    print("🔗 ANALYZING INTERNAL LINKS")
    print("=" * 50)

    # Filter out internal links based on known domains
    internal_domains = set(DOMAIN_MAPPING.keys())

    internal_links = []

    for text, href, status in links + pdfs:
        parsed = urlparse(href)
        if parsed.hostname in internal_domains:
            internal_links.append((text, href, status))

    if not internal_links:
        print("✅ No internal links found.")
        return

    print(f"Found {len(internal_links)} internal links:")
    print()

    for i, (text, href, status) in enumerate(internal_links, 1):
        print(f"{i:2}. {text[:60]}")
        print(f"    🔗 {href}")

        # Perform automatic lookup
        result = lookup_link_in_dsm(href, state.excel_data, state)
        if result["found"]:
            print(f"    ✅ Found in DSM - {result['domain']} - {result['row']}")
            # use shared formatting for new path
            path_str = format_hierarchy(
                result["proposed_hierarchy"]["root"],
                result["proposed_hierarchy"]["segments"],
            )
            for idx, line in enumerate(path_str.split("\n")):
                # Prefix first line with 🎯, subsequent lines align
                prefix = "    " if idx == 0 else "       "
                print(f"{prefix} {line}")
        else:
            print(f"    ❌ Not found in DSM")
        print()

    print(
        "💡 Use 'lookup <url>' for detailed navigation instructions for any specific link"
    )
