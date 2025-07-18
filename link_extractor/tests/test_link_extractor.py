# import sys
# import os

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# import pytest
# from unittest.mock import patch, mock_open
# from link_extractor import (
#     extract_links,
#     normalize_url,
#     page_already_processed,
#     check_status_code,
# )


# # def test_check_status_code():
# #     assert check_status_code("")


# def test_normalize_url():
#     assert normalize_url("example.com") == "http://example.com"
#     assert normalize_url("https://example.com") == "https://example.com"


# @patch("link_extractor.requests.get")
# def test_extract_links(mock_get):
#     html = """
#     <div id="main">
#         <a href="https://web.musc.edu/afwejfio">foo</a>
#         <a href="https://web.musc.edu">bar</a>
#         <a href="mailto:whatever@musc.edu">baz</a>
#         <a href="tel:1234567890">Call Us</a>
#         <a href="/home">Home</a>
#     </div>
#     """
#     mock_get.return_value.status_code = 200
#     mock_get.return_value.text = html
#     mock_get.return_value.url = "http://example.com"

#     links = extract_links("http://example.com", "#main")
#     assert len(links) == 5
#     assert links[0] == ("foo", "https://web.musc.edu/afwejfio", "404")
#     assert links[1] == ("bar", "https://web.musc.edu", "200")
#     assert links[2] == ("baz", "mailto:whatever@musc.edu", "0")
#     assert links[3] == ("Call Us", "tel:1234567890", "0")
#     assert links[4] == ("Home", "http://example.com/home", "404")


# @patch("builtins.open", new_callable=mock_open, read_data="http://example.com\n")
# @patch("os.path.isfile", return_value=True)
# def test_page_already_processed(mock_isfile, mock_file):
#     assert page_already_processed("http://example.com") is True
