from bs4 import BeautifulSoup
from utils.scraping import extract_meta_robots


def test_extract_meta_robots_found():
    html = "<html><head><meta name='ROBOTS' content='NOINDEX, NOFOLLOW'></head></html>"
    soup = BeautifulSoup(html, "html.parser")
    assert extract_meta_robots(soup) == "NOINDEX, NOFOLLOW"


def test_extract_meta_robots_missing():
    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert extract_meta_robots(soup) == ""
