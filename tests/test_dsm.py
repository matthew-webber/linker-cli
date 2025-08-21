import pandas as pd
from data import dsm


def test_get_existing_urls_returns_all_urls():
    df = pd.DataFrame({"EXISTING URL": ["http://one.com http://two.com"]})
    assert dsm.get_existing_urls(df, 0) == ["http://one.com", "http://two.com"]


def test_get_existing_urls_handles_commas_and_semicolons():
    df = pd.DataFrame(
        {"EXISTING URL": ["http://one.com,http://two.com;http://three.com"]}
    )
    assert dsm.get_existing_urls(df, 0) == [
        "http://one.com",
        "http://two.com",
        "http://three.com",
    ]


def test_get_existing_url_wrapper_returns_first():
    df = pd.DataFrame({"EXISTING URL": ["http://one.com http://two.com"]})
    assert dsm.get_existing_url(df, 0) == "http://one.com"
