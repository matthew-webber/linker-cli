import pandas as pd
from data import dsm


def test_get_existing_url_returns_first_url():
    df = pd.DataFrame({"EXISTING URL": ["http://one.com http://two.com"]})
    assert dsm.get_existing_url(df, 0) == "http://one.com"


def test_get_existing_url_handles_commas_and_semicolons():
    df = pd.DataFrame(
        {"EXISTING URL": ["http://one.com,http://two.com;http://three.com"]}
    )
    assert dsm.get_existing_url(df, 0) == "http://one.com"
