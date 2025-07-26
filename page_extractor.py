"""
Page extraction and analysis utilities for Linker CLI.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

from utils.core import debug_print, normalize_url, check_status_code

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def extract_links_from_page(url, selector="#main"):
    debug_print(f"Fetching page: {url}")
    debug_print(f"Using CSS selector: {selector}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.select_one(selector)
        if not container:
            print(
                f"⚠️ Warning ⚠️: No element found matching selector '{selector}', falling back to entire page"
            )
            # container = soup
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
    embeds = []
    container = soup.select_one(selector)
    if not container:
        print(
            f"Warning: No element found matching selector '{selector}', falling back to entire page for embeds"
        )
        # container = soup
    for iframe in container.find_all("iframe", src=True):
        src = iframe.get("src", "")
        if "vimeo" in src.lower():
            title = (
                iframe.get("title", "") or iframe.get_text(strip=True) or "Vimeo Video"
            )
            embeds.append(("vimeo", title, src))
            debug_print(f"Found Vimeo embed: {title}")
    return embeds


def retrieve_page_data(url, selector="#main", include_sidebar=False):
    debug_print(f"Retrieving page data for URL: {url}")

    try:
        url = normalize_url(url)
        debug_print(f"Normalized URL: {url}")
        response = requests.get(url, timeout=30)
        debug_print(
            f"HTTP GET request completed with status code: {response.status_code}"
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        debug_print("HTML content successfully parsed with BeautifulSoup")

        # Extract main content
        debug_print(f"Extracting main content using selector: {selector}")
        main_links, main_pdfs = extract_links_from_page(url, selector)
        debug_print(
            f"Extracted {len(main_links)} links and {len(main_pdfs)} PDFs from main content"
        )
        main_embeds = extract_embeds_from_page(soup, selector)
        debug_print(f"Extracted {len(main_embeds)} embeds from main content")

        # Extract sidebar content if requested
        sidebar_links, sidebar_pdfs, sidebar_embeds = [], [], []
        if include_sidebar:
            debug_print("Sidebar content extraction enabled")
            try:
                sidebar_links, sidebar_pdfs = extract_links_from_page(
                    url, "#sidebar-components"
                )
                debug_print(
                    f"Extracted {len(sidebar_links)} links and {len(sidebar_pdfs)} PDFs from sidebar"
                )
                sidebar_embeds = extract_embeds_from_page(soup, "#sidebar-components")
                debug_print(f"Extracted {len(sidebar_embeds)} embeds from sidebar")
            except Exception as e:
                debug_print(f"Warning: Error extracting sidebar content: {e}")

        data = {
            "links": main_links,
            "pdfs": main_pdfs,
            "embeds": main_embeds,
            "sidebar_links": sidebar_links,
            "sidebar_pdfs": sidebar_pdfs,
            "sidebar_embeds": sidebar_embeds,
        }

        total_main = len(main_links) + len(main_pdfs) + len(main_embeds)
        total_sidebar = len(sidebar_links) + len(sidebar_pdfs) + len(sidebar_embeds)
        debug_print(
            f"Extracted main content: {len(main_links)} links, {len(main_pdfs)} PDFs, {len(main_embeds)} embeds"
        )
        if include_sidebar:
            debug_print(
                f"Extracted sidebar content: {len(sidebar_links)} links, {len(sidebar_pdfs)} PDFs, {len(sidebar_embeds)} embeds"
            )

        return data
    except Exception as e:
        debug_print(f"Error retrieving page data: {e}")
        return {
            "url": url,
            "links": [],
            "pdfs": [],
            "embeds": [],
            "sidebar_links": [],
            "sidebar_pdfs": [],
            "sidebar_embeds": [],
            "error": str(e),
            "selector_used": selector,
            "include_sidebar": include_sidebar,
        }


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
