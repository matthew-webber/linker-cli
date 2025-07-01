"""
Page extraction and analysis utilities for Linker CLI.
"""

import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def normalize_url(url):
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url


def check_status_code(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return str(response.status_code)
    except requests.RequestException:
        return "0"


def extract_links_from_page(url, selector="#main", debug_print=None):
    if debug_print:
        debug_print(f"Fetching page: {url}")
        debug_print(f"Using CSS selector: {selector}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.select_one(selector)
        if not container:
            if debug_print:
                debug_print(
                    f"Warning: No element found matching selector '{selector}', falling back to entire page"
                )
            container = soup
        anchors = container.find_all("a", href=True)
        if debug_print:
            debug_print(f"Found {len(anchors)} anchor tags")
        links = []
        pdfs = []
        for a in anchors:
            text = a.get_text(strip=True)
            href = urljoin(response.url, a["href"])
            if debug_print:
                debug_print(
                    f"Processing link: {text[:50]}{'...' if len(text) > 50 else ''} -> {href}"
                )
            status_code = check_status_code(href)
            if href.lower().endswith(".pdf"):
                pdfs.append((text, href, status_code))
                if debug_print:
                    debug_print(f"  -> Categorized as PDF")
            else:
                links.append((text, href, status_code))
                if debug_print:
                    debug_print(f"  -> Categorized as regular link")
        return links, pdfs
    except requests.RequestException as e:
        if debug_print:
            debug_print(f"Error fetching page: {e}")
        raise


def extract_embeds_from_page(soup, selector="#main", debug_print=None):
    embeds = []
    container = soup.select_one(selector)
    if not container:
        if debug_print:
            debug_print(
                f"Warning: No element found matching selector '{selector}', falling back to entire page for embeds"
            )
        container = soup
    for iframe in container.find_all("iframe", src=True):
        src = iframe.get("src", "")
        if "vimeo" in src.lower():
            title = (
                iframe.get("title", "") or iframe.get_text(strip=True) or "Vimeo Video"
            )
            embeds.append(("vimeo", title, src))
            if debug_print:
                debug_print(f"Found Vimeo embed: {title}")
    return embeds


def retrieve_page_data(url, selector="#main", debug_print=None):
    if debug_print:
        debug_print(f"Retrieving page data for URL: {url}")
    try:
        url = normalize_url(url)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links, pdfs = extract_links_from_page(url, selector, debug_print)
        embeds = extract_embeds_from_page(soup, selector, debug_print)
        data = {
            "url": url,
            "links": links,
            "pdfs": pdfs,
            "embeds": embeds,
            "selector_used": selector,
        }
        if debug_print:
            debug_print(
                f"Extracted {len(links)} links, {len(pdfs)} PDFs, {len(embeds)} embeds"
            )
        return data
    except Exception as e:
        if debug_print:
            debug_print(f"Error retrieving page data: {e}")
        return {
            "url": url,
            "links": [],
            "pdfs": [],
            "embeds": [],
            "error": str(e),
            "selector_used": selector,
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
    print()
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
    print()
    embeds = data.get("embeds", [])
    print(f"🎬 VIMEO EMBEDS: {len(embeds)}")
    if embeds:
        print("-" * 40)
        for i, (embed_type, title, src) in enumerate(embeds, 1):
            print(f"{i:2}. [VIMEO] {title[:50]}")
            print(f"    → {src}")
    print()
    print("=" * 60)
