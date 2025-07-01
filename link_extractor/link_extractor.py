#!/usr/bin/env python3
"""
link_extractor.py: Fetch a webpage, extract all <a> tags within a specified CSS selector,
and log them to links.csv, avoiding reprocessing pages.

Usage:
  python link_extractor.py URL -s SELECTOR
Example:
  python link_extractor.py http://example.com/foo.html -s '#main'
"""

import argparse
import csv
import os
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Constants
CSV_FILE = "links.csv"


def check_status_code(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return str(response.status_code)
    except requests.RequestException:
        return "0"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract anchor tags within a given CSS selector from a webpage and log them to a CSV file."
    )
    parser.add_argument("url", help="URL of the webpage to process")
    parser.add_argument(
        "-s",
        "--selector",
        help='CSS selector of the container element (e.g., "#main" or ".content")',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a trial run without making any changes",
    )
    return parser.parse_args()


def normalize_url(url):
    """Ensure the URL has a scheme."""
    parsed = urlparse(url)
    if not parsed.scheme:
        return "http://" + url
    return url


def page_already_processed(legacy_page_url):
    """Check if the page URL is already logged in the CSV."""
    if not os.path.isfile(CSV_FILE):
        return False
    try:
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == legacy_page_url:
                    return True
    except Exception:
        pass
    return False


def generate_row_data(legacy_page_url, links):
    """Generate header and data rows for the CSV file."""
    header_row = ["Legacy Page URL", "Link Text", "Link Href", "Status Code"]
    data_rows = [
        [legacy_page_url, text, href, status_code] for text, href, status_code in links
    ]
    return header_row, data_rows


def append_links(legacy_page_url, links):
    """Append extracted links to the CSV file."""
    file_exists = os.path.isfile(CSV_FILE)
    header_row, data_rows = generate_row_data(legacy_page_url, links)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header_row)
        writer.writerows(data_rows)


def extract_links(url, selector):
    """Fetch the page, parse HTML, and return list of (text, absolute href)."""
    print(f"Fetching {url}...")
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.select_one(selector)
    if not container:
        print(
            f"Error: No element found matching selector '{selector}'", file=sys.stderr
        )
        sys.exit(1)

    anchors = container.find_all("a", href=True)
    links = []
    for a in anchors:
        text = a.get_text(strip=True)
        href = urljoin(response.url, a["href"])
        status_code = check_status_code(href)
        links.append((text, href, status_code))
    return links


def main():
    args = parse_args()
    url = normalize_url(args.url)
    selector = args.selector or "#main"

    print(f"Selector set to '{selector}'")

    if page_already_processed(url):
        print(f"Page '{url}' has already been processed. Exiting.")
        sys.exit(0)

    try:
        links = extract_links(url, selector)
    except requests.RequestException as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)

    if not links:
        print(f"No links found within selector '{selector}'.")
    elif args.dry_run:
        print(f"Dry run: Would append {len(links)} link(s) to '{CSV_FILE}'.")
        _, links = generate_row_data(url, links)
        for link in links:
            print(f" - {link}")
    else:
        append_links(url, links)
        print(f"Appended {len(links)} link(s) to '{CSV_FILE}'.")


if __name__ == "__main__":
    main()
