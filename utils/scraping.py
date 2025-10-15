"""
Page extraction and analysis utilities for Linker CLI.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

from utils.core import debug_print, normalize_url, check_status_code

CACHE_DIR = Path("migration_cache")
CACHE_DIR.mkdir(exist_ok=True)


def get_page_soup(url):
    """
    Common utility to fetch a page and return the BeautifulSoup object.

    Args:
        url (str): The URL to fetch

    Returns:
        tuple: (soup, response) - BeautifulSoup object and the response object

    Raises:
        requests.RequestException: If there's an error fetching the page
    """
    debug_print(f"Fetching page: {url}")
    try:
        url = normalize_url(url)
        debug_print(f"Normalized URL: {url}")
        response = requests.get(url, timeout=5)
        debug_print(
            f"HTTP GET request completed with status code: {response.status_code}"
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        debug_print("HTML content successfully parsed with BeautifulSoup")
        return soup, response
    except requests.RequestException as e:
        debug_print(f"Error fetching page: {e}")
        raise


def extract_meta_description(soup):
    """
    Extract the meta description from a BeautifulSoup object.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object of the page

    Returns:
        str: The content of the meta description tag, or an empty string if not found
    """
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and "content" in meta_desc.attrs:
        debug_print(f"Meta description found: {meta_desc['content']}")
        return meta_desc["content"]
    debug_print("No meta description found")
    return ""


def extract_meta_robots(soup):
    """Extract the meta robots directive from a BeautifulSoup object."""

    meta_tag = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "robots"})
    if meta_tag and "content" in meta_tag.attrs:
        debug_print(f"Meta robots found: {meta_tag['content']}")
        return meta_tag["content"]
    debug_print("No meta robots tag found")
    return ""


def extract_links_from_page(soup, response, selector="#main"):
    """Return the hyperlinks found within a page section.

    Both the parsed ``soup`` and original ``response`` are required so that
    relative URLs can be resolved without re-fetching the page. Links ending
    in ``.pdf`` are returned separately from other hyperlinks.

    Args:
        soup: Parsed BeautifulSoup document for the page.
        response: ``requests`` response object used to resolve relative URLs.
        selector: CSS selector identifying the container to inspect. Defaults
            to ``"#main"`` and falls back to the entire page if not found.

    Returns:
        tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
        Two lists containing ``(text, href, status_code)`` tuples for regular
        links and PDFs respectively.
    """

    debug_print(f"Using CSS selector: {selector}")
    container = soup.select_one(selector)
    if not container:
        print(
            f"⚠️ Warning ⚠️: No element found matching selector '{selector}', falling back to entire page"
        )
        container = soup
    anchors = container.find_all("a", href=True)
    debug_print(f"Found {len(anchors)} anchor tags")
    links = []
    pdfs = []
    for a in anchors:
        if a.get("href") == "#" and a.has_attr("data-video"):
            debug_print("Skipping anchor tag treated as Vimeo embed")
            continue

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


def extract_embeds_from_page(soup, selector="#main"):
    """Return Vimeo embeds found on the page.

    Embeds are represented in the markup as ``<a href="#" data-video="..." data-title="...">``
    elements, which are transformed into iframes by client-side JavaScript.
    """

    embeds = []
    container = soup.select_one(selector)
    if not container:
        print(
            f"Warning: No element found matching selector '{selector}', falling back to entire page for embeds"
        )
        container = soup

    for a in container.find_all("a", href="#"):
        video_id = a.get("data-video")
        if not video_id:
            continue
        title = a.get("data-title", "") or a.get_text(strip=True) or "Vimeo Video"
        src = f"https://player.vimeo.com/video/{video_id}"
        embeds.append((title, src))
        debug_print(f"Found Vimeo embed: {title}")

    return embeds


def retrieve_page_data(url, selector="#main", include_sidebar=False):
    debug_print(f"Retrieving page data for URL: {url}")

    try:
        soup, response = get_page_soup(url)

        # Extract main content
        debug_print(f"Extracting main content using selector: {selector}")
        main_links, main_pdfs = extract_links_from_page(soup, response, selector)
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
                    soup, response, "#sidebar-components"
                )
                debug_print(
                    f"Extracted {len(sidebar_links)} links and {len(sidebar_pdfs)} PDFs from sidebar"
                )
                sidebar_embeds = extract_embeds_from_page(soup, "#sidebar-components")
                debug_print(f"Extracted {len(sidebar_embeds)} embeds from sidebar")
            except Exception as e:
                debug_print(f"Warning: Error extracting sidebar content: {e}")

        meta_description = extract_meta_description(soup)
        debug_print(f"Meta description extracted: {meta_description}")
        meta_robots = extract_meta_robots(soup)
        debug_print(f"Meta robots extracted: {meta_robots}")

        data = {
            "links": main_links,
            "pdfs": main_pdfs,
            "embeds": main_embeds,
            "sidebar_links": sidebar_links,
            "sidebar_pdfs": sidebar_pdfs,
            "sidebar_embeds": sidebar_embeds,
            "meta_description": meta_description,
            "meta_robots": meta_robots,
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
            "meta_description": "",
            "meta_robots": "",
            "error": str(e),
            "selector_used": selector,
            "include_sidebar": include_sidebar,
        }
