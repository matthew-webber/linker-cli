from bs4 import BeautifulSoup
from types import SimpleNamespace
from unittest.mock import patch

from utils.scraping import (
    extract_meta_robots,
    extract_links_from_page,
    extract_embeds_from_page,
)


def test_extract_meta_robots_found():
    html = "<html><head><meta name='ROBOTS' content='NOINDEX, NOFOLLOW'></head></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert extract_meta_robots(soup) == "NOINDEX, NOFOLLOW"


def test_extract_meta_robots_missing():
    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert extract_meta_robots(soup) == ""


def test_extract_embeds_and_skip_from_links():
    html = """
    <div id='main'>
        <a href='http://example.com'>Regular Link</a>
        <a href='#' data-video='12345' data-title='Sample Video'>Embed Link</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    response = SimpleNamespace(url="http://base.com")

    with patch("utils.scraping.check_status_code", return_value="200"):
        links, pdfs = extract_links_from_page(soup, response)

    assert links == [("Regular Link", "http://example.com", "200")]
    assert pdfs == []

    embeds = extract_embeds_from_page(soup)
    assert embeds == [("Sample Video", "https://player.vimeo.com/video/12345")]
