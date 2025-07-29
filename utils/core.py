"""
Utility functions for Linker CLI.
"""

import requests
from urllib.parse import urlparse
import socket

from constants import DOMAIN_MAPPING
from utils.sitecore import format_hierarchy

# from constants import DOMAIN_MAPPING
# from data.dsm import lookup_link_in_dsm
# from migrate_hierarchy import format_hierarchy

DEBUG = False


def sync_debug_with_state(state):
    """Sync the cached DEBUG value with the state."""
    global DEBUG
    DEBUG = state.get_variable("DEBUG")


def debug_print(*msg):
    """Print debug messages if DEBUG is enabled."""
    if DEBUG and len(msg) == 1:
        print(f"DEBUG: {msg[0]}")
    elif DEBUG and len(msg) > 1:
        print("DEBUG:", " ".join(str(m) for m in msg))


def set_debug(enabled, state):
    """Set the global debug flag."""
    # Update state variable
    state.set_variable("DEBUG", "true" if enabled else "false")
    # Immediately sync the module-global DEBUG flag
    sync_debug_with_state(state)
    # Print debug message only if debugging is enabled
    if DEBUG:
        debug_print(f"Debugging is {'enabled' if enabled else 'disabled'}")


def check_status_code(url):
    # if the URL is has URI, skip
    if not urlparse(url).scheme:
        debug_print(f"Skipping status check for URL without scheme: {url}")
        return "0"
    try:
        response = requests.head(url, allow_redirects=True, timeout=3)
        debug_print(f"Checked URL: {url} - Status Code: {response.status_code}")
        return str(response.status_code)
    except (requests.Timeout, requests.exceptions.ReadTimeout, socket.timeout) as e:
        debug_print(f"⏳ Timeout checking URL {url}: {e}")
        return "420"
    except requests.RequestException as e:
        debug_print(f"❌ Error checking URL {url}: {e}")
        return "0"


def normalize_url(url):
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url


def output_internal_links_analysis_detail(state):
    from data.dsm import lookup_link_in_dsm

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


def display_page_data(data):
    print("\n" + "=" * 60)
    print("EXTRACTED PAGE DATA")
    print("=" * 60)
    if "error" in data:
        print(f"❌ Error occurred: {data['error']}")
        return
    print(f"📄 Source URL: {data.get('url', 'Unknown')}")
    print(f"🎯 CSS Selector: {data.get('selector_used', 'Unknown')}")
    if data.get("include_sidebar", False):
        print("🔲 Sidebar inclusion: ENABLED")
    print()

    # Display main content
    links = data.get("links", [])
    print(f"🔗 LINKS FOUND: {len(links)}")
    if links:
        print("-" * 40)
        for i, (text, href, status) in enumerate(links, 1):
            status_icon = (
                "✅" if status.startswith("2") else "❌" if status != "0" else "⚠️"
            )
            print(f"{i:2}. {status_icon} [{status}] {text[:50]}")
            print(f"    → {href}")

    # Display sidebar links if they exist (with subtle distinction)
    sidebar_links = data.get("sidebar_links", [])
    if sidebar_links:
        print()
        print(f"🔗 SIDEBAR LINKS: {len(sidebar_links)}")
        print("-" * 40)
        for i, (text, href, status) in enumerate(sidebar_links, len(links) + 1):
            status_icon = (
                "✅" if status.startswith("2") else "❌" if status != "0" else "⚠️"
            )
            # Add subtle indicator with │ character
            print(f"{i:2}.│{status_icon} [{status}] {text[:50]}")
            print(f"   │→ {href}")

    print()
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

    # Display sidebar PDFs if they exist
    sidebar_pdfs = data.get("sidebar_pdfs", [])
    if sidebar_pdfs:
        print()
        print(f"📄 SIDEBAR PDF FILES: {len(sidebar_pdfs)}")
        print("-" * 40)
        for i, (text, href, status) in enumerate(sidebar_pdfs, len(pdfs) + 1):
            status_icon = (
                "✅" if status.startswith("2") else "❌" if status != "0" else "⚠️"
            )
            print(f"{i:2}.│{status_icon} [{status}] {text[:50]}")
            print(f"   │→ {href}")

    print()
    embeds = data.get("embeds", [])
    print(f"🎬 VIMEO EMBEDS: {len(embeds)}")
    if embeds:
        print("-" * 40)
        for i, (embed_type, title, src) in enumerate(embeds, 1):
            print(f"{i:2}. [VIMEO] {title[:50]}")
            print(f"    → {src}")

    # Display sidebar embeds if they exist
    sidebar_embeds = data.get("sidebar_embeds", [])
    if sidebar_embeds:
        print()
        print(f"🎬 SIDEBAR VIMEO EMBEDS: {len(sidebar_embeds)}")
        print("-" * 40)
        for i, (embed_type, title, src) in enumerate(sidebar_embeds, len(embeds) + 1):
            print(f"{i:2}.│[VIMEO] {title[:50]}")
            print(f"   │→ {src}")

    print()
    print("=" * 60)
