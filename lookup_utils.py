"""
Link lookup and analysis utilities for Linker CLI.
"""

from urllib.parse import urlparse
from constants import DOMAINS, DOMAIN_MAPPING
from dsm_utils import get_existing_url, get_proposed_url
from utils import debug_print


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

    # Normalize the URL for comparison (remove trailing slashes, etc.)
    normalized_link = link_url.rstrip("/")
    debug_print(f"Normalized link for lookup: {normalized_link}")

    for domain in DOMAINS:
        debug_print(f"Searching in domain: {domain}")
        try:
            df = excel_data.parse(
                domain.get("worksheet_name", domain["full_name"]),
                header=domain.get("worksheet_header_row", 4),
            )
            debug_print(f"Loaded {domain} sheet with {len(df)} rows")

            # Search through all rows in this domain
            for idx in range(len(df)):
                excel_row = idx
                existing_url = get_existing_url(df, excel_row)

                if not existing_url:
                    continue

                # Normalize the existing URL for comparison
                normalized_existing = existing_url.rstrip("/")

                debug_print(
                    f"Comparing '{normalized_link}' with '{normalized_existing}'"
                )

                # Check for exact match
                if normalized_link == normalized_existing:
                    proposed_url = get_proposed_url(df, excel_row)
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


def display_link_lookup_result(result):
    """Display the result of a link lookup in a user-friendly format."""
    if not result["found"]:
        print("❌ Link not found in DSM spreadsheet")
        if "error" in result:
            print(f"   Error: {result['error']}")
        return

    print("✅ Link found in DSM!")
    print(f"📍 Domain: {result['domain']}")
    print(f"📊 Row: {result['row']}")
    print(f"🔗 Existing URL: {result['existing_url']}")
    print(f"🎯 Proposed URL: {result['proposed_url']}")
    print()
    print("🗂️  NEW SITE NAVIGATION PATH:")
    print(f"   Start at: {result['proposed_hierarchy']['root']} (Sites)")

    for segment in result["proposed_hierarchy"]["segments"]:
        print(f"   └─ Navigate to: {segment}")

    if not result["proposed_hierarchy"]["segments"]:
        print("   └─ Target is at root level")

    print()
    print("💡 Use this path to navigate the Sitecore widget and select the target page")


def analyze_page_links_for_migration(state):
    """Analyze all links on the current page and identify which ones need migration lookup."""
    if not state.current_page_data:
        print(
            "❌ No page data available. Run 'check' first to analyze the current page."
        )
        return

    links = state.current_page_data.get("links", [])
    pdfs = state.current_page_data.get("pdfs", [])

    if not links and not pdfs:
        print("No links found on the current page.")
        return

    print("🔗 ANALYZING LINKS FOR MIGRATION")
    print("=" * 50)

    # Filter for internal links that might need migration
    internal_domains = set(DOMAIN_MAPPING.keys())

    migration_candidates = []

    for text, href, status in links + pdfs:
        parsed = urlparse(href)
        if parsed.hostname in internal_domains:
            migration_candidates.append((text, href, status))

    if not migration_candidates:
        print("✅ No internal links found that require migration lookup.")
        return

    print(f"Found {len(migration_candidates)} internal links that may need migration:")
    print()

    for i, (text, href, status) in enumerate(migration_candidates, 1):
        print(f"{i:2}. {text[:60]}")
        print(f"    🔗 {href}")

        # Perform automatic lookup
        result = lookup_link_in_dsm(href, state.excel_data, state)
        if result["found"]:
            print(f"    ✅ Found in DSM - {result['domain']} row {result['row']}")
            print(f"    🎯 New path: {result['proposed_hierarchy']['root']}", end="")
            for segment in result["proposed_hierarchy"]["segments"]:
                print(f" → {segment}", end="")
            print()
        else:
            print(f"    ❌ Not found in DSM - manual migration required")
        print()

    print(
        "💡 Use 'lookup <url>' for detailed navigation instructions for any specific link"
    )
